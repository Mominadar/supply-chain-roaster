# ============================================================
# Feasibility Checker for Production Planning
# - Validates production plan feasibility before optimization
# - Checks team size constraints and time-based capacity
# ============================================================

from src.config.constants import LineType


class FeasibilityChecker:
    """
    Validates feasibility of production plans before optimization.
    
    Performs two main types of checks:
    1. Team size constraints: Ensures team size doesn't exceed line capacity
    2. Time-based constraints: Ensures available person-hours can meet demand
    """
    
    @staticmethod
    def check_production_feasibility(
        sorted_product_list,
        employee_type_list,
        team_req_per_product,
        demand_dictionary,
        kit_line_match_dict,
        per_product_speed,
        max_workers_line,
        max_employee_type_day,
        max_hours_shift,
        active_shift_list,
        date_span_list
    ):
        """
        Check feasibility of production plan before optimization.
        
        Performs two types of checks:
        1. Team size constraint: Ensures team size doesn't exceed line capacity
        2. Time-based constraint: Ensures available person-hours can meet demand
        
        Args:
            sorted_product_list: List of products sorted by hierarchy
            employee_type_list: List of employee types to consider
            team_req_per_product: Dict of employee requirements per product
            demand_dictionary: Dict of demand per product
            kit_line_match_dict: Dict mapping products to line types
            per_product_speed: Dict of production speed per product (units/hour)
            max_workers_line: Dict of max workers per line type
            max_employee_type_day: Dict of max employees per type per day
            max_hours_shift: Dict of max hours per shift
            active_shift_list: List of active shifts
            date_span_list: List of dates in planning period
        
        Returns:
            dict: Summary of feasibility check results with warnings and errors
        
        Raises:
            KeyError: If required data is missing for any product/employee type
        """
        print("\n[FEASIBILITY] Starting feasibility checks...")
        print("="*60)
        
        results = {
            'feasible': True,
            'warnings': [],
            'errors': [],
            'tight_capacity_products': []
        }
        
        # Check 1: Validate data existence for each product
        print("\n[CHECK 1] Validating products...")
        for i, p in enumerate(sorted_product_list):
        #     print(f"\n  Product {i+1}/{len(sorted_product_list)}: {p}")
            
            # Validate data existence
            try:
                FeasibilityChecker._validate_data_existence(
                    p, employee_type_list, team_req_per_product
                )
                
            except KeyError as e:
                error_msg = str(e)
                results['errors'].append(error_msg)
                results['feasible'] = False
                print(f"  [ERROR] {error_msg}")
                raise
        
        
        # Check 2: Time-based feasibility check across ALL products
        print("\n[CHECK 2] Time-based feasibility across ALL products...")
        time_warnings = FeasibilityChecker._check_time_based_feasibility(
            sorted_product_list, employee_type_list, team_req_per_product,
            demand_dictionary, per_product_speed,
            max_employee_type_day, max_hours_shift,
            active_shift_list, date_span_list
        )
        
        if time_warnings:
            results['warnings'].extend(time_warnings)
            # Extract products mentioned in warnings
            for warning in time_warnings:
                if "INFEASIBLE" in warning or "HIGH UTILIZATION" in warning:
                    results['feasible'] = False if "INFEASIBLE" in warning else results['feasible']
        
        print("\n" + "="*60)
        print("[FEASIBILITY] Feasibility checks completed")
        print(f"  Total warnings: {len(results['warnings'])}")
        print(f"  Total errors: {len(results['errors'])}")
        print(f"  Tight capacity products: {len(results['tight_capacity_products'])}")
        print("="*60 + "\n")
        
        return results
    
    @staticmethod
    def _validate_data_existence(product, employee_type_list, team_req_per_product):
        """
        Validate that required data exists for the product.
        
        Args:
            product: Product name to validate
            employee_type_list: List of employee types
            team_req_per_product: Dict of employee requirements per product
        
        Raises:
            KeyError: If data is missing
        """
        for e in employee_type_list:
            if e not in team_req_per_product:
                raise KeyError(
                    f"Employee type '{e}' not found in team requirements. "
                    f"Available: {list(team_req_per_product.keys())}"
                )
            if product not in team_req_per_product[e]:
                raise KeyError(
                    f"Product '{product}' not found in requirements for '{e}'"
                )

    
    @staticmethod
    def _check_time_based_feasibility(
        sorted_product_list, employee_type_list, team_req_per_product,
        demand_dictionary, per_product_speed,
        max_employee_type_day, max_hours_shift,
        active_shift_list, date_span_list
    ):
        """
        Check if available person-hours can meet total demand across ALL products.
        
        This calculates the total person-hours needed for each employee type
        to produce ALL products, then compares against available capacity.
        
        Args:
            sorted_product_list: List of all products to produce
            employee_type_list: List of employee types
            team_req_per_product: Dict of employee requirements per product
            demand_dictionary: Dict of demand per product
            per_product_speed: Dict of production speed per product
            max_employee_type_day: Dict of max employees per type per day
            max_hours_shift: Dict of max hours per shift
            active_shift_list: List of active shifts
            date_span_list: List of dates in planning period
        
        Returns:
            list: List of warning messages (empty if no issues)
        """
        warnings = []
        
        print("\nCalculating total person-hours needed across ALL products...")
        print("  " + "="*58)
        
        # Step 1: Calculate available person-hours for each employee type
        # Structure: {employee_type: total_hours_available}
        hours_available = {}
        for e in employee_type_list:
            total_hours = 0
            for t in date_span_list:
                employees_available_on_day = max_employee_type_day.get(e, {}).get(t, 0)
                shift_hours_per_day = sum(max_hours_shift[s] for s in active_shift_list)
                total_hours += employees_available_on_day * shift_hours_per_day
            hours_available[e] = total_hours
        
        print("\n  Available person-hours by employee type:")
        for e, hours in hours_available.items():
            print(f"    {e}: {hours:.1f}h (across {len(date_span_list)} days)")
        
        # Step 2: Calculate needed person-hours for each employee type across ALL products
        # Structure: {employee_type: {total: X, breakdown: [{product, demand, employees_needed, hours}, ...]}}
        hours_needed = {}
        for e in employee_type_list:
            hours_needed[e] = {
                'total': 0,
                'breakdown': []
            }
            
            for product in sorted_product_list:
                demand = demand_dictionary.get(product, 0)
                if demand == 0:
                    continue
                
                # Get production speed
                speed = per_product_speed.get(product, None)
                if speed is None:
                    continue
                
                # Hours per unit of product
                hours_per_unit = 1.0 / speed
                
                # Number of employees of this type needed per unit
                employees_of_type_per_unit = team_req_per_product[e][product]
                
                if employees_of_type_per_unit == 0:
                    continue  # This employee type not needed for this product
                
                # Calculate person-hours needed for this product
                # Formula: (employees of this type per unit) × (hours per unit) × (total units demanded)
                #
                # Example:
                #   - Product needs 2 workers of this type (employees_of_type_per_unit = 2)
                #   - Each unit takes 0.01 hours (hours_per_unit = 0.01)
                #   - Need 1000 units (demand = 1000)
                #   - Result = 2 × 0.01 × 1000 = 20 person-hours
                person_hours_for_product = employees_of_type_per_unit * hours_per_unit * demand
                
                hours_needed[e]['total'] += person_hours_for_product
                hours_needed[e]['breakdown'].append({
                    'product': product,
                    'demand': demand,
                    'employees_needed': employees_of_type_per_unit,
                    'hours': person_hours_for_product,
                    'speed': speed  # units per hour
                })
        
        # Step 3: Compare needed vs available and generate warnings
        print("\n  Needed person-hours by employee type (sum across all products):")
        for e in employee_type_list:
            print(f"\n  Employee Type: {e}")
            print("  " + "-"*58)
            
            needed = hours_needed[e]['total']
            available = hours_available[e]
            breakdown = hours_needed[e]['breakdown']
            
            # Print breakdown
            if breakdown:
                print(f"    Products requiring {e}:")
                for item in breakdown:
                    print(f"      - {item['product']}: {item['hours']:.1f}h "
                          f"({item['employees_needed']} workers × {item['demand']} units @ {item['speed']:.1f} units/hr)")
            else:
                print(f"    No products require {e}")
            
            # Print summary
            print(f"\n    TOTAL NEEDED: {needed:.1f} person-hours")
            print(f"    TOTAL AVAILABLE: {available:.1f} person-hours")
            
            # Check feasibility
            if available > 0:
                utilization_pct = (needed / available) * 100
                print(f"    UTILIZATION: {utilization_pct:.1f}%")
                
                if needed > available:
                    shortage = needed - available
                    warning = (
                        f"Employee type {e}: INFEASIBLE - Total needed ({needed:.1f}h) "
                        f"exceeds available capacity ({available:.1f}h). "
                        f"Shortage: {shortage:.1f} person-hours ({utilization_pct:.1f}% utilization)."
                    )
                    print(f"    ❌ [ERROR] {warning}")
                    warnings.append(warning)
                elif utilization_pct > 90:
                    warning = (
                        f"Employee type {e}: HIGH UTILIZATION - {utilization_pct:.1f}% "
                        f"({needed:.1f}h / {available:.1f}h). May be tight."
                    )
                    print(f"    ⚠️  [WARN] {warning}")
                    warnings.append(warning)
                else:
                    print(f"    ✅ Capacity OK")
            else:
                if needed > 0:
                    warning = f"Employee type {e}: No capacity available but {needed:.1f}h needed!"
                    print(f"    ❌ [ERROR] {warning}")
                    warnings.append(warning)
                else:
                    print(f"    ✅ No capacity needed")
        
        print("\n  " + "="*58)
        return warnings


