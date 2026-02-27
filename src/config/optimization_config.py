import pandas as pd
import datetime
from datetime import timedelta
import src.preprocess.extract as extract
from src.config.constants import ShiftType, LineType, KitLevel, DefaultConfig

# Re-import all the packages
import importlib

# Reload modules to get latest changes - REMOVED to prevent infinite loops
# importlib.reload(extract)


# ============================================================
# SINGLE SOURCE OF TRUTH FOR DATE CONFIGURATION
# ============================================================

from src.utils.logger import config_logger, ConfigSource


def get_date_configuration():
    """
    Get date configuration from session state.
    
    ⚠️ CENTRALIZED DATE ACCESS POINT - All modules must use this function ⚠️
    
    Data Flow:
    - session_state is initialized by: initialize_session_state() in config_page.py
    - session_state is updated by: save_configuration() in config_page.py
    - session_state is read by: this function (read-only access)
    - Business logic uses: this function (never directly access session_state)
    
    This ensures:
    - Consistent date values across all modules
    - Single source of truth (session_state only)
    - No confusion from multiple date sources
    
    All other components MUST use this function to get dates.
    Do NOT read dates directly from session_state elsewhere.
    
    Returns:
        tuple: (demand_start_date, production_start_date, production_end_date, planning_days, date_span)
            - demand_start_date: datetime object for filtering demand data
            - production_start_date: datetime object for first production day
            - production_end_date: datetime object for last production day
            - planning_days: int number of planning days (production_end_date - production_start_date + 1)
            - date_span: list of day numbers [1, 2, ..., planning_days]
    
    Raises:
        RuntimeError: If session_state is not initialized (should never happen in normal flow)
    """
    try:
        import streamlit as st
        
        if not hasattr(st, 'session_state'):
            raise RuntimeError(
                "❌ CRITICAL: Streamlit session_state not available!\n"
                "This function must be called within a Streamlit app context."
            )
        
        # Check which fields are available
        required_fields = [
            'demand_start_date',
            'production_start_date',
            'production_end_date',
            'planning_days',
            'date_span'
        ]
        
        missing_fields = [f for f in required_fields if f not in st.session_state]
        
        if missing_fields:
            raise RuntimeError(
                f"❌ CRITICAL: Date configuration not initialized!\n"
                f"Missing fields in session_state: {missing_fields}\n"
                f"initialize_session_state() must be called before accessing dates.\n"
                f"This indicates a bug in the application flow."
            )
        
        # All fields present - read from session state (SINGLE SOURCE OF TRUTH)
        demand_start_date = datetime.datetime.combine(
            st.session_state.demand_start_date, datetime.datetime.min.time()
        )
        production_start_date = datetime.datetime.combine(
            st.session_state.production_start_date, datetime.datetime.min.time()
        )
        production_end_date = datetime.datetime.combine(
            st.session_state.production_end_date, datetime.datetime.min.time()
        )
        planning_days = st.session_state.planning_days
        date_span = st.session_state.date_span
        
        config_logger.log_date_config(
            ConfigSource.SESSION_STATE,
            demand_start_date, production_end_date, planning_days, date_span
        )
        
        return demand_start_date, production_start_date, production_end_date, planning_days, date_span
        
    except Exception as e:
        error_msg = f"❌ CRITICAL: Failed to get date configuration: {e}"
        config_logger.logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def get_product_list():
    """
    Get filtered product list using centralized date configuration.
    Uses get_date_configuration() as single source of truth.
    """
    try:
        from src.demand_filtering import DemandFilter
        
        # Get dates from SINGLE SOURCE OF TRUTH
        demand_start_date, _, _, _, _ = get_date_configuration()
        
        filter_instance = DemandFilter()
        filter_instance.load_data(start_date=demand_start_date, force_reload=True)
        return filter_instance.get_filtered_product_list()
    except Exception as e:
        print(f"[WARN] Could not load filtered product list: {e}")
        # Fallback to default
        demand_start_date, _, _, _, _ = get_date_configuration()
        return extract.get_released_product_list(demand_start_date)


# def get_employee_type_list():
#     """Get employee type list from session state or default"""
#     employee_type_list = extract.read_employee_data()
#     return employee_type_list["employment_type"].unique().tolist()

