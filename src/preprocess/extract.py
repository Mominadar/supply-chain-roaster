import pandas as pd
import datetime
from datetime import date, timedelta
import json
import os
import yaml
from pathlib import Path

# Load paths configuration
_config_dir = Path(__file__).parent.parent / "config"
_paths_file = _config_dir / "paths.yaml"
with open(_paths_file, 'r', encoding='utf-8') as f:
    PATHS = yaml.safe_load(f)


def read_kit_line_match_data() -> pd.DataFrame:
    """Read kit composition and relation data"""
    path = PATHS['data']['csv']['kit_composition']
    return pd.read_csv(path)


def read_employee_data() -> pd.DataFrame:
    """Read employee workforce hourly pay scale data"""
    path = PATHS['data']['csv']['workforce_pay_scale']
    return pd.read_csv(path)

def get_shift_info() -> pd.DataFrame:
    """Read work shift information"""
    path = PATHS['data']['csv']['work_shift']
    df = pd.read_csv(path)
    return df

def get_released_product_list(start_date=None):
    """
    get released product list from COOIS_Released_Prod_Orders.csv
    
    Args:
        start_date: start date to filter data. Required.
    """
    released_orders = read_orders_data(
        start_date=start_date, 
    )
    product_list = released_orders["Material Number"].unique().tolist()
    print(f"Released products for date range {start_date}: {len(product_list)} products")
    return product_list

# def read_shift_cost_data() -> pd.DataFrame:
#     """Read shift cost data from workforce pay scale"""
#     path = PATHS['data']['csv']['workforce_pay_scale']
#     return pd.read_csv(path)


# def read_work_center_capacity() -> pd.DataFrame:
#     """Read work center capacity data"""
#     path = PATHS['data']['csv']['work_center_capacity']
#     return pd.read_csv(path)


# def read_material_master() -> pd.DataFrame:
#     """Read material master WMS data"""
#     path = PATHS['data']['csv']['material_master']
#     return pd.read_csv(path)

def read_packaging_line_data() -> pd.DataFrame:
    """Read packaging line data (filtered work center capacity)"""
    path = PATHS['data']['csv']['work_center_capacity_processed']
    df = pd.read_csv(path)
    # Validate expected columns (common Cloud Run issue when Git LFS pointers are present)
    if "line_for_packaging" not in df.columns:
        # Provide a clear error to guide deployment fixes
        cols = ", ".join(df.columns)
        raise KeyError(
            f"Missing column 'line_for_packaging' in {path}. Columns found: [{cols}]. "
            "If deploying on Cloud Run/Cloud Build, ensure Git LFS files are included in the image. "
            "Options: (1) build from a workspace with 'git lfs pull' done, (2) use a Cloud Build step to fetch LFS, "
            "or (3) move data to GCS and load at runtime."
        )
    # Filter for packaging lines only
    df = df[df["line_for_packaging"] == True]
    return df


def read_orders_data(
    start_date=None,
) -> pd.DataFrame:
    """
    Read COOIS Released Production Orders data
    
    Args:
        start_date: start date (pd.Timestamp or datetime)
    
    Returns:
        pd.DataFrame: filtered dataframe by date
    """
    path = PATHS['data']['csv']['demand']
    df = pd.read_csv(path)
    assert len(df) > 0, "No data found in the file"
    # convert date column to datetime
    df["Basic start date"] = pd.to_datetime(df["Basic start date"])
    
    
    # filter by date
    if start_date is not None:    # Filter for exact start date only
        df = df[df["Basic start date"] == pd.to_datetime(start_date)]
    else:
        raise ValueError("start_date is required")
    df['Order quantity (GMEIN)'] = df['Order quantity (GMEIN)'].astype(int)
    
    return df


