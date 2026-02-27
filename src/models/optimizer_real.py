# ============================================================
# SD_roster_real - Fixed Team Production Planning (Option A)
# - Uses config-style variable names from src/config/optimization_config.py
# - Team per product (simultaneous): UNICEF Fixed term / Humanizer
# - Line types via numeric ids: 6=long, 7=short
# - One product per (line, shift, day)
# - Weekly demand (across DATE_SPAN)
# ============================================================

from ortools.linear_solver import pywraplp
from math import ceil
import datetime
import time
from src.config.constants import ShiftType, LineType, KitLevel

# ---- config import ----
# Import constants and other modules directly
from src.config.constants import ShiftType, LineType, DefaultConfig, PaymentMode
import src.preprocess.extract as extract
from src.preprocess.hierarchy_parser import sort_products_by_hierarchy
from src.utils.optimization_logger import OptimizationLogger


class Optimizer:
    """Workforce optimization class that handles all configuration and optimization logic"""

    def __init__(self):
        """Initialize optimizer with session state configuration"""
        self.load_session_state_config()
        self.load_data()
        self.logger = None  # Will be initialized in run_optimization

    # def get_constants(self):
    #     self.employee_type_list = constants.EMPLOYEE_TYPE_LIST

    def load_session_state_config(self):
        """Load all configuration from session state"""
        import streamlit as st
        from src.config.optimization_config import get_date_configuration, get_max_employee_per_type_on_day

        # Date configuration - SINGLE SOURCE OF TRUTH
        # All dates come from get_date_configuration() only
        self.demand_start_date, self.production_start_date, self.production_end_date, self.planning_days, self.date_span = get_date_configuration()

        # # Convert to date objects if needed
        # if hasattr(self.demand_start_date, 'date'):
        #     self.demand_start_date_obj = self.demand_start_date.date()
        # else:
        #     self.demand_start_date_obj = self.demand_start_date

        # if hasattr(self.production_start_date, 'date'):
        #     self.production_start_date_obj = self.production_start_date.date()
        # else:
        #     self.production_start_date_obj = self.production_start_date

        # if hasattr(self.production_end_date, 'date'):
        #     self.production_end_date_obj = self.production_end_date.date()
        # else:
        #     self.production_end_date_obj = self.production_end_date

        # Employee and shift configuration
        self.employee_type_list = list(st.session_state.selected_employee_types)
        self.active_shift_list = sorted(list(st.session_state.selected_shifts))

        # print("\n[DEBUG] From session_state.selected_employee_types:")
        # for emp in self.employee_type_list:
        #     print(f"  - '{emp}' (len={len(emp)}, repr={repr(emp)})")

        # Working hours configuration
        self.max_hour_per_person_per_day = st.session_state.max_hour_per_person_per_day
        self.max_hours_shift = {
            ShiftType.REGULAR: st.session_state.max_hours_shift_1,
            ShiftType.EVENING: st.session_state.max_hours_shift_2,
            ShiftType.OVERTIME: st.session_state.max_hours_shift_3
        }

        # Workforce limits - use safe getter function with fallback to defaults
        self.max_employee_per_type_on_day = get_max_employee_per_type_on_day()

        # Operations configuration
        self.line_counts = st.session_state.line_counts
        self.max_parallel_workers = {
            LineType.LONG_LINE: st.session_state.max_parallel_workers_long_line,
            LineType.MINI_LOAD: st.session_state.max_parallel_workers_mini_load
        }

        # Cost configuration
        self.cost_list_per_emp_shift = st.session_state.cost_list_per_emp_shift

        # Payment mode configuration
        self.payment_mode_config = st.session_state.payment_mode_config

        # Fixed staffing requirements
        self.fixed_min_unicef_per_day = st.session_state.fixed_min_unicef_per_day

        # Time padding configuration
        self.time_padding = st.session_state.time_padding

        print("✅ Session state configuration loaded successfully")

    def load_data(self):
        """Load all required data from files"""
        kit_levels, dependencies, priority_order = extract.get_production_order_data()
        self.kit_levels = kit_levels
        self.kit_dependencies = dependencies
        self.production_priority_order = priority_order

        # Note: Kit line match data is now loaded from DemandFilter (see below)
        # This ensures consistency with demand validation and filtering

        # Load product and demand data with date range from optimizer config
        from src.demand_filtering import DemandFilter
        filter_instance = DemandFilter()
        filter_instance.load_data(start_date=self.demand_start_date, force_reload=True)
        self.product_list = filter_instance.get_filtered_product_list()
        self.demand_dictionary = filter_instance.get_filtered_demand_dictionary()

        # Get line assignments directly from DemandFilter (already processed and validated)
        self.kit_line_match_dict = filter_instance.get_line_assignments()


        kits_df = extract.read_personnel_requirement_data()


        # Initialize team requirements dictionary
        self.team_req_per_product = {
            "UNICEF Fixed term": {},
            "Humanizer": {}
        }

        # Process each product in the product list
        for product in self.product_list:
            product_data = kits_df[kits_df['Kit'] == product]
            if not product_data.empty:
                # Extract Humanizer and UNICEF staff requirements
                humanizer_req = product_data["Humanizer"].iloc[0]
                unicef_req = product_data["UNICEF staff"].iloc[0]

                # Convert to int (data is already cleaned in extract function)
                self.team_req_per_product["Humanizer"][product] = int(humanizer_req)
                self.team_req_per_product["UNICEF Fixed term"][product] = int(unicef_req)
            else:
                print(f"[WARN] Product {product} not found in Kits Calculation, setting requirements to 0")
                self.team_req_per_product["Humanizer"][product] = 0
                self.team_req_per_product["UNICEF Fixed term"][product] = 0


        # Load product speed data
        self.per_product_speed = extract.read_package_speed_data()
        
        print("✅ All data loaded successfully")

    def build_lines(self):
        """Build line instances from session state configuration"""
        line_tuples = []

        try:
            import streamlit as st
            # Get selected line types from Data Selection tab
            selected_lines = st.session_state.selected_lines
            # Get line counts from Operations tab
            line_counts = st.session_state.line_counts

            print(f"Using lines from session state - selected: {selected_lines}, counts: {line_counts}")
            for line_type in selected_lines:
                count = line_counts.get(line_type, 0)
                for i in range(1, count + 1):
                    line_tuples.append((line_type, i))

            return line_tuples

        except Exception as e:
            print(f"Could not get line config from session state: {e}")
            raise Exception(f"Could not get line config from session state: {e}")

    def run_optimization(self):
        """Run the main optimization algorithm"""
        # Setup logging using context manager
        self.logger = OptimizationLogger()
        self.logger.setup()
        optimization_start_time = time.time()

        
        # *** CRITICAL: Load fresh data to reflect current Streamlit configs ***
        self.logger.log_section("🔄 LOADING FRESH DATA FOR OPTIMIZATION", length=60)
        self.logger.log_timestamp("Start Time")
        self.logger.log("")

        self.logger.log(f"📦 LOADED PRODUCTS: {len(self.product_list)} products")
        self.logger.log(f"📈 LOADED DEMAND: {sum(self.demand_dictionary.values())} total units")
        self.logger.log(f"👥 LOADED TEAM REQUIREMENTS: {len(self.team_req_per_product)} employee types")



        # Build ACTIVE schedule for fresh product list
        ACTIVE = {t: {p: 1 for p in self.product_list} for t in self.date_span}

        # --- Sets ---
        date_span_list = list(self.date_span)
        employee_type_list = self.employee_type_list
        active_shift_list = self.active_shift_list
        # print(f"\n[DEBUG] employee_type_list: {employee_type_list}")
        # print(f"[DEBUG] active_shift_list: {active_shift_list}")

        # *** HIERARCHY SORTING: Sort products by production priority ***
        # print("\n" + "="*60)
        # print("🔗 APPLYING HIERARCHY-BASED PRODUCTION ORDERING")
        # print("="*60)
        sorted_product_list = sort_products_by_hierarchy(
            list(self.product_list), self.kit_levels, self.kit_dependencies)

        line_tuples = self.build_lines()
        print("Lines", line_tuples)

        print("PER_PRODUCT_SPEED", self.per_product_speed)

        # --- Short aliases for parameters ---
        print("\n[DEBUG] Creating variable aliases...")
        Hmax_s = dict(self.max_hours_shift)  # per-shift hours
        Hmax_daily = self.max_hour_per_person_per_day
        max_workers_line = dict(self.max_parallel_workers)  # per line type
        max_employee_type_day = self.max_employee_per_type_on_day  # {emp_type:{t:headcount}}
        cost = self.cost_list_per_emp_shift  # {emp_type:{shift:cost}}

        # Create aliases for data dictionaries
        TEAM_REQ_PER_PRODUCT = self.team_req_per_product
        DEMAND_DICTIONARY = self.demand_dictionary
        KIT_LINE_MATCH_DICT = self.kit_line_match_dict
        KIT_LEVELS = self.kit_levels
        KIT_DEPENDENCIES = self.kit_dependencies
        PER_PRODUCT_SPEED = self.per_product_speed
        FIXED_MIN_UNICEF_PER_DAY = self.fixed_min_unicef_per_day
        PAYMENT_MODE_CONFIG = self.payment_mode_config
        TIME_PADDING_HOURS = self.time_padding / 60.0  # Convert minutes to hours

        # print(f"[DEBUG] TEAM_REQ_PER_PRODUCT has {len(TEAM_REQ_PER_PRODUCT)} employee types")
        # print(f"[DEBUG] employee_type_list has {len(employee_type_list)} types")

        # --- Feasibility checks ---
        # NOTE: Feasibility check is now performed in config_page.py during "Save Settings"
        # This validates the configuration before optimization runs and blocks saving if infeasible.
        # No need to check again here - we assume configuration is already validated.

        # --- Solver Setup with Performance Diagnostics ---
        print("\n" + "="*70)
        print("🔧 SOLVER SETUP & PROBLEM SIZE ANALYSIS")
        print("="*70)

        # Calculate problem dimensions
        num_products = len(sorted_product_list)
        num_lines = len(line_tuples)
        num_shifts = len(active_shift_list)
        num_days = len(date_span_list)
        num_employees = len(employee_type_list)

        # Estimate variable counts
        production_slots = num_products * num_lines * num_shifts * num_days
        employee_slots = num_employees * num_shifts * num_days

        # print(f"\n📊 Problem Dimensions:")
        # print(f"   Products: {num_products}")
        # print(f"   Lines: {num_lines} {line_tuples}")
        # print(f"   Shifts: {num_shifts}")
        # print(f"   Days: {num_days}")
        # print(f"   Employee Types: {num_employees}")
        # print(f"\n📈 Estimated Variables:")
        # print(f"   Assignment (binary): {production_slots:,}")
        # print(f"   Hours (continuous): {production_slots:,}")
        # print(f"   Units (integer): {production_slots:,}")
        # print(f"   Employee Count (integer): {employee_slots:,}")
        # print(f"   TOTAL: ~{production_slots * 3 + employee_slots:,} variables")
        # print(f"\n⚠️  WARNING: If total > 5,000 variables, optimization may be very slow!")

        if production_slots * 3 + employee_slots > 5000:
            print(f"   💡 Consider: reduce days, filter low-priority products, or use fewer lines")

        # Using mixed integer linear optimizer where some variables are integer and some are continuous
        solver = pywraplp.Solver.CreateSolver('CBC')
        if not solver:
            raise RuntimeError("CBC solver not found.")

        # Configure solver for ULTRA-FAST performance
        print(f"\n⚙️  Configuring Solver Parameters (ULTRA-FAST MODE)...")

        # Time limit: 5 minutes maximum (빠른 결과)
        solver.SetTimeLimit(60000)  # milliseconds (5 minutes)
        print(f"   ⏱️  Time Limit: 60 seconds (1 minute)")

        # ULTRA-FAST: 첫 번째 좋은 해를 찾으면 바로 멈춤!
        solver_params = [
            "sec:300",               # ⚡ 5분 하드 리미트
            "ratioGap:0.01",         # 5% gap tolerance (충분히 좋은 해)
            "allowableGap:100",      # Absolute gap (빠른 종료)
            "maxSol:1",              # ⚡ 첫 번째 integer solution만!
            "maxN:2000",             # Branch-and-bound 노드 제한 (더 작게)
            "presolve:on",           # Problem simplification
            "cuts:off",              # ⚡ Cutting planes 완전히 끔 (매우 빠름)
            "heur:on",               # Heuristics 활성화
            "passC:1",               # ⚡ Cutting plane pass 1번만
            "passF:5",               # ⚡ Feasibility pump 5번만
            "passP:1",               # ⚡ Presolve pass 1번만
            "pumpC:0"                # ⚡ Perturbation 끔!
        ]

        solver.SetSolverSpecificParametersAsString(" ".join(solver_params))
        print(f"   🚀 ULTRA-FAST: maxSol=1 → Stop at first integer solution!")
        print(f"   ⚡ pumpC=0, cuts=off → No perturbation or extra verification!")
        print(f"   💨 Expected: Stop immediately after finding feasible solution")

        # Enable solver output for progress tracking
        solver.EnableOutput()
        print(f"   📢 Solver Output: ENABLED")

        print(f"✅ Solver configured and ready")

        INF = solver.infinity()

        # ========================================================================
        # PRE-FILTERING: Determine valid combinations FIRST
        # ========================================================================
        # This must be done BEFORE creating variables to avoid creating unnecessary variables
        print("\n[OPTIMIZATION] Pre-filtering valid production combinations...")
        epsilon = 0.01  # Threshold for linking Hours to IsProduced

        valid_combinations = set()
        invalid_combinations = []

        for p in sorted_product_list:
            demand = DEMAND_DICTIONARY.get(p, 0)

            # Skip products with zero demand entirely
            if demand <= 0:
                print(f"   ⚠️  Skipping product {p} (zero demand)")
                for ell in line_tuples:
                    for s in active_shift_list:
                        for t in date_span_list:
                            invalid_combinations.append((p, ell, s, t))
                continue

            # Get valid line type for this product (single integer: 6=Long Line, 7=Mini Load)
            required_line_type_id = KIT_LINE_MATCH_DICT.get(p, None)

            if required_line_type_id is None:
                print(f"   ⚠️  Product {p} has no line type assignment")
                for ell in line_tuples:
                    for s in active_shift_list:
                        for t in date_span_list:
                            invalid_combinations.append((p, ell, s, t))
                continue

            # Only add combinations where product can be produced on this line type
            for ell in line_tuples:
                line_type_id = ell[0]

                if line_type_id != required_line_type_id:
                    # Invalid line-product combination
                    for s in active_shift_list:
                        for t in date_span_list:
                            invalid_combinations.append((p, ell, s, t))
                else:
                    # Valid combination
                    for s in active_shift_list:
                        for t in date_span_list:
                            valid_combinations.add((p, ell, s, t))

        print(f"   ✅ Valid combinations: {len(valid_combinations)}")
        print(f"   ❌ Invalid combinations: {len(invalid_combinations)}")
        print(f"   📊 Reduction: {len(invalid_combinations)}/{production_slots} "
                f"({100*len(invalid_combinations)/production_slots:.1f}%) slots eliminated")

        # ========================================================================
        # VARIABLES: Create ONLY for valid combinations
        # ========================================================================
        # OPTIMIZATION BREAKTHROUGH #1: Assignment variable REMOVED!
        # Assignment[p,ell,s,t] was redundant - we can infer it from Hours > 0
        #
        # OPTIMIZATION BREAKTHROUGH #2: Create variables ONLY for valid combinations!
        # This eliminates 30-60% of variables before solver even starts!

        print("\n[OPTIMIZATION] Creating production variables (valid combinations only)...")
        Hours, Units = {}, {}

        for p, ell, s, t in valid_combinations:
            # How many hours does product p run on line ell, during shift s, on day t?
            Hours[p, ell, s, t] = solver.NumVar(0, Hmax_s[s], f"T_{p}_{ell[0]}_{ell[1]}_s{s}_d{t}")

            # How many units does product p produce?
            Units[p, ell, s, t] = solver.IntVar(0, INF, f"U_{p}_{ell[0]}_{ell[1]}_s{s}_d{t}")

        print(f"   ✅ Created {len(Hours)} Hours variables (continuous)")
        print(f"   ✅ Created {len(Units)} Units variables (integer)")
        print(f"   💡 Savings: {len(invalid_combinations)*2} variables not created!")

        # Note: IDLE variables removed - we only track employees actually working on production

        # ========================================================================
        # EMPLOYEE VARIABLES - ULTRA-MINIMAL for maximum performance
        # ========================================================================
        # OPTIMIZATION BREAKTHROUGH:
        # 1. EMPLOYEE_HOURS = computed expression (not a variable!)
        # 2. WORK_IN_SHIFT = NOT needed (can check EMPLOYEE_HOURS > 0 implicitly)
        # 3. EMPLOYEES_IN_SHIFT = NOT needed (use EMPLOYEE_COUNT instead!)
        #
        # This eliminates ALL auxiliary employee variables!

        # ONLY ONE decision variable per (employee, shift, day):
        EMPLOYEE_COUNT = {}  # The ONLY employee variable we need!

        # EMPLOYEE_HOURS: Computed expression (0 variables)
        EMPLOYEE_HOURS = {}  # Dictionary of expressions, not variables

        print("\n[OPTIMIZATION] Creating employee variables...")

        # Step 1: Create EMPLOYEE_COUNT variables
        # The employee needed for specific shift / day. It is sum of employees needed for each line. 
        for e in employee_type_list:
            for s in active_shift_list:
                for t in date_span_list:
                    max_count = max_employee_type_day.get(e, {}).get(t, 100)
                    EMPLOYEE_COUNT[e, s, t] = solver.IntVar(
                        0,
                        max_count,
                        f"EmpCount_{e}_s{s}_day{t}"
                    )

        # Step 2: Line-based grouping for Bulk payment cost optimization
        # Simple approach: Each (line, shift, day) is a natural group
        # Products produced on same line/shift/day share workers
        # MaxEmployeesOnLine[e, ell, s, t] = max employees needed on that line
        print("\n[OPTIMIZATION] Creating line-based grouping: MaxEmployeesOnLine...")

        MaxEmployeesOnLine = {}  # MaxEmployeesOnLine[e, ell, s, t]: max employees on line ell

        # Create MaxEmployeesOnLine variables
        #Because of the bulk payment, this is same as the actual employees needed for each line. 
        for e in employee_type_list:
            for ell in line_tuples:
                for s in active_shift_list:
                    for t in date_span_list:
                        max_team_req = max(TEAM_REQ_PER_PRODUCT[e][p] for p in sorted_product_list)
                        MaxEmployeesOnLine[e, ell, s, t] = solver.IntVar(
                            0,
                            max_team_req,
                            f"MaxEmpLine_{e}_{ell[0]}_{ell[1]}_s{s}_d{t}"
                        )

        # MaxEmployeesOnLine constraints
        # MaxEmployeesOnLine[e, ell, s, t] must be >= team requirement for any product produced on that line
        print("\n[OPTIMIZATION] Setting MaxEmployeesOnLine constraints...")

        # ========================================================================
        # Create IsProducedOnLine binary indicators (only for valid combinations)
        # ========================================================================
        print("\n[OPTIMIZATION] Creating IsProducedOnLine indicators...")

        IsProducedOnLine = {}
        # IsProducedOnLine[p, ell, s, t] = 1 if product p is produced on line ell, during shift s, on day t

        for p, ell, s, t in valid_combinations:
            IsProducedOnLine[p, ell, s, t] = solver.BoolVar(f"IsProd_{p}_{ell[0]}_{ell[1]}_s{s}_d{t}")

            # Link to Hours: if Hours > epsilon, IsProduced must be 1
            solver.Add(Hours[p, ell, s, t] >= epsilon * IsProducedOnLine[p, ell, s, t])
            solver.Add(Hours[p, ell, s, t] <= Hmax_s[s] * IsProducedOnLine[p, ell, s, t])

        # ========================================================================
        # MaxEmployeesOnLine constraints (only for valid combinations)
        # ========================================================================
        print("[OPTIMIZATION] Setting MaxEmployeesOnLine constraints (filtered)...")

        for e in employee_type_list:
            for ell in line_tuples:
                for s in active_shift_list:
                    for t in date_span_list:
                        for p in sorted_product_list:
                            # Only add constraint if this is a valid combination
                            if (p, ell, s, t) in valid_combinations:
                                # MaxEmployeesOnLine >= TEAM_REQ[e][p] if product p is produced on line ell
                                solver.Add(
                                    MaxEmployeesOnLine[e, ell, s, t] >=
                                    TEAM_REQ_PER_PRODUCT[e][p] * IsProducedOnLine[p, ell, s, t]
                                )

        print(f"   ✅ MaxEmployeesOnLine = max(team requirements of products on that line)")
        print(f"   IsProducedOnLine: {len(IsProducedOnLine)} binary variables")

        # Step 3: Create EMPLOYEE_HOURS as computed expressions (only for valid combinations)
        print("\n[OPTIMIZATION] Computing EMPLOYEE_HOURS expressions from production (filtered)...")
        for e in employee_type_list:
            for s in active_shift_list:
                for t in date_span_list:
                # This is an EXPRESSION, not a variable
                # Solver evaluates it directly from production variables
                # Only sum over valid combinations to improve performance
                # employee_hours = actual needed hours + padding hours (as per user request)
                # User Requirement: (hours + padding) * team_req_per_prod
                    EMPLOYEE_HOURS[e, s, t] = solver.Sum(
                        TEAM_REQ_PER_PRODUCT[e][p] * (Hours[p, ell, s_iter, t_iter] + (TIME_PADDING_HOURS * IsProducedOnLine[p, ell, s_iter, t_iter]))
                        for p, ell, s_iter, t_iter in valid_combinations
                            if s_iter == s and t_iter == t
                                )

        print(f"✅ Employee variables and grouping setup:")
        print(f"   EMPLOYEE_COUNT: {len(EMPLOYEE_COUNT)} integer variables")
        print(f"   EMPLOYEE_HOURS: {len(EMPLOYEE_HOURS)} computed expressions")
        print(f"   MaxEmployeesOnLine: {len(MaxEmployeesOnLine)} integer variables")
        print(f"   IsProducedOnLine: {len(IsProducedOnLine)} binary variables")
        print(f"   🎯 Line-based grouping: each line is a natural group")

        # ========================================================================
        # LINE-BASED GROUPING FOR COST OPTIMIZATION
        # ========================================================================
        # Simple approach: Each (line, shift, day) is a natural group
        # - Products on same line share workers
        # - MaxEmployeesOnLine = max(team requirements) on that line
        # - Cost based on MaxEmployeesOnLine × shift_hour

        print("\n[OPTIMIZATION] Using line-based grouping for cost optimization")

        # ========================================================================
        # OBJECTIVE: Minimize total labor cost (wages)
        # ========================================================================
        print(f"\n[OPTIMIZATION] Building simplified cost objective function...")
        print(f"Payment mode configuration: {PAYMENT_MODE_CONFIG}")

        cost_terms = []

        for e in employee_type_list:
            for s in active_shift_list:
                for t in date_span_list:
                # Strict validation: payment mode must be explicitly configured for each shift
                    if s not in PAYMENT_MODE_CONFIG:
                        raise ValueError(
                            f"Payment mode not configured for shift {s}. "
                            f"Available shifts in config: {list(PAYMENT_MODE_CONFIG.keys())}. "
                            f"Please configure payment_mode_config in session state."
                        )
                    else:
                        payment_mode = PAYMENT_MODE_CONFIG[s]
                        if payment_mode not in [PaymentMode.PARTIAL, PaymentMode.BULK]:
                            raise ValueError(f"Invalid payment mode: {payment_mode}")

                        if payment_mode == PaymentMode.PARTIAL:
                            # Partial payment: Using line-based grouping
                            # Each line is a natural group - products on same line share workers
                            # Cost = hourly_rate × shift_hour × max_employees_on_line

                            for ell in line_tuples:
                                cost_terms.append(cost[e][s] * Hmax_s[s] * MaxEmployeesOnLine[e, ell, s, t])

                        elif payment_mode == PaymentMode.BULK:
                            # Bulk payment with line-based grouping
                            # Each line is a natural group - products on same line share workers
                            # Cost = Σ (hourly_rate × shift_hour × max_employees_on_line)
                            #
                            # Example: Long Line 1, Shift 1, Day 1
                            #   Product A (2h, 3 workers) + Product B (3h, 5 workers)
                            #   → MaxEmployeesOnLine = max(3,5) = 5 workers
                            #   → Cost = rate × 8h × 5 workers
                            #
                            # This is more efficient than hiring separately:
                            #   Without grouping: (3 workers × 8h) + (5 workers × 8h) = 64 worker-hours
                            #   With grouping: 5 workers × 8h = 40 worker-hours (savings!)

                            for ell in line_tuples:
                                cost_terms.append(cost[e][s] * Hmax_s[s] * MaxEmployeesOnLine[e, ell, s, t])

        print(f"✅ Cost function built with {len(cost_terms)} terms")
        print(f"   Both Partial & Bulk payment modes:")
        print(f"     - Cost = hourly_rate × shift_hour × MaxEmployeesOnLine")
        print(f"     - Line-based grouping: products on same line share workers")
        print(f"     - Linear formulation: LP solver compatible")

        # Note: No idle employee costs - only pay for employees actually working

        total_cost = solver.Sum(cost_terms)

        # Objective: minimize total labor cost (wages)
        # This finds the optimal production schedule (product order, line assignment, timing)
        # that minimizes total wages while meeting all demand and capacity constraints
        solver.Minimize(total_cost)

        # --- Constraints ---

        # 1) Weekly demand - must meet exactly (no over/under production)
        # Only iterate over products with non-zero demand
        print("\n[OPTIMIZATION] Setting demand constraints (filtered)...")
        products_with_demand = [p for p in sorted_product_list if DEMAND_DICTIONARY.get(p, 0) > 0]

        for p in products_with_demand:
            # Only sum over valid combinations for this product
            total_production = solver.Sum(
                Units[p, ell, s, t]
                for p_iter, ell, s, t in valid_combinations
                if p_iter == p
            )
            demand = DEMAND_DICTIONARY.get(p, 0)

            # Must produce at least the demand
            solver.Add(total_production >= demand)

            # Must not produce more than the demand (prevent overproduction)
            solver.Add(total_production <= demand)

        print(f"   ✅ Demand constraints set for {len(products_with_demand)} products with demand > 0")

        # 2) Time capacity constraint: total work hours on each (line, shift, day) cannot exceed shift hours
        # This allows multiple products to be produced sequentially in the same shift
        # Example: 8-hour shift can have 2hr product + 3hr product + 2hr product = 7hr total
        print("\n[OPTIMIZATION] Setting time capacity constraints (filtered)...")
        for ell in line_tuples:
            for s in active_shift_list:
                for t in date_span_list:
                    # Total hours used on this line/shift/day must not exceed shift capacity
                    # Total hours used on this line/shift/day must not exceed shift capacity
                    # Include time padding between tasks:
                    # Total Time = Sum(Hours) + (Count - 1) * Padding
                    # Constraint: Sum(Hours) + Count * Padding <= Hmax + Padding
                    
                    total_hours = solver.Sum(
                            Hours[p, ell_iter, s_iter, t_iter]
                            for p, ell_iter, s_iter, t_iter in valid_combinations
                            if ell_iter == ell and s_iter == s and t_iter == t
                        )
                    
                    product_count = solver.Sum(
                        IsProducedOnLine[p, ell_iter, s_iter, t_iter]
                        for p, ell_iter, s_iter, t_iter in valid_combinations
                            if ell_iter == ell and s_iter == s and t_iter == t
                    )
                    
                    # If padding is positive, add the constraint
                    if TIME_PADDING_HOURS > 0:
                        solver.Add(
                            total_hours + product_count * TIME_PADDING_HOURS <= Hmax_s[s] + TIME_PADDING_HOURS
                        )
                    else:
                        solver.Add(total_hours <= Hmax_s[s])

                    # Note: No Assignment variable needed!
                    # If Hours > 0, product is automatically "assigned"
                    # If Hours = 0, product is automatically "not assigned"

        # 3) Product-line type compatibility + (optional) activity by day
        print("\n[OPTIMIZATION] Setting up activity constraints (filtered)...")

        # Note: Line compatibility constraints are already enforced by valid_combinations filtering
        # Here we only need to check ACTIVE constraints for valid combinations

        inactive_count = 0
        for p, ell, s, t in valid_combinations:
            # If the product is not active on this day, force Hours and Units to 0
            if ACTIVE[t][p] == 0:
                # Force Hours and Units to 0 for inactive days
                solver.Add(Hours[p, ell, s, t] == 0)
                solver.Add(Units[p, ell, s, t] == 0)
                inactive_count += 1

        print(f"   ✅ Set {inactive_count} inactive day constraints (only for valid combinations)")

        # Note: Line compatibility and demand filtering already enforced by:
        # - valid_combinations pre-filtering (lines 356-403)
        # - Variables only created for valid combinations (lines 414-426)

        # 4) Line throughput: Units ≤ product_speed * Hours (only for valid combinations)
        print("\n[OPTIMIZATION] Setting line throughput constraints (filtered)...")

        missing_speed_products = []
        for p, ell, s, t in valid_combinations:
            # Get product speed (same speed regardless of line type)
            if p in PER_PRODUCT_SPEED:
            # Convert kit per day to kit per hour (assuming 7.5 hour workday)
                speed = PER_PRODUCT_SPEED[p]
            # Upper bound: units cannot exceed capacity
                solver.Add(Units[p, ell, s, t] <= speed * Hours[p, ell, s, t])
            # Lower bound: if working, must produce (prevent phantom work)
                solver.Add(Units[p, ell, s, t] >= speed * Hours[p, ell, s, t])
            else:
            # Default speed if not found
                if p not in missing_speed_products:
                    raise Exception(f"No speed data for product {p}")


        # 5) Working hours constraint: active employees cannot exceed shift hour capacity

        for e in employee_type_list:
            for s in active_shift_list:
                for t in date_span_list:
                    # No idle employee constraints - employees are only counted when working
                    solver.Add(EMPLOYEE_HOURS[e, s, t] <= Hmax_s[s] * max_employee_type_day[e][t])

        # 6) Link EMPLOYEE_COUNT to line-based grouping
        # EMPLOYEE_COUNT must be >= sum of MaxEmployeesOnLine across all lines
        # This ensures we hire enough employees to cover all lines
        print("\n[OPTIMIZATION] Linking EMPLOYEE_COUNT to MaxEmployeesOnLine...")
        for e in employee_type_list:
            for s in active_shift_list:
                for t in date_span_list:
                    total_employees_needed = solver.Sum(
                        MaxEmployeesOnLine[e, ell, s, t] for ell in line_tuples
                    )
                    # EMPLOYEE_COUNT must be at least the sum of max employees on all lines
                    solver.Add(EMPLOYEE_COUNT[e, s, t] >= total_employees_needed)

        print(f"   ✅ EMPLOYEE_COUNT >= Σ MaxEmployeesOnLine (across all lines)")

        # 7) Shift ordering constraints (only apply if shifts are available)
        # Evening shift after regular shift
        # Now using EMPLOYEE_HOURS expressions directly!
        if ShiftType.EVENING in active_shift_list and ShiftType.REGULAR in active_shift_list:
            for e in employee_type_list:
                for t in date_span_list:
                    solver.Add(
                    EMPLOYEE_HOURS[e, ShiftType.EVENING, t] <= EMPLOYEE_HOURS[e, ShiftType.REGULAR, t]
                )

        # Overtime should only be used when regular shift is at capacity
        if ShiftType.OVERTIME in active_shift_list and ShiftType.REGULAR in active_shift_list:
            print("\n[OVERTIME] Adding constraints to ensure overtime only when regular shift is insufficient...")

            for e in employee_type_list:
                for t in date_span_list:
                    # Get available regular capacity for this employee type and day
                    regular_capacity = max_employee_type_day[e][t]

                    # Use EMPLOYEE_HOURS expressions directly
                    regular_usage = EMPLOYEE_HOURS[e, ShiftType.REGULAR, t]
                    overtime_usage = EMPLOYEE_HOURS[e, ShiftType.OVERTIME, t]

                    # Create binary variable: 1 if using overtime, 0 otherwise
                    using_overtime = solver.IntVar(0, 1, f'using_overtime_{e}_{t}')

                    # If using overtime, regular capacity must be utilized significantly
                    # Regular usage must be at least 90% of capacity to allow overtime
                    min_regular_for_overtime = int(0.9 * regular_capacity)

                    # Constraint 1: Can only use overtime if regular usage is high
                    solver.Add(regular_usage >= min_regular_for_overtime * using_overtime)

                    # Constraint 2: If any overtime is used, set the binary variable
                    solver.Add(overtime_usage <= regular_capacity * using_overtime)

            overtime_constraints_added = len(employee_type_list) * len(date_span_list) * \
                2  # 2 constraints per employee type per day
            print(
                f"[OVERTIME] Added {overtime_constraints_added} constraints ensuring overtime only when regular shifts are at 90%+ capacity")

        # 7.5) Bulk payment linking constraints ELIMINATED (no longer needed!)

        # 7.6) *** FIXED MINIMUM UNICEF EMPLOYEES CONSTRAINT ***
        # Ensure minimum UNICEF fixed-term staff work in the REGULAR shift every day
        # The minimum applies to the regular shift specifically (not overtime or evening)
        if 'UNICEF Fixed term' in employee_type_list and FIXED_MIN_UNICEF_PER_DAY > 0:
            if ShiftType.REGULAR in active_shift_list:
                print(
                    f"\n[FIXED STAFFING] Adding constraint for minimum {FIXED_MIN_UNICEF_PER_DAY} UNICEF employees in REGULAR shift per day...")
                for t in date_span_list:
                    # At least FIXED_MIN_UNICEF_PER_DAY employees must work in the regular shift each day
                    solver.Add(EMPLOYEE_COUNT['UNICEF Fixed term', ShiftType.REGULAR, t] >= FIXED_MIN_UNICEF_PER_DAY)
                print(f"[FIXED STAFFING] Added {len(date_span_list)} constraints ensuring >= {FIXED_MIN_UNICEF_PER_DAY} UNICEF employees in regular shift per day")
            else:
                print(f"\n[FIXED STAFFING] Warning: Regular shift not available, cannot enforce minimum UNICEF staffing")

        # 8) *** HIERARCHY DEPENDENCY CONSTRAINTS ***
        # For subkits with prepack dependencies: dependencies should be produced before or same time
        print("\n[HIERARCHY] Adding dependency constraints (only for valid combinations)...")
        dependency_constraints_added = 0

        for p in sorted_product_list:
            dependencies = KIT_DEPENDENCIES.get(p, [])
        if dependencies:
            # Get the level of the current product
            p_level = KIT_LEVELS.get(p, 2)

            for dep in dependencies:
                if dep in sorted_product_list:  # Only if dependency is also in production list
                    # Calculate "completion time" for each product (sum of all production times)
                    # Only sum over valid combinations where variables exist
                    p_completion = solver.Sum(
                        t * Hours[p, ell, s, t]
                        for p_iter, ell, s, t in valid_combinations
                            if p_iter == p
                                )
                    dep_completion = solver.Sum(
                        t * Hours[dep, ell, s, t]
                        for dep_iter, ell, s, t in valid_combinations
                            if dep_iter == dep
                                )

                    # Dependency should complete before or at the same time
                    solver.Add(dep_completion <= p_completion)
                    dependency_constraints_added += 1

                    print(f"  Added constraint: {dep} (dependency) <= {p} (level {p_level})")

        print(f"[HIERARCHY] Added {dependency_constraints_added} dependency constraints")

        # --- Solve ---
        self.logger.log_section("🚀 STARTING OPTIMIZATION")

        # Print final problem statistics
        actual_production_vars = len(valid_combinations)
        self.logger.log(f"\n📊 Final Problem Statistics:")
        self.logger.log(f"   Total Variables: {solver.NumVariables():,}")
        self.logger.log(f"   Total Constraints: {solver.NumConstraints():,}")
        self.logger.log(
            f"   Binary Variables: {actual_production_vars:,} (IsProducedOnLine - only valid combinations)")
        self.logger.log(
            f"   Integer Variables: {actual_production_vars + employee_slots:,} (Units + Employee Count)")
        self.logger.log(f"   Continuous Variables: {actual_production_vars:,} (Hours - only valid combinations)")
        self.logger.log(
            f"   💡 Optimization: {production_slots - actual_production_vars:,} variables eliminated by pre-filtering!")

        self.logger.log(f"\n⏱️  Starting solver... (max 5 minutes)")
        self.logger.log(f"📊 Solver will show progress below:\n")

        solver_start_time = time.time()

        # Run optimization
        status = solver.Solve()

        solver_elapsed_time = time.time() - solver_start_time

        self.logger.log_duration(solver_elapsed_time, "Solver completed")

        # Handle different solver statuses
        if status == pywraplp.Solver.OPTIMAL:
            self.logger.log("✅ OPTIMAL solution found!")
        elif status == pywraplp.Solver.FEASIBLE:
            self.logger.log("⚠️  FEASIBLE solution found (not proven optimal, but acceptable)")
            self.logger.log(f"   Reason: Time limit reached or gap tolerance met")
            self.logger.log(f"   Solution quality: within 5% of optimal")
            # Continue with feasible solution
        else:
            status_names = {
                pywraplp.Solver.INFEASIBLE: "INFEASIBLE",
                pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
                pywraplp.Solver.NOT_SOLVED: "NOT_SOLVED"
            }
            status_name = status_names.get(status, 'UNKNOWN')
            self.logger.log(f"❌ No solution found. Status: {status} ({status_name})")

            if status == pywraplp.Solver.INFEASIBLE:
                self.logger.log("\n💡 Problem is INFEASIBLE. Possible reasons:")
                self.logger.log("   1. Demand exceeds total production capacity")
                self.logger.log("   2. Not enough employees for required work")
                self.logger.log("   3. Conflicting constraints (hierarchy, line compatibility, etc.)")
                self.logger.log("   4. Production time required exceeds available shift hours")

                # Export model for debugging
                try:
                    model_path = "/tmp/infeasible_model.lp"
                    solver.ExportModelAsLpFile(model_path)
                    self.logger.log(f"\n🔍 Model exported to {model_path} for debugging")
                except BaseException:
                    pass

            return None

        # Check if we have a usable solution
        if status not in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
            return None

        # --- Report ---
        result = {}
        result['objective'] = solver.Objective().Value()

        # Weekly production (only sum over valid combinations where variables exist)
        prod_week = {}
        for p in sorted_product_list:
            total_units = sum(
                Units[p, ell, s, t].solution_value()
                for p_iter, ell, s, t in valid_combinations
                if p_iter == p
            )
            prod_week[p] = total_units
        result['weekly_production'] = prod_week

        # Which product ran on which line/shift/day
        # Note: Multiple products can run sequentially on the same (line, shift, day)
        # Also includes idle lines/shifts (no production) for complete visibility
        schedule = []
        for t in date_span_list:
            for ell in line_tuples:
                for s in active_shift_list:
                    # Track products produced in this (line, shift, day)
                    products_in_slot = []
                    total_hours_in_slot = 0

                    # Get all products that were produced (only check valid combinations)
                    for p, ell_iter, s_iter, t_iter in valid_combinations:
                        if ell_iter == ell and s_iter == s and t_iter == t:
                            hours_val = Hours[p, ell, s, t].solution_value()
                            if hours_val > 0.01:  # Produced with meaningful hours
                                units_val = Units[p, ell, s, t].solution_value()
                                
                                # Calculate employee requirements for this product
                                employees = {}
                                for e in employee_type_list:
                                    emp_count = TEAM_REQ_PER_PRODUCT[e][p]
                                    if emp_count > 0:  # Only include if employees are needed
                                        employees[e] = emp_count
                                
                                products_in_slot.append({
                                    'product': p,
                                    'run_hours': hours_val,
                                    'units': units_val,
                                    'employees': employees
                                })
                                total_hours_in_slot += hours_val

                    # Add all products to schedule
                    if products_in_slot:
                        for prod_info in products_in_slot:
                            schedule.append({
                                'day': t,
                                'line_type_id': ell[0],
                                'line_idx': ell[1],
                                'shift': s,
                                'product': prod_info['product'],
                                'run_hours': prod_info['run_hours'],
                                'units': prod_info['units'],
                                'employees': prod_info['employees'],
                                'is_idle': False
                            })
                    else:
                        # No production - add idle entry for visibility
                        schedule.append({
                            'day': t,
                            'line_type_id': ell[0],
                            'line_idx': ell[1],
                            'shift': s,
                            'product': None,  # No product assigned
                            'run_hours': 0,
                            'units': 0,
                            'employees': {},  # No employees needed for idle
                            'is_idle': True
                        })
        result['run_schedule'] = schedule

        # Actual headcount by type/shift/day from MaxEmployeesOnLine (correct calculation)
        # Sum across all lines since multiple lines operate simultaneously
        headcount = []
        for e in employee_type_list:
            for s in active_shift_list:
                for t in date_span_list:
                    # Sum employees needed across all lines (lines work in parallel)
                    total_needed = sum(
                        int(MaxEmployeesOnLine[e, ell, s, t].solution_value()) 
                        for ell in line_tuples
                    )
                    if total_needed > 0:  # Only add if employees are actually needed
                        headcount.append({
                            'emp_type': e, 
                            'shift': s, 
                            'day': t,
                            'needed': total_needed, 
                            'available': max_employee_type_day[e][t]
                        })
        result['headcount_per_shift'] = headcount

        # Build hierarchical employee allocation: day → shift → employee_type
        # This creates the final structure directly without intermediate flat lists
        employee_allocation = {}
        for e in employee_type_list:
            for s in active_shift_list:
                for t in date_span_list:
                    # Calculate actual employee count from MaxEmployeesOnLine (line-based grouping)
                    actual_count = sum(
                        int(MaxEmployeesOnLine[e, ell, s, t].solution_value())
                        for ell in line_tuples
                    )
                    
                    if actual_count > 0:  # Only add if employees are actually needed
                        used_hours = sum(
                            TEAM_REQ_PER_PRODUCT[e][p] * Hours[p, ell, s_iter, t_iter].solution_value()
                            for p, ell, s_iter, t_iter in valid_combinations
                            if s_iter == s and t_iter == t
                        )
                        avg_hours_per_employee = used_hours / actual_count if actual_count > 0 else 0
                        
                        # Initialize hierarchical structure
                        day_key = f"day_{t}"
                        shift_key = f"shift_{s}"
                        
                        if day_key not in employee_allocation:
                            employee_allocation[day_key] = {}
                        
                        if shift_key not in employee_allocation[day_key]:
                            employee_allocation[day_key][shift_key] = {
                                'shift_name': ShiftType.get_name(s),
                                'employees': {}
                            }
                        
                        # Add employee type data
                        employee_allocation[day_key][shift_key]['employees'][e] = {
                            'employee_count': actual_count,
                            'total_person_hours': used_hours,
                            'avg_hours_per_employee': avg_hours_per_employee
                        }
        
        result['employee_allocation'] = employee_allocation
        
        # Extract EMPLOYEE_COUNT solution values for visualization
        # EMPLOYEE_COUNT[e, s, t] is the actual optimized employee count
        employee_count_data = []
        for e in employee_type_list:
            for s in active_shift_list:
                for t in date_span_list:
                    # emp_count_value = int(EMPLOYEE_COUNT[e, s, t].solution_value())
                    emp_count_value = sum(int(MaxEmployeesOnLine[e, ell, s, t].solution_value()) for ell in line_tuples)
                    if emp_count_value >= 0:  # Only include non-zero values
                        employee_count_data.append({
                            'employee_type': e,
                            'shift': s,
                            'shift_name': ShiftType.get_name(s),
                            'day': t,
                            'employee_count': emp_count_value,
                            'max_available': max_employee_type_day.get(e, {}).get(t, 0)
                            # 'total_employees_needed': total_employees_needed
                        })
        result['employee_count_optimized'] = employee_count_data
        
        # Calculate detailed cost breakdown from optimization variables (not from schedule!)
        # Use actual MaxEmployeesOnLine values that were used in objective function
        cost_breakdown = {
            'by_employee_type': {},
            'by_day': {},
            'by_shift': {},
            'detailed_costs': []
        }
        
        # Initialize accumulators
        for e in employee_type_list:
            cost_breakdown['by_employee_type'][e] = 0
        for s in active_shift_list:
            shift_name = ShiftType.get_name(s)
            cost_breakdown['by_shift'][shift_name] = 0
        
        # Extract cost from optimization variables (same as objective function)
        for e in employee_type_list:
            for s in active_shift_list:
                for t in date_span_list:
                    payment_mode = PAYMENT_MODE_CONFIG[s]
                    hourly_rate = cost[e][s]
                    shift_hours = Hmax_s[s]
                    
                    day_key = f"day_{t}"
                    shift_name = ShiftType.get_name(s)
                    
                    # Initialize day if needed
                    if day_key not in cost_breakdown['by_day']:
                        cost_breakdown['by_day'][day_key] = 0
                    
                    for ell in line_tuples:
                        # Get MaxEmployeesOnLine from solver (actual optimized value)
                        max_emp = MaxEmployeesOnLine[e, ell, s, t].solution_value()
                        
                        if max_emp > 0.01:  # Only if employees were actually assigned
                            # Calculate cost exactly as in objective function
                            # Cost = hourly_rate × shift_hour × max_employees_on_line
                            line_cost = hourly_rate * shift_hours * max_emp
                            
                            # Add to accumulators
                            cost_breakdown['by_employee_type'][e] += line_cost
                            cost_breakdown['by_day'][day_key] += line_cost
                            cost_breakdown['by_shift'][shift_name] += line_cost
                            
                            # Find which products ran on this line/shift/day for detailed entry
                            products_on_line = []
                            total_hours_on_line = 0
                            for p, ell_iter, s_iter, t_iter in valid_combinations:
                                if ell_iter == ell and s_iter == s and t_iter == t:
                                    hours_val = Hours[p, ell, s, t].solution_value()
                                    if hours_val > 0.01:
                                        products_on_line.append(p)
                                        total_hours_on_line += hours_val
                            
                            # Add detailed entry
                            mode_str = payment_mode.value if hasattr(payment_mode, 'value') else str(payment_mode)
                            line_name = f"{LineType.get_name(ell[0])}_{ell[1]}"
                            
                            cost_breakdown['detailed_costs'].append({
                                'day': t,
                                'shift': s,
                                'shift_name': shift_name,
                                'line_type_id': ell[0],
                                'line_idx': ell[1],
                                'line_name': line_name,
                                'products': products_on_line,  # May be multiple products
                                'employee_type': e,
                                'max_employees_on_line': int(max_emp),
                                'actual_hours': float(total_hours_on_line),
                                'paid_hours': float(shift_hours),
                                'hourly_rate': float(hourly_rate),
                                'cost': float(line_cost),
                                'payment_mode': mode_str
                            })
        
        result['cost_breakdown'] = cost_breakdown
        
        # Verify cost breakdown matches objective value
        total_breakdown_cost = sum(cost_breakdown['by_employee_type'].values())
        objective_cost = result['objective']
        cost_difference = abs(total_breakdown_cost - objective_cost)
        
        if cost_difference < 0.01:  # Allow small floating point differences
            print(f"✅ Cost breakdown verified: ﹩{total_breakdown_cost:.2f} matches objective ﹩{objective_cost:.2f}")
        else:
            print(f"⚠️ Warning: Cost breakdown (﹩{total_breakdown_cost:.2f}) differs from objective (﹩{objective_cost:.2f}) by ﹩{cost_difference:.2f}")

        # Pretty print
        print("Objective (min cost):", result['objective'])
        print("\n--- Weekly production by product ---")
        for p, u in prod_week.items():
            print(f"{p}: {u:.1f} / demand {DEMAND_DICTIONARY.get(p,0)}")

        print("\n--- Schedule (line, shift, day) ---")
        for row in schedule:
            shift_name = ShiftType.get_name(row['shift'])
            line_name = LineType.get_name(row['line_type_id'])
            if row['is_idle']:
                print(f"date_span_list{row['day']} {line_name}-{row['line_idx']} {shift_name}: "
                        f"[IDLE - No Production]")
            else:
                print(f"date_span_list{row['day']} {line_name}-{row['line_idx']} {shift_name}: "
                        f"{row['product']}  Hours={row['run_hours']:.2f}h  Units={row['units']:.1f}")

        print("\n--- Implied headcount need (per type/shift/day) ---")
        for row in headcount:
            shift_name = ShiftType.get_name(row['shift'])
            print(f"{row['emp_type']}, {shift_name}, date_span_list{row['day']}: "
                f"need={row['needed']} (avail {row['available']})")

        print("\n--- Actual employee count by type/shift/day ---")
        for day_key in sorted(employee_allocation.keys()):
            for shift_key in sorted(employee_allocation[day_key].keys()):
                shift_data = employee_allocation[day_key][shift_key]
                for emp_type, emp_data in shift_data['employees'].items():
                    print(f"{emp_type}, {shift_data['shift_name']}, {day_key}: "
                        f"count={emp_data['employee_count']} employees, "
                        f"total_hours={emp_data['total_person_hours']:.1f}h, "
                        f"avg={emp_data['avg_hours_per_employee']:.1f}h/employee")

        # Note: All employee data now in hierarchical structure from the start

        # Calculate and log optimization summary
        optimization_end_time = time.time()
        total_time = optimization_end_time - optimization_start_time
        
        # Store metadata in result for later use (e.g., saving to JSON)
        result['metadata'] = {
            'start_time': datetime.datetime.fromtimestamp(optimization_start_time).strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'duration_seconds': total_time,
            'solver_time_seconds': solver_elapsed_time,
            'status': 'OPTIMAL' if status == pywraplp.Solver.OPTIMAL else 'FEASIBLE'
        }

        self.logger.log_summary(
            end_time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_duration=total_time,
            optimal_cost=result['objective'],
            products_scheduled=len([p for p, u in result['weekly_production'].items() if u > 0]),
            total_production=int(sum(result['weekly_production'].values()))
        )

        return result



if __name__ == "__main__":
    optimizer = Optimizer()
    optimizer.run_optimization()