# ============================================================
# Main function for testing and validation
# ============================================================

def main():
    """
    Main function to test feasibility checker with sample data.
    Run this file directly to validate the checker logic.
    """
    print("\n" + "="*80)
    print("FEASIBILITY CHECKER - Non_virtual TEST")
    print("="*80)
    
    # Sample data setup
    print("\n📋 Setting up sample test data...")
    
    # Products
    sorted_product_list = ['Kit_A', 'Kit_B', 'Kit_C']
    
    # Employee types
    employee_type_list = ['UNICEF Fixed term', 'Humanizer']
    
    # Team requirements per product
    # Format: {employee_type: {product: number_of_workers_needed}}
    team_req_per_product = {
        'UNICEF Fixed term': {
            'Kit_A': 2,  # Kit A needs 2 UNICEF workers
            'Kit_B': 1,  # Kit B needs 1 UNICEF worker
            'Kit_C': 3   # Kit C needs 3 UNICEF workers
        },
        'Humanizer': {
            'Kit_A': 1,  # Kit A needs 1 Humanizer
            'Kit_B': 2,  # Kit B needs 2 Humanizers
            'Kit_C': 1   # Kit C needs 1 Humanizer
        }
    }
    
    # Demand per product
    demand_dictionary = {
        'Kit_A': 1000,  # Need to produce 1000 units of Kit A
        'Kit_B': 500,   # Need to produce 500 units of Kit B
        'Kit_C': 800    # Need to produce 800 units of Kit C
    }
    
    # Product to line type mapping
    kit_line_match_dict = {
        'Kit_A': LineType.LONG_LINE,
        'Kit_B': LineType.LONG_LINE,
        'Kit_C': LineType.MINI_LOAD
    }
    
    # Production speed (units per hour)
    per_product_speed = {
        'Kit_A': 100,  # Can produce 100 units/hour
        'Kit_B': 50,   # Can produce 50 units/hour
        'Kit_C': 80    # Can produce 80 units/hour
    }
    
    # Max workers per line type
    max_workers_line = {
        LineType.LONG_LINE: 5,   # Long line can have max 5 workers
        LineType.MINI_LOAD: 4    # Mini load can have max 4 workers
    }
    
    # Max employees per type per day
    # Format: {employee_type: {day: max_employees}}
    date_span_list = [1, 2, 3, 4, 5]  # 5 days
    max_employee_type_day = {
        'UNICEF Fixed term': {1: 10, 2: 10, 3: 10, 4: 10, 5: 10},  # 10 UNICEF workers available each day
        'Humanizer': {1: 8, 2: 8, 3: 8, 4: 8, 5: 8}  # 8 Humanizers available each day
    }
    
    # Max hours per shift
    from src.config.constants import ShiftType
    max_hours_shift = {
        ShiftType.REGULAR: 8,   # Regular shift: 8 hours
        ShiftType.EVENING: 6,   # Evening shift: 6 hours
        ShiftType.OVERTIME: 4   # Overtime shift: 4 hours
    }
    
    # Active shifts
    active_shift_list = [ShiftType.REGULAR, ShiftType.EVENING]
    
    print("\n📊 Test Data Summary:")
    print(f"  Products: {len(sorted_product_list)}")
    print(f"  Employee types: {len(employee_type_list)}")
    print(f"  Planning days: {len(date_span_list)}")
    print(f"  Active shifts: {len(active_shift_list)}")
    print(f"  Total demand: {sum(demand_dictionary.values())} units")
    
    # Calculate expected needs manually for verification
    print("\n🧮 Manual calculation verification:")
    for e in employee_type_list:
        print(f"\n  {e}:")
        total_needed = 0
        for p in sorted_product_list:
            demand = demand_dictionary[p]
            speed = per_product_speed[p]
            workers = team_req_per_product[e][p]
            hours_per_unit = 1.0 / speed
            hours_for_product = workers * hours_per_unit * demand
            total_needed += hours_for_product
            print(f"    {p}: {workers} workers × {demand} units @ {speed:.1f} units/hr = {hours_for_product:.1f}h")
        
        # Calculate available
        available = 0
        for day in date_span_list:
            workers_per_day = max_employee_type_day[e][day]
            hours_per_day = sum(max_hours_shift[s] for s in active_shift_list)
            available += workers_per_day * hours_per_day
        
        print(f"    → TOTAL NEEDED: {total_needed:.1f}h")
        print(f"    → TOTAL AVAILABLE: {available:.1f}h ({len(date_span_list)} days × {sum(max_hours_shift[s] for s in active_shift_list)}h/day × {max_employee_type_day[e][1]} workers)")
        print(f"    → UTILIZATION: {(total_needed/available*100):.1f}%")
    
    # Run feasibility check
    print("\n" + "="*80)
    print("🔍 RUNNING FEASIBILITY CHECK")
    print("="*80)
    
    results = FeasibilityChecker.check_production_feasibility(
        sorted_product_list=sorted_product_list,
        employee_type_list=employee_type_list,
        team_req_per_product=team_req_per_product,
        demand_dictionary=demand_dictionary,
        kit_line_match_dict=kit_line_match_dict,
        per_product_speed=per_product_speed,
        max_workers_line=max_workers_line,
        max_employee_type_day=max_employee_type_day,
        max_hours_shift=max_hours_shift,
        active_shift_list=active_shift_list,
        date_span_list=date_span_list
    )
    
    # Print results summary
    print("\n" + "="*80)
    print("📈 RESULTS SUMMARY")
    print("="*80)
    print(f"  Feasible: {'✅ YES' if results['feasible'] else '❌ NO'}")
    print(f"  Warnings: {len(results['warnings'])}")
    print(f"  Errors: {len(results['errors'])}")
    
    if results['warnings']:
        print("\n  Warnings:")
        for i, warning in enumerate(results['warnings'], 1):
            print(f"    {i}. {warning}")
    
    if results['errors']:
        print("\n  Errors:")
        for i, error in enumerate(results['errors'], 1):
            print(f"    {i}. {error}")
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETED")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