def read_package_speed_data():
    """Read package speed data from Kits Calculation"""
    path = PATHS['data']['csv']['kits_calculation']
    df = pd.read_csv(path, usecols=["Kit", "Kit per day","Paid work hours per day"], encoding='latin1')
    df["Kit per day"] = 800
    df['Kit per day'] = df['Kit per day'].astype(int)
    df["Paid work hours per day"] = 7.5
    df['Paid work hours per day'] = df['Paid work hours per day'].astype(float)
    df["Kit"] = df["Kit"].astype(str)
    df['kits_per_hour'] = df['Kit per day']/df['Paid work hours per day']
    speeds_per_hour = dict(zip(df["Kit"], df["kits_per_hour"]))
    return speeds_per_hour

def read_personnel_requirement_data():
    """Read personnel requirement data from Kits Calculation"""
    path = PATHS['data']['csv']['kits_calculation']
    df = pd.read_csv(path, usecols=["Kit", "Humanizer", "UNICEF staff"], encoding='latin1')
    
    # Clean the data by handling special whitespace characters like \xa0 (non-breaking space)
    def clean_and_convert_to_float(value):
        if pd.isna(value):
            return 0.0
        
        # Convert to string and strip all kinds of whitespace (including \xa0)
        clean_value = str(value).strip()
        
        # If empty after stripping, return 0
        if clean_value == '' or clean_value == 'nan':
            return 0.0
        
        try:
            return float(clean_value)
        except ValueError as e:
            print(f"Warning: Could not convert '{repr(value)}' to float, setting to 0. Error: {e}")
            return 0.0
    
    df["Humanizer"] = df["Humanizer"].apply(clean_and_convert_to_float)
    df["UNICEF staff"] = df["UNICEF staff"].apply(clean_and_convert_to_float)
    df["Kit"] = df["Kit"].astype(str)
    
    return df


def get_production_order_data():
    """
    Extract production order information from hierarchy.
    
    Returns:
        tuple: (kit_levels, dependencies, priority_order)
            - kit_levels: {kit_id: level} where level 0=prepack, 1=subkit, 2=master
            - dependencies: {kit_id: [dependency_list]}
            - priority_order: [kit_ids] sorted by production priority
    """
    path = PATHS['data']['hierarchy']['kit_hierarchy']
    with open(path, 'r', encoding='utf-8') as f:
        hierarchy = json.load(f)
    
    kit_levels = {}
    dependencies = {}
    
    # Process hierarchy to extract levels and dependencies
    for master_id, master_data in hierarchy.items():
        # Master kits are level 2
        kit_levels[master_id] = 2
        dependencies[master_id] = master_data.get('dependencies', [])
        
        # Process subkits (level 1)
        for subkit_id, subkit_data in master_data.get('subkits', {}).items():
            kit_levels[subkit_id] = 1
            dependencies[subkit_id] = subkit_data.get('dependencies', [])
            
            # Process prepacks under subkits (level 0)
            for prepack_id in subkit_data.get('prepacks', []):
                if prepack_id not in kit_levels:  # Avoid overwriting if already exists
                    kit_levels[prepack_id] = 0
                    dependencies[prepack_id] = []
        
        # Process direct prepacks under master (level 0)
        for prepack_id in master_data.get('direct_prepacks', []):
            if prepack_id not in kit_levels:  # Avoid overwriting if already exists
                kit_levels[prepack_id] = 0
                dependencies[prepack_id] = []
    
    # Create priority order: prepacks first, then subkits, then masters
    priority_order = []
    
    # Level 0: Prepacks (highest priority)
    prepacks = [kit for kit, level in kit_levels.items() if level == 0]
    priority_order.extend(sorted(prepacks))
    
    # Level 1: Subkits (medium priority)
    subkits = [kit for kit, level in kit_levels.items() if level == 1]
    priority_order.extend(sorted(subkits))
    
    # Level 2: Masters (lowest priority)
    masters = [kit for kit, level in kit_levels.items() if level == 2]
    priority_order.extend(sorted(masters))
    
    return kit_levels, dependencies, priority_order
    #{kit_id: level} where level 0=prepack, 1=subkit, 2=master
    #{kit_id: [dependency_list]}
    #priority_order: [kit_ids] sorted by production priority
    



if __name__ == "__main__":
    employee_data = read_employee_data()
    print("employee data")
    print(employee_data)
    print("line speed data",read_package_speed_data())
    