#Need to change from get_shift_list
def get_shift_list():
    """Get shift list from session state or default"""
    try:
        import streamlit as st
        if hasattr(st, 'session_state') and 'selected_shifts' in st.session_state:
            return st.session_state.selected_shifts
    except:
        # print("Could not get shift list from session state")
        raise Exception("Shift list not found with error:"+str(e))
    #     pass
    
    # # Default: load from data files
    # shift_list = extract.get_shift_info()
    # return shift_list["id"].unique().tolist()

#where?
def get_line_list():
    """Get line list - try from streamlit session state first, then from data files"""
    try:
        # Try to get from streamlit session state (from Dataset Metadata page)
        import streamlit as st
        if hasattr(st, 'session_state') and 'selected_lines' in st.session_state:
            print(f"Using lines from Dataset Metadata page: {st.session_state.selected_lines}")
            return st.session_state.selected_lines
    except Exception as e:
        print(f"Could not get lines from streamlit session: {e}")
    
    # Default: load from data files
    print(f"Loading line list from data files")
    line_df = extract.read_packaging_line_data()
    line_list = line_df["id"].unique().tolist()
    return line_list

# DO NOT load at import time - always call get_line_list() dynamically
# LINE_LIST = get_line_list()  # REMOVED - was causing stale data!

#where?
def get_kit_line_match():
    kit_line_match = extract.read_kit_line_match_data()
    kit_line_match_dict = kit_line_match.set_index("kit_name")["line_type"].to_dict()
    
    # Create line name to ID mapping
    line_name_to_id = {
        "long line": LineType.LONG_LINE,
        "mini load": LineType.MINI_LOAD,
        "miniload": LineType.MINI_LOAD,     # Alternative naming (no space)
        "Long_line": LineType.LONG_LINE,    # Alternative naming
        "Mini_load": LineType.MINI_LOAD,    # Alternative naming
    }
    
    # Convert string line names to numeric IDs
    converted_dict = {}
    for kit, line_name in kit_line_match_dict.items():
        if isinstance(line_name, str) and line_name.strip():
            # Convert string names to numeric IDs
            line_id = line_name_to_id.get(line_name.strip(), None)
            if line_id is not None:
                converted_dict[kit] = line_id
            else:
                print(f"Warning: Unknown line type '{line_name}' for kit {kit}")
                # Default to long line if unknown
                converted_dict[kit] = LineType.LONG_LINE
        elif isinstance(line_name, (int, float)) and not pd.isna(line_name):
            # Already numeric
            converted_dict[kit] = int(line_name)
        else:
            # Missing or empty line type - skip (no production needed for virtual masters)
            pass  # Don't add to converted_dict - these kits won't have line assignments
            
    return converted_dict

KIT_LINE_MATCH_DICT = get_kit_line_match()


def get_line_cnt_per_type():
    try:
        # Try to get from streamlit session state (from config page)
        import streamlit as st
        if hasattr(st, 'session_state') and 'line_counts' in st.session_state:
            # print(f"Using line counts from config page: {st.session_state.line_counts}")
            return st.session_state.line_counts
    except Exception as e:
        print(f"Could not get line counts from streamlit session: {e}")
    
    print(f"Loading default line count values from data files")
    line_df = extract.read_packaging_line_data()
    line_cnt_per_type = line_df.set_index("id")["line_count"].to_dict()
    print("line cnt per type", line_cnt_per_type)
    return line_cnt_per_type

# DO NOT load at import time - always call get_line_cnt_per_type() dynamically
# LINE_CNT_PER_TYPE = get_line_cnt_per_type()  # REMOVED - was causing stale data!

#where?
def get_demand_dictionary(force_reload=False):
    """
    Get filtered demand dictionary from session state.
    IMPORTANT: This dynamically loads data to reflect current Streamlit configs/dates.
    Reads dates directly from st.session_state.
    """
    try:
        from src.demand_filtering import DemandFilter
        
        # Get dates from SINGLE SOURCE OF TRUTH
        demand_start_date, _, _, _, _ = get_date_configuration()
        
        # Always get fresh filtered demand to reflect current configs
        filter_instance = DemandFilter()
        filter_instance.load_data(start_date=demand_start_date, force_reload=True)
        
        demand_dictionary = filter_instance.get_filtered_demand_dictionary()
        print(f"📈 FRESH FILTERED DEMAND: {len(demand_dictionary)} products with total demand {sum(demand_dictionary.values())}")
        print(f"🔄 LOADED DYNAMICALLY: Reflects current date configuration")
        return demand_dictionary
    except Exception as e:
        print(f"Error loading dynamic demand dictionary: {e}")
        raise Exception("Demand dictionary not found with error:"+str(e))

