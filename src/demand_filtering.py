"""
Demand Data Filtering Module

This module filters demand data to include only products that are ready for optimization.
Excludes products that:
1. Have no line type assignments (virtual masters)
2. Have zero staffing requirements (both Humanizer and UNICEF staff = 0)

The filtered data is used by the optimization system.
"""

import pandas as pd
from typing import Dict, List, Tuple
from datetime import timedelta
from src.preprocess import extract
from src.config.optimization_config import get_line_cnt_per_type
from src.config.constants import DefaultConfig

class DemandFilter:
    """
    Filters demand data to include only products ready for optimization
    """
    
    def __init__(self):
        self.demand_data = None
        self.material_descriptions = None
        self.kit_levels = None
        self.kit_dependencies = None
        self.line_assignments = None
        self.team_requirements = None
        self.speed_data = None
        self.date_span = None
        
        
    def load_data(self, start_date, force_reload=False):
        """
        Load all necessary data for filtering
        
        Args:
            start_date: Start date for demand data filtering (end_date is calculated as start_date + DAYS_LENGTH)
            force_reload: If True, force reload data even if cached
        """
        try:
            # Skip loading if data already exists and not forcing reload
            if not force_reload and self.demand_data is not None:
                print("📊 Using cached filter data (set force_reload=True to refresh)")
                return True
                
            print("🔄 Loading fresh filtering data...")
            # Calculate end_date from start_date + DAYS_LENGTH
            import datetime
            if isinstance(start_date, datetime.datetime):
                start_dt = start_date
            else:
                start_dt = datetime.datetime.combine(start_date, datetime.datetime.min.time())
            
            # # Calculate end_date using DAYS_LENGTH
            # end_dt = start_dt + timedelta(days=DefaultConfig.DAYS_LENGTH - 1)
            
            # # Use DAYS_LENGTH directly
            # days_diff = DefaultConfig.DAYS_LENGTH
            # self.date_span = list(range(1, days_diff + 1))
            
            # print(f"🗓️ DEMAND FILTERING DATE: Using {start_date.date() if hasattr(start_date, 'date') else start_date} to {end_dt.date() if hasattr(end_dt, 'date') else end_dt} ({len(self.date_span)} days)")
            
            # Load demand data directly from extract
            demand_df = extract.read_orders_data(start_date=start_date)
            self.demand_data = demand_df.groupby('Material Number')["Order quantity (GMEIN)"].sum().to_dict()
            
            # Store material descriptions (take first occurrence per Material Number)
            self.material_descriptions = demand_df.groupby('Material Number')['Material description'].first().to_dict()
            
            # Load kit hierarchy data
            kit_levels, dependencies, _ = extract.get_production_order_data()
            self.kit_levels = kit_levels
            self.kit_dependencies = dependencies
            
            # Load line assignments from kit line match data
            kit_line_match = extract.read_kit_line_match_data()
            kit_line_match_dict = kit_line_match.set_index("kit_name")["line_type"].to_dict()
            
            # Convert string line names to numeric IDs
            from src.config.constants import LineType
            line_name_to_id = {
                "long line": LineType.LONG_LINE,
                "mini load": LineType.MINI_LOAD,
                "miniload": LineType.MINI_LOAD,
                "Long_line": LineType.LONG_LINE,
                "Mini_load": LineType.MINI_LOAD,
            }
            
            self.line_assignments = {}
            for kit, line_name in kit_line_match_dict.items():
                if isinstance(line_name, str) and line_name.strip():
                    line_id = line_name_to_id.get(line_name.strip())
                    if line_id is not None:
                        self.line_assignments[kit] = line_id
                elif isinstance(line_name, (int, float)) and not pd.isna(line_name):
                    self.line_assignments[kit] = int(line_name)
            
            # Load team requirements from Kits Calculation data
            kits_df = extract.read_personnel_requirement_data()
            self.team_requirements = {
                'UNICEF Fixed term': kits_df.set_index('Kit')['UNICEF staff'].to_dict(),
                'Humanizer': kits_df.set_index('Kit')['Humanizer'].to_dict()
            }
            
            # Load production speed data
            self.speed_data = extract.read_package_speed_data()
            
            print(f"✅ Filtering data loaded: {len(self.demand_data)} products with demand, {len(self.speed_data)} with speed data")
            return True
            
        except Exception as e:
            print(f"Error loading data for filtering: {str(e)}")
            return False
        
    
    def non_virtual_master_filter(self, product_id: str) -> Tuple[str, bool]:
        """
        Classify product type and check if it's a Non virtual master.
        
        Returns:
            Tuple[str, bool]: (product_type, is_non_virtual_master)
        """
        if product_id in self.kit_levels:
            level = self.kit_levels[product_id]
            
            if level == 0:
                return "prepack", False
            elif level == 1:
                return "subkit", False
            elif level == 2:
                # Check if this master is non_virtual (no dependencies, or only prepack dependencies)
                dependencies = self.kit_dependencies.get(product_id, [])
                is_non_virtual = len(dependencies) == 0 or all(
                    self.kit_levels.get(dep_id, -1) == 0 for dep_id in dependencies
                )
                return "master", is_non_virtual
            else:
                return "unknown", False
        else:
            return "unclassified", False

    def _get_line_type_capacity(self, line_type: int) -> int:
        """
        Calculate the total capacity in hours for a specific line type.
        
        Args:
            line_type: The line type ID (e.g., 6 for Long Line, 7 for Mini Load)
            
        Returns:
            int: Total capacity in hours for this line type
        """
        from src.config.optimization_config import get_max_hour_per_shift_per_person, get_date_configuration
        from src.config.constants import DefaultConfig, ShiftType
        import streamlit as st
        
        # # Check if date_span is initialized
        # if self.date_span is None:
        #     raise ValueError("❌ date_span is not initialized. Call load_data() first.")
        
        line_cnt_per_type = get_line_cnt_per_type()
        max_hours_per_shift_dict = get_max_hour_per_shift_per_person()
        
        # Get active shifts from session state, default to regular + overtime
        active_shifts = st.session_state.get('selected_shifts', [ShiftType.REGULAR, ShiftType.OVERTIME])
        _, _, _, _, date_span = get_date_configuration()
        
        # Get line count for this specific line type
        line_count = line_cnt_per_type.get(line_type, 0)
        
        # Calculate total hours per day (sum of all active shift hours)
        total_hours_per_day = sum(max_hours_per_shift_dict.get(shift, 0) for shift in active_shifts)
        
        # Calculate available capacity hours using stored date_span
        # Available hours = line_count × total_hours_per_day × days_in_period
        available_hours = line_count * total_hours_per_day * len(date_span)
        
        return available_hours

    # def get_maximum_packaging_capacity(self) -> int:
    #     """
    #     Get the maximum packaging capacity across all line types.
        
    #     Returns:
    #         int: Maximum total capacity in hours across all lines
    #     """
    #     from src.config.optimization_config import get_line_cnt_per_type
        
    #     line_cnt_per_type = get_line_cnt_per_type()
    #     total_capacity = 0
        
    #     for line_type, line_count in line_cnt_per_type.items():
    #         if line_count > 0:  # Only count active lines
    #             line_capacity = self._get_line_type_capacity(line_type)
    #             total_capacity += line_capacity
        
    #     return total_capacity

    def too_high_demand_filter(self, product_id: str) -> bool:
        """
        Check if the demand for a product is too high.
        
        A product has "too high demand" when the total processing hours needed
        exceeds the available capacity hours for the product's assigned line type.
        
        NOTE: This method assumes all prerequisite data is available (demand > 0,
        line assignment exists, speed data exists). The main filter function
        should handle these edge cases.
        
        Calculation:
        - Processing hours needed = demand_quantity / production_speed_per_hour
        - Available hours = line_count × hours_per_shift × shifts_per_day × days_in_period
        
        Args:
            product_id: The product ID to check
            
        Returns:
            bool: True if demand is too high (should be excluded), False otherwise
        """
        # Get demand for this product (assumes demand > 0, checked by main filter)
        demand = self.demand_data.get(product_id, 0)
        if demand <= 0:
            return False
        # Get line assignment for this product (assumes exists, checked by main filter)
        if self.line_assignments is None or product_id not in self.line_assignments:
            return False
        line_type = self.line_assignments.get(product_id)
        
        # Get production speed data (assumes exists, checked by main filter)
        if self.speed_data is None or product_id not in self.speed_data:
            return False
        production_speed_per_hour = self.speed_data[product_id]
        
        # Calculate processing hours needed
        processing_hours_needed = demand / production_speed_per_hour
        
        # Get available capacity for this specific line type
        available_hours = self._get_line_type_capacity(line_type)
        
        # Check if processing hours needed exceeds available capacity
        is_too_high = processing_hours_needed > available_hours
        
        if is_too_high:
            print(f"⚠️  HIGH DEMAND WARNING: {product_id} needs {processing_hours_needed:.1f}h but only {available_hours:.1f}h available (line_type={line_type}, demand={demand}, speed={production_speed_per_hour:.1f}/h)")
        
        return is_too_high
    
    def is_product_ready_for_optimization(self, product_id: str) -> Tuple[bool, List[str]]:
        """
        Check if a single product is ready for optimization.
        1) Should have demand higher than 0
        2) Should be right type - non_virtual master, subkit, prepack
        3) Should have line assignment
        4) Should have staffing requirements
        5) Should have production speed data
        
        Returns:
            Tuple[bool, List[str]]: (is_ready, exclusion_reasons)
        """
        exclusion_reasons = []
        
        # Check if product has positive demand
        demand = self.demand_data.get(product_id, 0)
        if demand <= 0:
            exclusion_reasons.append("No demand or zero demand")
        
        # Classify product type
        product_type, is_non_virtual_master = self.non_virtual_master_filter(product_id)
        
        # Check line assignment logic
        has_line_assignment = product_id in self.line_assignments
        
        # For masters: non_virtual should have line assignment, virtual should NOT
        
        if product_type == "master":
            if is_non_virtual_master:
                if not has_line_assignment:
                    exclusion_reasons.append("non_virtual master missing line assignment")
                elif self.line_assignments.get(product_id) != 6:  # 6 = LONG_LINE
                    exclusion_reasons.append("non_virtual master should have long line assignment")
            else:
                # Virtual masters should NOT have line assignment (excluded from production)
                exclusion_reasons.append("Virtual master (excluded from production)")
        else:
            # For subkits and prepacks, check normal line assignment
            if not has_line_assignment:
                exclusion_reasons.append("No line assignment")
        
        # Check staffing requirements
        unicef_team = self.team_requirements.get('UNICEF Fixed term', {})
        humanizer_team = self.team_requirements.get('Humanizer', {})
        has_team_data = (product_id in unicef_team) or (product_id in humanizer_team)
        unicef_staff = unicef_team.get(product_id, 0)
        humanizer_staff = humanizer_team.get(product_id, 0)
        total_staff = unicef_staff + humanizer_staff
        
        if not has_team_data:
            exclusion_reasons.append("No data in TEAM_REQ_PER_PRODUCT")
        elif total_staff == 0:
            exclusion_reasons.append("Zero staffing requirements")
        
        # Check production speed data
        if self.speed_data is None or product_id not in self.speed_data:
            exclusion_reasons.append("Missing production speed data")
        
        # Check if demand is too high (only if we have all required data)
        if self.too_high_demand_filter(product_id):
            exclusion_reasons.append("Demand exceeds available production capacity")

        


        is_ready = len(exclusion_reasons) == 0
        return is_ready, exclusion_reasons
    
    def filter_products(self, start_date=None) -> Tuple[List[str], Dict[str, int], List[str], Dict[str, int]]:
        """
        Filter products into included and excluded lists based on optimization readiness.
        Uses is_product_ready_for_optimization() to check all criteria.
        
        Args:
            start_date: Start date for demand data (required if data not already loaded)
        
        Returns:
            Tuple containing:
            - included_products: List of product IDs ready for optimization
            - included_demand: Dict of {product_id: demand} for included products
            - excluded_products: List of product IDs excluded from optimization
            - excluded_demand: Dict of {product_id: demand} for excluded products
        """
        # If data not loaded, require start_date
        if self.demand_data is None:
            if start_date is None:
                raise ValueError("start_date is required when data is not already loaded")
            if not self.load_data(start_date):
                raise Exception("Failed to load data for filtering")
        
        included_products = []
        included_demand = {}
        excluded_products = []
        excluded_demand = {}
        excluded_details = {}
        
        for product_id, demand in self.demand_data.items():
            is_ready, exclusion_reasons = self.is_product_ready_for_optimization(product_id)
            
            if is_ready:
                included_products.append(product_id)
                included_demand[product_id] = demand

            else:
                excluded_products.append(product_id)
                excluded_demand[product_id] = demand
                excluded_details[product_id] = exclusion_reasons
        
        # Sort products for consistent output
        included_products.sort()
        excluded_products.sort()
        # Print data quality warnings for included products
        included_without_hierarchy = sum(1 for pid in included_products if self.non_virtual_master_filter(pid)[0] == "unclassified")
        if included_without_hierarchy > 0:
            print(f"\n⚠️  DATA QUALITY WARNING: {included_without_hierarchy} included products missing hierarchy data")
        
        return included_products, included_demand, excluded_products, excluded_demand
    
    def get_filtered_product_list(self, start_date=None) -> List[str]:
        """
        Get list of products ready for optimization
        
        Args:
            start_date: Start date for demand data (required if data not already loaded)
        """
        included_products, _, _, _ = self.filter_products(start_date)
        return included_products
    
    def get_filtered_demand_dictionary(self, start_date=None) -> Dict[str, int]:
        """
        Get demand dictionary for products ready for optimization
        
        Args:
            start_date: Start date for demand data (required if data not already loaded)
        """
        _, included_demand, _, _ = self.filter_products(start_date)
        return included_demand
    
    def get_line_assignments(self) -> Dict[str, int]:
        """
        Get line type assignments for all products.
        Must call load_data() first.
        
        Returns:
            Dict[str, int]: Dictionary mapping product ID to line type ID (6=Long Line, 7=Mini Load)
        """
        if self.line_assignments is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        return self.line_assignments
    
    def get_complete_product_analysis(self, start_date=None) -> Dict:
        """
        Get complete analysis of all products for visualization
        
        Args:
            start_date: Start date for demand data (required if data not already loaded)
        """
        included_products, included_demand, excluded_products, excluded_demand = self.filter_products(start_date)
        
        all_products = {**included_demand, **excluded_demand}
        product_details = {}
        
        # Load speed data for additional validation
        speed_data = None
        try:
            from src.config import optimization_config
            from src.preprocess import extract
            speed_data = extract.read_package_speed_data()
        except Exception as e:
            print(f"Warning: Could not load speed data for analysis: {e}")
        
        for product_id, demand in all_products.items():
            product_type, is_non_virtual_master = self.non_virtual_master_filter(product_id)
            is_ready, exclusion_reasons = self.is_product_ready_for_optimization(product_id)
            
            # Get staffing info
            unicef_staff = self.team_requirements.get('UNICEF Fixed term', {}).get(product_id, 0)
            humanizer_staff = self.team_requirements.get('Humanizer', {}).get(product_id, 0)
            
            # Get line assignment
            line_assignment = self.line_assignments.get(product_id)
            
            # Get production speed info
            has_speed_data = speed_data is not None and product_id in speed_data

            # too high demand
            has_too_high_demand = self.too_high_demand_filter(product_id)
            
            # Get material description
            material_description = self.material_descriptions.get(product_id, "N/A") if self.material_descriptions else "N/A"
            
            product_details[product_id] = {
                'demand': demand,
                'product_type': product_type,
                'material_description': material_description,
                'is_non_virtual_master': is_non_virtual_master,
                'is_included_in_optimization': is_ready,
                'exclusion_reasons': exclusion_reasons,
                'unicef_staff': unicef_staff,
                'humanizer_staff': humanizer_staff,
                'total_staff': unicef_staff + humanizer_staff,
                'line_assignment': line_assignment,
                'has_line_assignment': line_assignment is not None,
                'has_staffing': (unicef_staff + humanizer_staff) > 0,
                'has_hierarchy': product_type != "unclassified",
                'has_speed_data': has_speed_data,
                'has_too_high_demand': has_too_high_demand
            }
        
        # Calculate data quality statistics for included products
        included_without_speed = sum(1 for pid in included_products if not product_details[pid]['has_speed_data'])
        included_without_hierarchy = sum(1 for pid in included_products if not product_details[pid]['has_hierarchy'])
        
        # Count products excluded due to too high demand
        excluded_with_too_high_demand = sum(1 for pid in excluded_products if product_details[pid]['has_too_high_demand'])
        return {
            'included_count': len(included_products),
            'included_demand': sum(included_demand.values()),
            'excluded_count': len(excluded_products),
            'excluded_demand': sum(excluded_demand.values()),
            'total_products': len(all_products),
            'total_demand': sum(all_products.values()),
            'product_details': product_details,
            'non_virtual_masters_count': sum(1 for p in product_details.values() if p['is_non_virtual_master']),
            'included_products': included_products,
            'excluded_products': excluded_products,
            # Data quality metrics for included products
            'included_missing_speed_count': included_without_speed,
            'included_missing_hierarchy_count': included_without_hierarchy,
            'excluded_with_too_high_demand_count': excluded_with_too_high_demand
        }


# Test script when run directly

if __name__ == "__main__":
    # Test the filtering with dates from SINGLE SOURCE OF TRUTH
    from src.config.optimization_config import get_date_configuration
    
    # Get dates from centralized configuration
    demand_start_date, _, _, _, _ = get_date_configuration()
    print(f"Using dates from get_date_configuration(): {demand_start_date}")
    
    filter_instance = DemandFilter()
    included_products, included_demand, excluded_products, excluded_demand = filter_instance.filter_products(demand_start_date)
    
    print(f"\n=== FILTERING TEST RESULTS ===")
    print(f"Included products: {included_products[:5]}..." if len(included_products) > 5 else f"Included products: {included_products}")
    print(f"Excluded products: {excluded_products[:5]}..." if len(excluded_products) > 5 else f"Excluded products: {excluded_products}")