# DO NOT load at import time - always call get_demand_dictionary() dynamically
# DEMAND_DICTIONARY = get_demand_dictionary()  # REMOVED - was causing stale data!

#delete as already using default cost rates
def get_cost_list_per_emp_shift():
    try:
        # Try to get from streamlit session state (from config page)
        import streamlit as st
        if hasattr(st, 'session_state') and 'cost_list_per_emp_shift' in st.session_state:
            print(f"Using cost list from config page: {st.session_state.cost_list_per_emp_shift}")
            return st.session_state.cost_list_per_emp_shift
    except Exception as e:
        print(f"Could not get cost list from streamlit session: {e}")
    
    print(f"Loading default cost values")
    # Default hourly rates - Important: multiple employment types with different costs
    return DefaultConfig.DEFAULT_COST_RATES

def shift_code_to_name():
    return ShiftType.get_all_names()

def line_code_to_name():
    """Convert line type IDs to readable names"""
    return LineType.get_all_names()

# DO NOT load at import time - always call get_cost_list_per_emp_shift() dynamically
# COST_LIST_PER_EMP_SHIFT = get_cost_list_per_emp_shift()  # REMOVED - was causing stale data!
        


# COST_LIST_PER_EMP_SHIFT = {  # WH_Workforce_Hourly_Pay_Scale
#     "Fixed": {1: 0, 2: 22, 3: 18},
#     "Humanizer": {1: 10, 2: 10, 3: 10},
# }






#where to put?
def get_team_requirements(product_list=None):
    """
    Extract team requirements from Kits Calculation CSV.
    Returns dictionary with employee type as key and product requirements as nested dict.
    """
    if product_list is None:
        product_list = get_product_list()  # Get fresh product list
        

    kits_df = extract.read_personnel_requirement_data()

    team_req_dict = {
        "UNICEF Fixed term": {},
        "Humanizer": {}
    }
    
    # Process each product in the product list
    for product in product_list:
        print("product",product)
        print(f"Processing team requirements for product: {product}")
        product_data = kits_df[kits_df['Kit'] == product]
        print("product_data",product_data)
        if not product_data.empty:
            # Extract Humanizer and UNICEF staff requirements
            humanizer_req = product_data["Humanizer"].iloc[0]
            unicef_req = product_data["UNICEF staff"].iloc[0]
            
            # Convert to int (data is already cleaned in extract function)
            team_req_dict["Humanizer"][product] = int(humanizer_req)
            team_req_dict["UNICEF Fixed term"][product] = int(unicef_req)
        else:
            print(f"Warning: Product {product} not found in Kits Calculation data, setting requirements to 0")
            
    
    return team_req_dict



def get_max_employee_per_type_on_day():
    try:
        # Try to get from streamlit session state (from config page)
        import streamlit as st
        if hasattr(st, 'session_state') and 'max_employee_per_type_on_day' in st.session_state:
            print(f"Using max employee counts from config page: {st.session_state.max_employee_per_type_on_day}")
            return st.session_state.max_employee_per_type_on_day
    except Exception as e:
        print(f"Could not get max employee counts from streamlit session: {e}")
    
    print(f"Loading default max employee values")
    # Get date span from SINGLE SOURCE OF TRUTH
    _, _, _, _, date_span = get_date_configuration()
    
    max_employee_per_type_on_day = {
        "UNICEF Fixed term": {
            t: 8 for t in date_span
        },
        "Humanizer": {
            t: 10 for t in date_span
        }
    }
    return max_employee_per_type_on_day


# Keep the constant for backward compatibility, but use function instead
MAX_HOUR_PER_PERSON_PER_DAY = 14  # legal standard
def get_max_hour_per_shift_per_person():
    """Get max hours per shift per person from session state or default"""
    try:
        import streamlit as st
        if hasattr(st, 'session_state'):
            # Build from individual session state values
            max_hours = {
                ShiftType.REGULAR: st.session_state.get('max_hours_shift_1', DefaultConfig.MAX_HOUR_PER_SHIFT_PER_PERSON[ShiftType.REGULAR]),
                ShiftType.EVENING: st.session_state.get('max_hours_shift_2', DefaultConfig.MAX_HOUR_PER_SHIFT_PER_PERSON[ShiftType.EVENING]),
                ShiftType.OVERTIME: st.session_state.get('max_hours_shift_3', DefaultConfig.MAX_HOUR_PER_SHIFT_PER_PERSON[ShiftType.OVERTIME])
            }
            return max_hours
    except Exception as e:
        print(f"Could not get max hours per shift from session: {e}")
    
    # Fallback to default
    return DefaultConfig.MAX_HOUR_PER_SHIFT_PER_PERSON



# Keep these complex getters that access DefaultConfig or have complex logic:

# ---- Kit Hierarchy for Production Ordering ----
def get_kit_hierarchy_data():
    kit_levels, dependencies, priority_order = extract.get_production_order_data()
    
    return kit_levels, dependencies, priority_order

KIT_LEVELS, KIT_DEPENDENCIES, PRODUCTION_PRIORITY_ORDER = get_kit_hierarchy_data()
print(f"Kit Hierarchy loaded: {len(KIT_LEVELS)} kits, Priority order: {len(PRODUCTION_PRIORITY_ORDER)} items")

def get_kit_levels():
    """Get kit levels lazily - returns {kit_id: level} where 0=prepack, 1=subkit, 2=master"""
    kit_levels, _, _ = get_kit_hierarchy_data()
    return kit_levels

def get_kit_dependencies():
    """Get kit dependencies lazily - returns {kit_id: [dependency_list]}"""
    _, dependencies, _ = get_kit_hierarchy_data()
    return dependencies

def get_max_parallel_workers():
    """Get max parallel workers from session state or default"""
    try:
        import streamlit as st
        if hasattr(st, 'session_state'):
            # Build from individual session state values
            max_parallel_workers = {
                LineType.LONG_LINE: st.session_state.get('max_parallel_workers_long_line', DefaultConfig.MAX_PARALLEL_WORKERS_LONG_LINE),
                LineType.MINI_LOAD: st.session_state.get('max_parallel_workers_mini_load', DefaultConfig.MAX_PARALLEL_WORKERS_MINI_LOAD)
            }
            return max_parallel_workers
    except Exception as e:
        print(f"Could not get max parallel workers from session: {e}")
    
    # Fallback to default
    return {
        LineType.LONG_LINE: DefaultConfig.MAX_PARALLEL_WORKERS_LONG_LINE,
        LineType.MINI_LOAD: DefaultConfig.MAX_PARALLEL_WORKERS_MINI_LOAD
    }



def get_fixed_min_unicef_per_day():
    """
    Get fixed minimum UNICEF employees per day - try from streamlit session state first, then default
    This ensures a minimum number of UNICEF fixed-term staff are present every working day
    """
    try:
        import streamlit as st
        if hasattr(st, 'session_state') and 'fixed_min_unicef_per_day' in st.session_state:
            print(f"Using fixed minimum UNICEF per day from config page: {st.session_state.fixed_min_unicef_per_day}")
            return st.session_state.fixed_min_unicef_per_day
    except ImportError:
        pass 
    
    # Fallback to default configuration
    return DefaultConfig.FIXED_MIN_UNICEF_PER_DAY


def get_payment_mode_config():
    """
    Get payment mode configuration - try from streamlit session state first, then default values
    Payment modes:
    - "bulk": If employee works any hours in shift, pay for full shift hours
    - "partial": Pay only for actual hours worked
    """
    try:
        # Try to get from streamlit session state (from Dataset Metadata page)
        import streamlit as st
        if hasattr(st, 'session_state') and 'payment_mode_config' in st.session_state:
            print(f"Using payment mode config from streamlit session: {st.session_state.payment_mode_config}")
            return st.session_state.payment_mode_config
    except Exception as e:
        print(f"Could not get payment mode config from streamlit session: {e}")
    
    # Default payment mode configuration
    print(f"Loading default payment mode configuration")
    payment_mode_config = DefaultConfig.PAYMENT_MODE_CONFIG
    
    return payment_mode_config


print("✅ Module-level configuration functions defined (variables initialized dynamically)")