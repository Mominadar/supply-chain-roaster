"""
Configuration Page for Supply Roster Optimization Tool
Contains all user input controls with default values from config
"""

import streamlit as st
import datetime
import sys
import os
from src.config import optimization_config
from src.config.constants import ShiftType, LineType, DefaultConfig

def clear_optimization_cache():
    """Clear all cached optimization results and validation data"""
    # Clear any previous optimization results since settings changed
    if 'optimization_results' in st.session_state:
        del st.session_state.optimization_results
    
    # Clear any previous validation state
    if 'show_validation_after_save' in st.session_state:
        del st.session_state.show_validation_after_save
    if 'settings_just_saved' in st.session_state:
        del st.session_state.settings_just_saved
    
    # Clear any cached validation results since settings changed
    validation_cache_key = f"validation_results_{st.session_state.get('demand_start_date', 'default')}"
    if validation_cache_key in st.session_state:
        del st.session_state[validation_cache_key]

def render_config_page():
    """Render the configuration page with all user input controls"""
    
    st.title("⚙️ Settings")
    st.markdown("---")
    

    st.markdown("Adjust the settings for your workforce optimization. These settings control how the system schedules employees and calculates costs.")
    
    # Initialize session state for all configuration values
    initialize_session_state()
    
    # Create tabs for better organization
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📅 Schedule", "👥 Workforce", "🏭 Operations", "💰 Cost", "📊 Data Selection"])
    
    with tab1:
        render_schedule_config()
    
    with tab2:
        render_workforce_config()
    
    with tab3:
        render_operations_config()
    
    with tab4:
        render_cost_config()
    
    with tab5:
        render_data_selection_config()
    
    # Save configuration button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("💾 Save Settings", type="primary", use_container_width=True):
            config = save_configuration()
            
            # Only proceed if configuration was saved successfully
            if config is not None:
                st.success("✅ Settings saved successfully!")
                
                # Clear all cached optimization and validation data
                clear_optimization_cache()
                
                # Trigger fresh demand validation after saving settings
                st.session_state.show_validation_after_save = True
                st.session_state.settings_just_saved = True
                
                # Force a page refresh to show the updated validation
                st.rerun()
            # If config is None, error messages are already shown by save_configuration()
    
    # Display settings summary at full width (outside columns)
    st.markdown("---")
    if 'optimization_config' in st.session_state:
        with st.expander("📋 Settings Summary", expanded=False):
            display_user_friendly_summary(st.session_state.optimization_config)
    
    # Show demand validation after saving settings
    if st.session_state.get('show_validation_after_save', False) or st.session_state.get('settings_just_saved', False):
        st.markdown("---")
        st.header("📋 Data Validation Results")
        st.markdown("Analyzing your demand data to identify potential optimization issues...")
        
        # Check if we have cached validation results
        validation_cache_key = f"validation_results_{st.session_state.get('demand_start_date', 'default')}"
        
        if validation_cache_key not in st.session_state:
            # Run validation and cache results
            with st.spinner("🔄 Running data validation..."):
                try:
                    from src.demand_validation_viz import DemandValidationViz
                    
                    # Initialize validator and run validation
                    validator = DemandValidationViz()
                    print("validator",validator)
                    if validator.load_data():
                        
                        validation_df = validator.validate_all_products()
                        print("validation_df", validation_df)
                        summary_stats = validator.get_summary_statistics(validation_df)
                        print("summary_stats", summary_stats)
                        # Cache the results
                        st.session_state[validation_cache_key] = {
                            'validation_df': validation_df,
                            'summary_stats': summary_stats,
                            'validator': validator
                        }
                    else:
                        st.error("❌ Failed to load validation data")
                        st.session_state[validation_cache_key] = None
                        
                except Exception as e:
                    print(validation_cache_key)
                    st.error(f"❌ Error in demand validation: {str(e)}")
                    st.session_state[validation_cache_key] = None
        
        # Display cached validation results
        if st.session_state.get(validation_cache_key):
            # print("cached_results",st.session_state[validation_cache_key])
            cached_results = st.session_state[validation_cache_key]
            
            validation_df = cached_results['validation_df']
            # print("validation_df",validation_df)
            summary_stats = cached_results['summary_stats']
            # print("summary_stats",summary_stats)
            # Display summary statistics
            st.subheader("📊 Summary Statistics")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Products", summary_stats['total_products'])
                st.metric("Included in Optimization", summary_stats['included_products'], delta="Ready for optimization")
            
            with col2:
                st.metric("Total Demand", f"{summary_stats['total_demand']:,}")
                st.metric("Excluded from Optimization", summary_stats['excluded_products'], delta="Omitted")
            
            with col3:
                st.metric("Included Demand", f"{summary_stats['included_demand']:,}", delta="Will be optimized")
                
            
            with col4:
                st.metric("Excluded Demand", f"{summary_stats['excluded_demand']:,}", delta="Omitted")
        
            
            # Separate the results into included and excluded
            included_df = validation_df[validation_df['Excluded from Optimization'] == False].copy()
            excluded_df = validation_df[validation_df['Excluded from Optimization'] == True].copy()
            
            # Products Included in Optimization
            st.subheader("✅ Products Included in Optimization")
            st.write(f"**{len(included_df)} products** will be included in the optimization with total demand of **{included_df['Demand'].sum():,} units**")
            
            if len(included_df) > 0:
                # Configure column display for included
                included_columns = ['Product ID', 'Demand', 'Material description','Product Type', 'Line Type', 'UNICEF Staff', 'Humanizer Staff', 'Production Speed (units/hour)', 'Validation Status']
                
                st.dataframe(
                    included_df[included_columns],
                    use_container_width=True,
                    height=300
                )
            else:
                st.warning("No products are included in optimization!")
            
            # Products Excluded from Optimization  
            st.subheader("🚫 Products Excluded from Optimization")
            st.write(f"**{len(excluded_df)} products** are excluded from optimization with total demand of **{excluded_df['Demand'].sum():,} units**")
            st.info("These products are omitted from optimization due to missing line assignments or zero staffing requirements.")
            
            if len(excluded_df) > 0:
                # Show exclusion breakdown
                exclusion_reasons = excluded_df['Exclusion Reasons'].value_counts()
                st.write("**Exclusion reasons:**")
                for reason, count in exclusion_reasons.items():
                    st.write(f"• {reason}: {count} products")
                
                # Configure column display for excluded
                excluded_columns = ['Product ID', 'Demand', 'Material description','Product Type', 'Exclusion Reasons', 'UNICEF Staff', 'Humanizer Staff', 'Line Type']
                
                st.dataframe(
                    excluded_df[excluded_columns],
                    use_container_width=True,
                    height=200
                )
            else:
                st.info("No products are excluded from optimization.")
            
            # Show validation reminder before optimization
            st.info("💡 **Review validation results above before running optimization.** " +
                   "Fix any critical issues (especially missing line assignments) to improve optimization success.")
        else:
            st.error("❌ Validation failed to run properly")
            st.info("💡 You can still proceed with optimization, but data issues may cause problems.")
        
        # # Reset the flags so validation doesn't show every time
        # col1, col2, col3 = st.columns([1, 1, 1])
        # with col2:
        #     if st.button("✅ Validation Reviewed - Continue to Optimization", use_container_width=True):
        #         st.session_state.show_validation_after_save = False
        #         st.session_state.settings_just_saved = False
        #         # Clear validation cache to force fresh validation next time
        #         if validation_cache_key in st.session_state:
        #             del st.session_state[validation_cache_key]
        #         st.rerun()  # Refresh to hide validation section
    
    # Show feasibility check results after saving settings
    if st.session_state.get('show_feasibility_after_save', False) or st.session_state.get('settings_just_saved', False):
        st.markdown("---")
        st.header("🔍 Feasibility Check Results")
        st.markdown("Validating if your configuration can meet production demand with available resources...")
        
        # Check if we have cached feasibility results
        feasibility_cache_key = f"feasibility_results_{st.session_state.get('demand_start_date', 'default')}"
        
        if feasibility_cache_key in st.session_state and st.session_state[feasibility_cache_key]:
            cached_feasibility = st.session_state[feasibility_cache_key]
            feasibility_results = cached_feasibility['results']
            captured_output = cached_feasibility['captured_output']
            
            # Display summary
            if not feasibility_results['feasible']:
                # Critical errors - configuration is infeasible
                st.error("❌ **Configuration is INFEASIBLE!**")
                st.error("The current settings cannot meet production demand with available resources.")
                
                with st.expander("⚠️ View Feasibility Issues", expanded=True):
                    if feasibility_results['errors']:
                        st.subheader("Critical Errors:")
                        for error in feasibility_results['errors']:
                            st.error(f"• {error}")
                    
                    if feasibility_results['warnings']:
                        st.subheader("Warnings:")
                        for warning in feasibility_results['warnings']:
                            st.warning(f"• {warning}")
                
                st.error("**⚠️ You must adjust your configuration before running optimization.**")
            
            elif feasibility_results['warnings']:
                # Warnings but feasible - show warnings but allow proceeding
                st.warning("⚠️ **Configuration is FEASIBLE but has warnings**")
                st.info("The configuration can work, but capacity may be tight in some areas.")
                
                with st.expander("⚠️ View Feasibility Warnings", expanded=True):
                    for warning in feasibility_results['warnings']:
                        st.warning(f"• {warning}")
                
                st.success("✅ You can proceed to optimization, but be aware of capacity constraints.")
            
            else:
                # All good
                st.success("✅ **Feasibility check passed!**")
                st.success("Your configuration can meet all production demands with available resources.")
                
                # Show some summary stats
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Status", "FEASIBLE", delta="Ready for optimization")
                with col2:
                    st.metric("Issues Found", "0", delta="No problems detected")
            
            # Show detailed log in expander
            if captured_output:
                with st.expander("🔍 Detailed Feasibility Check Log", expanded=False):
                    st.code(captured_output, language="text")
        
        else:
            st.info("💡 Save your settings to run feasibility check")
    
    # Optimization section
    st.markdown("---")
    st.header("🚀 Run Optimization")
    st.markdown("Once you've configured your settings, run the optimization to generate the optimal workforce schedule.")
    st.markdown("**💡 Tip:** Optimization automatically clears all previous cache and results to ensure fresh calculations with your current settings.")
    
    col1, col2 = st.columns([1, 1])
    # with col1:
    #     if st.button("🧹 Clear Cache", use_container_width=True):
    #         clear_all_cache_and_results()
    with col1:
        if st.button("🚀 Optimize Schedule", type="primary", use_container_width=True):
            # Quick validation check before optimization
            validation_warnings = check_critical_data_issues()
            if validation_warnings:
                st.warning("⚠️ **Data validation warnings detected:**")
                for warning in validation_warnings:
                    st.warning(f"• {warning}")
                st.warning("**These issues may cause optimization to fail. Consider fixing them first.**")
                
                # Give user option to proceed anyway
                if st.button("⚠️ Proceed with Optimization Anyway", type="secondary"):
                    run_optimization()
            else:
                run_optimization()
    with col2:
        # Show status of current results
        if 'optimization_results' in st.session_state and st.session_state.optimization_results is not None:
            st.success("✅ Results Available")
        elif 'optimization_config' in st.session_state:
            st.info("🔄 Settings Saved - Ready to Optimize")
        else:
            st.info("⏳ No Results Yet")
    
    # Show success message if optimization results are available
    if 'optimization_results' in st.session_state and st.session_state.optimization_results is not None:
        st.markdown("---")
        st.success("✅ Optimization completed! Click the **📊 Optimization Results** tab at the top to view detailed results.")

def initialize_session_state():
    """Initialize session state with default values from constants.py"""
    
    # Use constants from DefaultConfig - no more hardcoded values
    # Use setdefault to avoid overwriting existing values
    
    # Schedule defaults - NEW: Separated demand and production dates
    st.session_state.setdefault('demand_start_date',DefaultConfig.DEFAULT_DEMAND_START_DATE)
    st.session_state.setdefault('production_start_date', DefaultConfig.DEFAULT_PRODUCTION_START_DATE)
    st.session_state.setdefault('production_end_date', DefaultConfig.DEFAULT_PRODUCTION_END_DATE)
    st.session_state.setdefault('schedule_type', DefaultConfig.SCHEDULE_TYPE)
    
    # Planning days calculated from production dates
    st.session_state.setdefault('planning_days', DefaultConfig.DEFAULT_PLANNING_DAYS)
    st.session_state.setdefault('date_span', DefaultConfig.DEFAULT_DATE_SPAN)
    
    # Staff defaults
    st.session_state.setdefault('fixed_staff_mode', DefaultConfig.FIXED_STAFF_MODE)
    st.session_state.setdefault('fixed_min_unicef_per_day', DefaultConfig.FIXED_MIN_UNICEF_PER_DAY)
    
    # Payment modes
    st.session_state.setdefault('payment_mode_shift_1', DefaultConfig.PAYMENT_MODE_CONFIG[ShiftType.REGULAR])
    st.session_state.setdefault('payment_mode_shift_2', DefaultConfig.PAYMENT_MODE_CONFIG[ShiftType.EVENING])
    st.session_state.setdefault('payment_mode_shift_3', DefaultConfig.PAYMENT_MODE_CONFIG[ShiftType.OVERTIME])
    
    # Working hours
    st.session_state.setdefault('max_hour_per_person_per_day', DefaultConfig.MAX_HOUR_PER_PERSON_PER_DAY)
    st.session_state.setdefault('max_hours_shift_1', DefaultConfig.MAX_HOUR_PER_SHIFT_PER_PERSON[ShiftType.REGULAR])
    st.session_state.setdefault('max_hours_shift_2', DefaultConfig.MAX_HOUR_PER_SHIFT_PER_PERSON[ShiftType.EVENING])
    st.session_state.setdefault('max_hours_shift_3', DefaultConfig.MAX_HOUR_PER_SHIFT_PER_PERSON[ShiftType.OVERTIME])
    
    # Workforce limits
    st.session_state.setdefault('max_unicef_per_day', DefaultConfig.MAX_UNICEF_PER_DAY)
    st.session_state.setdefault('max_humanizer_per_day', DefaultConfig.MAX_HUMANIZER_PER_DAY)
    
    # Operations
    st.session_state.setdefault('line_count_long_line', DefaultConfig.LINE_COUNT_LONG_LINE)
    st.session_state.setdefault('line_count_mini_load', DefaultConfig.LINE_COUNT_MINI_LOAD)
    st.session_state.setdefault('max_parallel_workers_long_line', DefaultConfig.MAX_PARALLEL_WORKERS_LONG_LINE)
    st.session_state.setdefault('max_parallel_workers_mini_load', DefaultConfig.MAX_PARALLEL_WORKERS_MINI_LOAD)
    
    # Cost rates
    st.session_state.setdefault('unicef_rate_shift_1', DefaultConfig.UNICEF_RATE_SHIFT_1)
    st.session_state.setdefault('unicef_rate_shift_2', DefaultConfig.UNICEF_RATE_SHIFT_2)
    st.session_state.setdefault('unicef_rate_shift_3', DefaultConfig.UNICEF_RATE_SHIFT_3)
    st.session_state.setdefault('humanizer_rate_shift_1', DefaultConfig.HUMANIZER_RATE_SHIFT_1)
    st.session_state.setdefault('humanizer_rate_shift_2', DefaultConfig.HUMANIZER_RATE_SHIFT_2)
    st.session_state.setdefault('humanizer_rate_shift_3', DefaultConfig.HUMANIZER_RATE_SHIFT_3)
    
    # Data selection
    st.session_state.setdefault('selected_employee_types', ["UNICEF Fixed term", "Humanizer"])
    st.session_state.setdefault('selected_shifts', [ShiftType.REGULAR, ShiftType.OVERTIME])
    st.session_state.setdefault('selected_lines', [LineType.LONG_LINE, LineType.MINI_LOAD])
    
    # Operations defaults - Time Padding
    st.session_state.setdefault('time_padding', DefaultConfig.DEFAULT_TIME_PADDING)

def render_schedule_config():
    """Render schedule configuration section"""
    st.header("📅 Schedule Configuration")
    
    st.markdown("### 📊 Demand Date")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.date_input(
            "Demand Start Date",
            value=DefaultConfig.DEFAULT_DEMAND_START_DATE,
            key='demand_start_date',
            format="DD/MM/YYYY",
            help="Date to filter demand data - will only use orders that start on this specific date"
        )
    with col2:
        st.info("💡 **Demand Filtering**: System will use only demand data that starts on this date.")
    
    st.markdown("### 🏭 Production Period")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.date_input(
            "Production Start Date",
            value=DefaultConfig.DEFAULT_PRODUCTION_START_DATE,
            key='production_start_date',
            format="DD/MM/YYYY",
            help="First day of production period for workforce planning"
        )
    
    with col2:
        st.date_input(
            "Production End Date",
            value=DefaultConfig.DEFAULT_PRODUCTION_END_DATE,
            key='production_end_date',
            format="DD/MM/YYYY",
            help="Last day of production period for workforce planning"
        )
    
    # Calculate and display planning days
    if 'production_start_date' in st.session_state and 'production_end_date' in st.session_state:
        planning_days = (st.session_state.production_end_date - st.session_state.production_start_date).days + 1
        if planning_days > 0:
            st.info(f"📆 **Planning Period**: {planning_days} days ({st.session_state.production_start_date} to {st.session_state.production_end_date})")
        else:
            st.error("⚠️ Production end date must be after start date!")


def render_workforce_config():
    """Render workforce configuration section"""
    st.header("👥 Workforce Configuration")
    
    # Fixed staff constraint mode
    staff_mode_options = ['mandatory', 'available', 'priority', 'none']
    
    st.selectbox(
        "Fixed Staff Constraint Mode",
        options=staff_mode_options,
        index=staff_mode_options.index(DefaultConfig.FIXED_STAFF_MODE),
        key='fixed_staff_mode',
        help="""
        - **Mandatory**: Forces all fixed staff to work full hours every day
        - **Available**: Staff available up to limits but not forced
        - **Priority**: Fixed staff used first, then temporary staff (recommended)
        - **None**: Purely demand-driven scheduling
        """
    )
    
    # Workforce limits
    st.subheader("👨‍💼 Daily Workforce Limits")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.number_input(
            "Max UNICEF Fixed Term per Day",
            min_value=1,
            max_value=200,
            value=DefaultConfig.MAX_UNICEF_PER_DAY,
            key='max_unicef_per_day',
            help="Maximum number of UNICEF fixed term employees per day"
        )
    
    with col2:
        st.number_input(
            "Max Humanizer per Day",
            min_value=1,
            max_value=200,
            value=DefaultConfig.MAX_HUMANIZER_PER_DAY,
            key='max_humanizer_per_day',
            help="Maximum number of Humanizer employees per day"
        )
    
    # Fixed minimum UNICEF requirement
    st.subheader("🔒 Fixed Minimum Requirements")
    
    st.number_input(
        "Fixed Minimum UNICEF per Day",
        min_value=0,
        max_value=20,
        value=DefaultConfig.FIXED_MIN_UNICEF_PER_DAY,
        key='fixed_min_unicef_per_day',
        help="Minimum number of UNICEF Fixed term employees required every working day (constraint)"
        )
    
    # Working hours configuration
    st.subheader("⏰ Working Hours Configuration")
    
    st.number_input(
        "Max Hours per Person per Day",
        min_value=1,
        max_value=24,
        value=DefaultConfig.MAX_HOUR_PER_PERSON_PER_DAY,
        key='max_hour_per_person_per_day',
        help="Legal maximum working hours per person per day"
    )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.number_input(
            "Max Hours - Shift 1 (Regular)",
            min_value=1.0,
            max_value=12.0,
            value=float(DefaultConfig.MAX_HOUR_PER_SHIFT_PER_PERSON[ShiftType.REGULAR]),
            key='max_hours_shift_1',
            step=0.5,
            help="Maximum hours per person for regular shift"
        )
    
    with col2:
        st.number_input(
            "Max Hours - Shift 2 (Evening)",
            min_value=1.0,
            max_value=12.0,
            value=float(DefaultConfig.MAX_HOUR_PER_SHIFT_PER_PERSON[ShiftType.EVENING]),
            key='max_hours_shift_2',
            step=0.5,
            help="Maximum hours per person for evening shift"
        )
    
    with col3:
        st.number_input(
            "Max Hours - Shift 3 (Overtime)",
            min_value=1.0,
            max_value=12.0,
            value=float(DefaultConfig.MAX_HOUR_PER_SHIFT_PER_PERSON[ShiftType.OVERTIME]),
            key='max_hours_shift_3',
            step=0.5,
            help="Maximum hours per person for overtime shift"
        )

def render_operations_config():
    """Render operations configuration section"""
    st.header("🏭 Operations Configuration")
    
    # Line configuration
    st.subheader("📦 Production Line Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.number_input(
            "Number of Long Lines",
            min_value=1,
            max_value=20,
            value=DefaultConfig.LINE_COUNT_LONG_LINE,
            key='line_count_long_line',
            help="Number of long line production lines available"
        )
        
        st.number_input(
            "Max Workers per Long Line",
            min_value=1,
            max_value=50,
            value=DefaultConfig.MAX_PARALLEL_WORKERS_LONG_LINE,
            key='max_parallel_workers_long_line',
            help="Maximum number of workers that can work simultaneously on a long line"
        )
    
    with col2:
        st.number_input(
            "Number of Mini Load Lines",
            min_value=1,
            max_value=20,
            value=DefaultConfig.LINE_COUNT_MINI_LOAD,
            key='line_count_mini_load',
            help="Number of mini load production lines available"
        )
        
        st.number_input(
            "Max Workers per Mini Load Line",
            min_value=1,
            max_value=50,
            value=DefaultConfig.MAX_PARALLEL_WORKERS_MINI_LOAD,
            key='max_parallel_workers_mini_load',
            help="Maximum number of workers that can work simultaneously on a mini load line"
        )
    
    # Time Padding Configuration
    st.subheader("⏱️ Process Efficiency")
    
    st.number_input(
        "Time Padding Between Tasks (minutes)",
        min_value=0,
        max_value=120,
        value=DefaultConfig.DEFAULT_TIME_PADDING,
        key='time_padding',
        help="Buffer time required between consecutive tasks on the same line (applies only between products)"
    )

def render_cost_config():
    """Render cost configuration section"""
    st.header("💰 Cost Configuration")
    
    # Payment mode configuration
    st.subheader("💳 Payment Mode Configuration")
    
    st.markdown("""
    **Payment Modes:**
    - **Bulk**: If employee works any hours in shift, pay for full shift hours
    - **Partial**: Pay only for actual hours worked
    """)
    
    col1, col2, col3 = st.columns(3)
    
    payment_options = ['bulk', 'partial']
    
    with col1:
        st.selectbox(
            "Shift 1 (Regular) Payment",
            options=payment_options,
            index=payment_options.index(DefaultConfig.PAYMENT_MODE_CONFIG[ShiftType.REGULAR]),
            key='payment_mode_shift_1',
            help="Payment mode for regular shift"
        )
    
    with col2:
        st.selectbox(
            "Shift 2 (Evening) Payment",
            options=payment_options,
            index=payment_options.index(DefaultConfig.PAYMENT_MODE_CONFIG[ShiftType.EVENING]),
            key='payment_mode_shift_2',
            help="Payment mode for evening shift"
        )
    
    with col3:
        st.selectbox(
            "Shift 3 (Overtime) Payment",
            options=payment_options,
            index=payment_options.index(DefaultConfig.PAYMENT_MODE_CONFIG[ShiftType.OVERTIME]),
            key='payment_mode_shift_3',
            help="Payment mode for overtime shift"
        )
    
    # Hourly rates configuration - editable with defaults from config
    st.subheader("💵 Hourly Rates Configuration")
    
    st.markdown("**UNICEF Fixed Term Hourly Rates:**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.number_input(
            "Shift 1 (Regular) - UNICEF",
            min_value=0.0,
            max_value=200.0,
            value=float(DefaultConfig.UNICEF_RATE_SHIFT_1),
            key='unicef_rate_shift_1',
            step=0.01,
            format="%.2f",
            help="Hourly rate for UNICEF Fixed Term staff during regular shift"
        )
    
    with col2:
        st.number_input(
            "Shift 2 (Evening) - UNICEF",
            min_value=0.0,
            max_value=200.0,
            value=float(DefaultConfig.UNICEF_RATE_SHIFT_2),
            key='unicef_rate_shift_2',
            step=0.01,
            format="%.2f",
            help="Hourly rate for UNICEF Fixed Term staff during evening shift"
        )
    
    with col3:
        st.number_input(
            "Shift 3 (Overtime) - UNICEF",
            min_value=0.0,
            max_value=200.0,
            value=float(DefaultConfig.UNICEF_RATE_SHIFT_3),
            key='unicef_rate_shift_3',
            step=0.01,
            format="%.2f",
            help="Hourly rate for UNICEF Fixed Term staff during overtime shift"
        )
    
    st.markdown("**Humanizer Hourly Rates:**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.number_input(
            "Shift 1 (Regular) - Humanizer",
            min_value=0.0,
            max_value=200.0,
            value=float(DefaultConfig.HUMANIZER_RATE_SHIFT_1),
            key='humanizer_rate_shift_1',
            step=0.01,
            format="%.2f",
            help="Hourly rate for Humanizer staff during regular shift"
        )
    
    with col2:
        st.number_input(
            "Shift 2 (Evening) - Humanizer",
            min_value=0.0,
            max_value=200.0,
            value=float(DefaultConfig.HUMANIZER_RATE_SHIFT_2),
            key='humanizer_rate_shift_2',
            step=0.01,
            format="%.2f",
            help="Hourly rate for Humanizer staff during evening shift"
        )
    
    with col3:
        st.number_input(
            "Shift 3 (Overtime) - Humanizer",
            min_value=0.0,
            max_value=200.0,
            value=float(DefaultConfig.HUMANIZER_RATE_SHIFT_3),
            key='humanizer_rate_shift_3',
            step=0.01,
            format="%.2f",
            help="Hourly rate for Humanizer staff during overtime shift"
        )

def render_data_selection_config():
    """Render data selection configuration section"""
    st.header("📊 Data Selection Configuration")
    
    st.markdown("Configure which data elements to include in the optimization.")
    
    # Employee types selection
    st.subheader("👥 Employee Types")
    available_employee_types = ["UNICEF Fixed term", "Humanizer"]
    
    selected_employee_types = st.multiselect(
        "Select Employee Types to Include",
        available_employee_types,
        default=st.session_state.selected_employee_types,
        help="Choose which employee types to include in the optimization"
    )
    st.session_state.selected_employee_types = selected_employee_types
    
    # Shifts selection
    st.subheader("🕐 Shifts")
    available_shifts = list(optimization_config.shift_code_to_name().keys())
    shift_names = optimization_config.shift_code_to_name()
    
    selected_shifts = st.multiselect(
        "Select Shifts to Include",
        available_shifts,
        default=st.session_state.selected_shifts,
        format_func=lambda x: f"Shift {x} ({shift_names[x]})",
        help="Choose which shifts to include in the optimization"
    )
    st.session_state.selected_shifts = selected_shifts
    
    # Production lines selection
    st.subheader("🏭 Production Lines")
    available_lines = list(optimization_config.line_code_to_name().keys())
    line_names = optimization_config.line_code_to_name()
    
    selected_lines = st.multiselect(
        "Select Production Lines to Include",
        available_lines,
        default=st.session_state.selected_lines,
        format_func=lambda x: f"Line {x} ({line_names[x]})",
        help="Choose which production lines to include in the optimization"
    )
    st.session_state.selected_lines = selected_lines
    
    # Validation warnings
    if not selected_employee_types:
        st.error("⚠️ At least one employee type must be selected!")
    if not selected_shifts:
        st.error("⚠️ At least one shift must be selected!")
    if not selected_lines:
        st.error("⚠️ At least one production line must be selected!")

def run_feasibility_check():
    """
    Run feasibility check with current configuration from session state.
    
    This validates that the production plan can meet demand with available resources
    before saving the configuration.
    
    Returns:
        dict: Feasibility results with keys:
            - 'feasible': bool
            - 'warnings': list of warning messages
            - 'errors': list of error messages
            - 'tight_capacity_products': list of products with tight capacity
    """
    from src.models.feasibility_checker import FeasibilityChecker
    from src.demand_filtering import DemandFilter
    from src.preprocess.hierarchy_parser import sort_products_by_hierarchy
    import src.preprocess.extract as extract
    
    # Get date configuration from session state
    from src.config.optimization_config import get_date_configuration
    demand_start_date, production_start_date, production_end_date, planning_days, date_span = get_date_configuration()
    
    # Load product and demand data
    filter_instance = DemandFilter()
    filter_instance.load_data(start_date=demand_start_date, force_reload=True)
    product_list = filter_instance.get_filtered_product_list()
    demand_dictionary = filter_instance.get_filtered_demand_dictionary()
    kit_line_match_dict = filter_instance.get_line_assignments()
    
    # Load hierarchy data
    kit_levels, kit_dependencies, priority_order = extract.get_production_order_data()
    sorted_product_list = sort_products_by_hierarchy(list(product_list), kit_levels, kit_dependencies)
    
    # Load team requirements
    kits_df = extract.read_personnel_requirement_data()
    team_req_per_product = {
        "UNICEF Fixed term": {},
        "Humanizer": {}
    }
    for product in sorted_product_list:
        product_data = kits_df[kits_df['Kit'] == product]
        if not product_data.empty:
            team_req_per_product["Humanizer"][product] = int(product_data["Humanizer"].iloc[0])
            team_req_per_product["UNICEF Fixed term"][product] = int(product_data["UNICEF staff"].iloc[0])
        else:
            team_req_per_product["Humanizer"][product] = 0
            team_req_per_product["UNICEF Fixed term"][product] = 0
    
    # Load product speed data
    per_product_speed = extract.read_package_speed_data()
    
    # Get configuration from session state
    employee_type_list = list(st.session_state.selected_employee_types)
    active_shift_list = sorted(list(st.session_state.selected_shifts))
    
    max_hours_shift = {
        ShiftType.REGULAR: st.session_state.max_hours_shift_1,
        ShiftType.EVENING: st.session_state.max_hours_shift_2,
        ShiftType.OVERTIME: st.session_state.max_hours_shift_3
    }
    
    max_workers_line = {
        LineType.LONG_LINE: st.session_state.max_parallel_workers_long_line,
        LineType.MINI_LOAD: st.session_state.max_parallel_workers_mini_load
    }
    
    max_employee_per_type_on_day = {
        "UNICEF Fixed term": {t: st.session_state.max_unicef_per_day for t in date_span},
        "Humanizer": {t: st.session_state.max_humanizer_per_day for t in date_span}
    }
    
    # Run feasibility check
    results = FeasibilityChecker.check_production_feasibility(
        sorted_product_list=sorted_product_list,
        employee_type_list=employee_type_list,
        team_req_per_product=team_req_per_product,
        demand_dictionary=demand_dictionary,
        kit_line_match_dict=kit_line_match_dict,
        per_product_speed=per_product_speed,
        max_workers_line=max_workers_line,
        max_employee_type_day=max_employee_per_type_on_day,
        max_hours_shift=max_hours_shift,
        active_shift_list=active_shift_list,
        date_span_list=date_span
    )
    
    return results


def save_configuration():
    """
    Save current configuration to session state.
    
    ⚠️ SINGLE SOURCE OF TRUTH for date configuration ⚠️
    This is the ONLY function that should update date-related session_state values.
    
    Flow:
    1. Read user's selected dates from UI (demand_start_date, production_start_date, production_end_date)
    2. Calculate planning_days and date_span from production dates
    3. Validate demand data exists for the demand_start_date
    4. Update session_state with all date configuration
    5. optimization_config.get_date_configuration() reads from session_state
    6. All modules use get_date_configuration() for consistency
    
    Returns:
        dict: Configuration dictionary if successful, None if validation fails
    """
    
    import src.preprocess.extract as extract
    import pandas as pd
    from datetime import datetime, timedelta
    
    # Validate production dates
    if st.session_state.production_end_date < st.session_state.production_start_date:
        st.error("❌ Production end date must be after or equal to start date!")
        return None
    
    # Calculate planning_days from production dates
    planning_days = (st.session_state.production_end_date - st.session_state.production_start_date).days + 1
    date_span = list(range(1, planning_days + 1))
    
    # Update session state with calculated values
    st.session_state.planning_days = planning_days
    st.session_state.date_span = date_span
    
    # Validate demand data exists for the selected demand_start_date
    demand_datetime = datetime.combine(st.session_state.demand_start_date, datetime.min.time())
    demand_data = extract.read_orders_data(start_date=demand_datetime)
    
    if demand_data.empty:
        st.warning(f"⚠️ No demand data found for {st.session_state.demand_start_date}")
    
    # Create comprehensive configuration dictionary
    config = {
        'date_range': {
            'demand_start_date': st.session_state.demand_start_date,  # demand filtering date
            'production_start_date': st.session_state.production_start_date,  # production start
            'production_end_date': st.session_state.production_end_date,  # production end
            'planning_days': planning_days,  # production days (calculated from production dates)
            'date_span': date_span,  # [1, 2, 3, ..., planning_days]
        },
        'schedule_type': st.session_state.schedule_type,
        'fixed_staff_mode': st.session_state.fixed_staff_mode,
        'payment_mode_config': {
            ShiftType.REGULAR: st.session_state.payment_mode_shift_1,
            ShiftType.EVENING: st.session_state.payment_mode_shift_2,
            ShiftType.OVERTIME: st.session_state.payment_mode_shift_3,
        },
        'workforce_limits': {
            'max_unicef_per_day': st.session_state.max_unicef_per_day,
            'max_humanizer_per_day': st.session_state.max_humanizer_per_day,
            'fixed_min_unicef_per_day': st.session_state.fixed_min_unicef_per_day,
        },
        'working_hours': {
            'max_hour_per_person_per_day': st.session_state.max_hour_per_person_per_day,
            'max_hours_per_shift': {
                ShiftType.REGULAR: st.session_state.max_hours_shift_1,
                ShiftType.EVENING: st.session_state.max_hours_shift_2,
                ShiftType.OVERTIME: st.session_state.max_hours_shift_3,
            }
        },
        'operations': {
            'line_counts': {
                LineType.LONG_LINE: st.session_state.line_count_long_line,
                LineType.MINI_LOAD: st.session_state.line_count_mini_load,
            },
            'max_parallel_workers': {
                LineType.LONG_LINE: st.session_state.max_parallel_workers_long_line,
                LineType.MINI_LOAD: st.session_state.max_parallel_workers_mini_load,
            }
        },
        'cost_rates': {
            'UNICEF Fixed term': {
                ShiftType.REGULAR: st.session_state.unicef_rate_shift_1,
                ShiftType.EVENING: st.session_state.unicef_rate_shift_2,
                ShiftType.OVERTIME: st.session_state.unicef_rate_shift_3,
            },
            'Humanizer': {
                ShiftType.REGULAR: st.session_state.humanizer_rate_shift_1,
                ShiftType.EVENING: st.session_state.humanizer_rate_shift_2,
                ShiftType.OVERTIME: st.session_state.humanizer_rate_shift_3,
            }
        },
        'data_selection': {
            'selected_employee_types': st.session_state.get('selected_employee_types', []),
            'selected_shifts': st.session_state.get('selected_shifts', []),
            'selected_lines': st.session_state.get('selected_lines', []),
        }
    }
    
    # Store individual items in session state for optimization_config.py to access
    st.session_state.line_counts = config['operations']['line_counts']
    st.session_state.cost_list_per_emp_shift = config['cost_rates']
    st.session_state.payment_mode_config = config['payment_mode_config']
    st.session_state.max_employee_per_type_on_day = {
        "UNICEF Fixed term": {t: st.session_state.max_unicef_per_day for t in st.session_state.date_span},
        "Humanizer": {t: st.session_state.max_humanizer_per_day for t in st.session_state.date_span}
    }
    
    # Store complete configuration
    st.session_state.optimization_config = config
    
    # Refresh module-level variables to pick up new configuration
    # try:
    #     from src.config.optimization_config import _ensure_fresh_config
    #     _ensure_fresh_config()
    #     print("✅ Refreshed module-level configuration variables")
    # except Exception as e:
    #     print(f"⚠️ Could not refresh module-level variables: {e}")
    
    # ============================================================
    # FEASIBILITY CHECK: Run and store results in session state
    # ============================================================
    # Run feasibility check and store results for display in UI
    try:
        import io
        from contextlib import redirect_stdout
        
        # Create string buffer to capture print output
        output_buffer = io.StringIO()
        
        # Run feasibility check and capture output
        with redirect_stdout(output_buffer):
            feasibility_results = run_feasibility_check()
        
        # Get captured output
        captured_output = output_buffer.getvalue()
        
        # Store results in session state for display after save
        feasibility_cache_key = f"feasibility_results_{st.session_state.get('demand_start_date', 'default')}"
        st.session_state[feasibility_cache_key] = {
            'results': feasibility_results,
            'captured_output': captured_output
        }
        st.session_state['show_feasibility_after_save'] = True
        
        # Check if configuration is infeasible - block saving if so
        if not feasibility_results['feasible']:
            st.error("❌ **Configuration is INFEASIBLE!**")
            st.error("Cannot save configuration - it cannot meet production demand with available resources.")
            st.error("**Please review feasibility issues below and adjust your configuration.**")
            return None  # Don't save infeasible configuration
    
    except Exception as e:
        st.error(f"❌ Error during feasibility check: {e}")
        import traceback
        st.error("**Cannot save configuration due to feasibility check error.**")
        with st.expander("🔍 Error Details"):
            st.code(traceback.format_exc(), language="python")
        return None
    
    # Return config for use in main function
    return config

def display_user_friendly_summary(config):
    """Display a user-friendly summary of the configuration settings"""
    
    # Schedule Settings
    st.subheader("📅 Schedule Settings")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Demand Start Date:** {config['date_range']['demand_start_date']}")
        st.caption("Date used to filter demand data")
    with col2:
        st.write(f"**Schedule Type:** {config['schedule_type'].title()}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Production Start:** {config['date_range']['production_start_date']}")
    with col2:
        st.write(f"**Production End:** {config['date_range']['production_end_date']}")
    with col3:
        st.write(f"**Planning Period:** {config['date_range']['planning_days']} days")
    
    # Add evening shift mode in new row
    # Workforce Settings
    st.subheader("👥 Workforce Settings")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Max UNICEF Staff per Day:** {config['workforce_limits']['max_unicef_per_day']} people")
        st.write(f"**Max Humanizer Staff per Day:** {config['workforce_limits']['max_humanizer_per_day']} people")
        st.write(f"**Fixed Minimum UNICEF per Day:** {config['workforce_limits']['fixed_min_unicef_per_day']} people")
    with col2:
        st.write(f"**Staff Management Mode:** {config['fixed_staff_mode'].replace('_', ' ').title()}")
        st.write(f"**Max Hours per Person per Day:** {config['working_hours']['max_hour_per_person_per_day']} hours")
    
    # Operations Settings
    st.subheader("🏭 Operations Settings")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Long Lines Available:** {config['operations']['line_counts'][LineType.LONG_LINE]} lines")
        st.write(f"**Mini Load Lines Available:** {config['operations']['line_counts'][LineType.MINI_LOAD]} lines")
    with col2:
        st.write(f"**Max Workers per Long Line:** {config['operations']['max_parallel_workers'][LineType.LONG_LINE]} people")
        st.write(f"**Max Workers per Mini Load Line:** {config['operations']['max_parallel_workers'][LineType.MINI_LOAD]} people")
    
    # Cost Settings
    st.subheader("💰 Cost Settings")
    st.write("**Hourly Rates:**")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("*UNICEF Fixed Term Staff:*")
        st.write(f"• Regular Shift: ﹩{config['cost_rates']['UNICEF Fixed term'][ShiftType.REGULAR]:.2f}/hour")
        st.write(f"• Evening Shift: ﹩{config['cost_rates']['UNICEF Fixed term'][ShiftType.EVENING]:.2f}/hour") 
        st.write(f"• Overtime Shift: ﹩{config['cost_rates']['UNICEF Fixed term'][ShiftType.OVERTIME]:.2f}/hour")
    
    with col2:
        st.write("*Humanizer Staff:*")
        st.write(f"• Regular Shift: ﹩{config['cost_rates']['Humanizer'][ShiftType.REGULAR]:.2f}/hour")
        st.write(f"• Evening Shift: ﹩{config['cost_rates']['Humanizer'][ShiftType.EVENING]:.2f}/hour")
        st.write(f"• Overtime Shift: ﹩{config['cost_rates']['Humanizer'][ShiftType.OVERTIME]:.2f}/hour")
    
    # Payment Settings
    st.write("**Payment Modes:**")
    payment_descriptions = {
        'bulk': 'Full shift payment (even for partial hours)',
        'partial': 'Pay only for actual hours worked'
    }
    
    col1, col2, col3 = st.columns(3)
    with col1:
        mode = config['payment_mode_config'][ShiftType.REGULAR]
        st.write(f"• **Regular Shift:** {mode.title()}")
        st.caption(payment_descriptions[mode])
    with col2:
        mode = config['payment_mode_config'][ShiftType.EVENING] 
        st.write(f"• **Evening Shift:** {mode.title()}")
        st.caption(payment_descriptions[mode])
    with col3:
        mode = config['payment_mode_config'][ShiftType.OVERTIME]
        st.write(f"• **Overtime Shift:** {mode.title()}")
        st.caption(payment_descriptions[mode])
    
    # Data Selection Settings (if available)
    if 'data_selection' in config:
        st.subheader("📊 Data Selection")
        col1, col2, col3 = st.columns(3)
        with col1:
            employee_types = config['data_selection']['selected_employee_types']
            st.write(f"**Employee Types:** {len(employee_types)} selected")
            for emp_type in employee_types:
                st.write(f"• {emp_type}")
        
        with col2:
            shifts = config['data_selection']['selected_shifts']
            shift_names = ShiftType.get_all_names()
            st.write(f"**Shifts:** {len(shifts)} selected")
            for shift in shifts:
                st.write(f"• Shift {shift} ({shift_names.get(shift, 'Unknown')})")
        
        with col3:
            lines = config['data_selection']['selected_lines']
            line_names = LineType.get_all_names()
            st.write(f"**Production Lines:** {len(lines)} selected")
            for line in lines:
                st.write(f"• Line {line} ({line_names.get(line, 'Unknown')})")
    
    # Summary totals
    st.subheader("📊 Quick Summary")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        duration = config['date_range']['planning_days']
        st.metric("Planning Period", f"{duration} days")
    
    with col2:
        total_staff = config['workforce_limits']['max_unicef_per_day'] + config['workforce_limits']['max_humanizer_per_day']
        st.metric("Max Daily Staff", f"{total_staff} people")
    
    with col3:
        total_lines = config['operations']['line_counts'][LineType.LONG_LINE] + config['operations']['line_counts'][LineType.MINI_LOAD]
        st.metric("Production Lines", f"{total_lines} lines")
    
    with col4:
        avg_unicef_rate = sum(config['cost_rates']['UNICEF Fixed term'].values()) / 3
        st.metric("Avg UNICEF Rate", f"﹩{avg_unicef_rate:.2f}/hr")
    
    # Demand Data Preview
    st.subheader("📊 Demand Data Preview")
    try:
        import src.preprocess.extract as extract
        from datetime import datetime
        
        # Get demand data for the configured demand start date
        demand_start_date = config['date_range']['demand_start_date']
        demand_datetime = datetime.combine(demand_start_date, datetime.min.time())
        demand_data = extract.read_orders_data(start_date=demand_datetime)
        
        if not demand_data.empty:
            # Show summary statistics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📦 Total Orders", len(demand_data))
            
            with col2:
                total_quantity = demand_data['Order quantity (GMEIN)'].sum()
                st.metric("📊 Total Quantity", total_quantity)
            
            with col3:
                unique_products = demand_data['Material Number'].nunique()
                st.metric("🏷️ Unique Products", unique_products)
            
            with col4:
                # Calculate date range
                if 'Basic finish date' in demand_data.columns:
                    import pandas as pd
                    finish_dates = pd.to_datetime(demand_data['Basic finish date']).dt.date
                    min_finish = finish_dates.min()
                    max_finish = finish_dates.max()
                    if min_finish == max_finish:
                        date_range = f"{min_finish}"
                    else:
                        date_range = f"{min_finish} to {max_finish}"
                else:
                    date_range = "N/A"
                st.metric("📅 Finish Dates for the start date orders", date_range)
            
            # Show top products
            if 'Material' in demand_data.columns and 'Quantity' in demand_data.columns:
                with st.expander("🔝 Top 10 Products by Quantity", expanded=False):
                    top_products = demand_data.groupby('Material')['Quantity'].sum().sort_values(ascending=False).head(10)
                    
                    if not top_products.empty:
                        # Create a nice table
                        import pandas as pd
                        top_products_df = pd.DataFrame({
                            'Product': top_products.index,
                            'Total Quantity': top_products.values
                        }).reset_index(drop=True)
                        top_products_df.index = top_products_df.index + 1  # Start index from 1
                        st.dataframe(top_products_df, use_container_width=True)
                    else:
                        st.info("No product quantity data available.")
            
        else:
            st.warning(f"⚠️ No demand data found for {demand_start_date}. Please select a different date or check your data files.")
            
    except Exception as e:
        st.error(f"❌ Error loading demand data: {e}")

def clear_all_cache_and_results():
    """Clear all cached data, modules, and results from previous runs"""
    import importlib
    import sys
    
    print("🧹 Clearing all cached data and previous results...")
    # st.info("🧹 Clearing all cached data and previous results...")
    
    # Clear optimization cache using the dedicated function
    clear_optimization_cache()
    
    # Clear additional optimization-related session state
    keys_to_clear = [
        'demand_dictionary',
        'kit_hierarchy_data',
        'team_requirements'
    ]
    
    cleared_keys = []
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
            cleared_keys.append(key)
    
    if cleared_keys:
        st.write(f"🗑️ Cleared session state: {', '.join(cleared_keys)}")
    
    # 2. Force reload all related modules to clear any module-level caches
    modules_to_reload = [
        'src.preprocess.extract',
        'src.config.optimization_config',
        'src.models.optimizer_real'
    ]
    
    reloaded_modules = []
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
            reloaded_modules.append(module_name)
    
    if reloaded_modules:
        # st.write(f"🔄 Reloaded modules: {', '.join(reloaded_modules)}")
        print(f"🔄 Reloaded modules: {', '.join(reloaded_modules)}")
    
    # # 3. Get end date from session state (calculated during save) and update global dates
    # if 'end_date' in st.session_state and 'planning_days' in st.session_state:
    #     calculated_end_date = st.session_state.end_date
    #     planning_days = st.session_state.planning_days
    # else:
    #     # Fallback - use start date only for now, will be recalculated
    #     from datetime import timedelta
    #     calculated_end_date = st.session_state.start_date + timedelta(days=4)
    #     planning_days = 5
    
    # Note: Dates are stored in st.session_state and read directly by optimizer
    # All components read dates from st.session_state.start_date and st.session_state.planning_days
    # st.write(f"📅 Date configuration: {st.session_state.start_date} to {calculated_end_date} ({planning_days} days)")
    # st.info("💡 Dates will be applied when optimization runs (read directly from st.session_state)")
    print("💡 Dates will be applied when optimization runs (read directly from st.session_state)")
    print("✅ All caches and previous results cleared!")
    # st.success("✅ All caches and previous results cleared!")

def run_optimization():
    """Run the optimization model and store results"""
    
    # Auto-hide validation panel when optimization starts
    st.session_state.show_validation_after_save = False
    st.session_state.settings_just_saved = False
    
    try:
        st.info("🔄 Running optimization... This may take a few moments.")
    
        
        # Always clear everything first for clean slate
        clear_all_cache_and_results()
        
        # Show brief validation summary
        # st.info("📋 Performing pre-optimization data validation...")
        validation_warnings = check_critical_data_issues()
        if validation_warnings:
            with st.expander("⚠️ Data Validation Warnings", expanded=True):
                for warning in validation_warnings:
                    st.warning(f"• {warning}")
                st.warning("**Optimization may fail due to these issues. Consider fixing them first.**")
        else:
            print("✅ Data validation passed - no critical issues detected")
            # st.success("✅ Data validation passed - no critical issues detected")
        
        # Show current configuration being used  
        
        demand_start_date, production_start_date, production_end_date, planning_days, date_span = optimization_config.get_date_configuration()

        st.info(f"📊 **Demand Date**: {demand_start_date} (filtering demand data)")
        st.info(f"🏭 **Production Period**: {production_start_date} to {production_end_date} ({planning_days} days)")

        
        st.info(f"👥 Max UNICEF/day: {st.session_state.max_unicef_per_day}, Max Humanizer/day: {st.session_state.max_humanizer_per_day}")
        
        # Import and run the optimization (after clearing)
        from src.models.optimizer_real import Optimizer
        
        # Run the optimization using Optimizer class
        with st.spinner('Optimizing workforce schedule...'):
            optimizer = Optimizer()
            results = optimizer.run_optimization()
        
        if results is None:
            st.error("❌ Optimization failed! The problem may be infeasible with current settings.")
            if validation_warnings:
                st.error("💡 **Likely cause:** Data validation warnings detected above. Fix missing line assignments and other data issues first.")
            st.error("Try adjusting your workforce limits, line counts, or evening shift settings.")
            return
        
        # Store results in session state
        st.session_state.optimization_results = results
        
        # Save optimization results to JSON
        try:
            from src.utils.result_saver import save_optimization_result_to_json
            json_file_path = save_optimization_result_to_json(optimizer, results)
            st.success(f"✅ Optimization completed successfully!")
            st.info(f"📄 Results saved to: {json_file_path}")
        except Exception as json_error:
            st.warning(f"⚠️ Optimization completed, but failed to save JSON: {json_error}")
        
        st.rerun()  # Refresh to show results
        
    except Exception as e:
        import traceback
        st.error(f"❌ Error during optimization: {str(e)}")
        st.error("Please check your settings and data files.")
        
        # Show detailed traceback in expander
        with st.expander("🔍 Show detailed error traceback"):
            st.code(traceback.format_exc())
        
        # Also print to console for debugging
        print("\n" + "="*60)
        print("❌ OPTIMIZATION ERROR - FULL TRACEBACK:")
        print("="*60)
        traceback.print_exc()
        print("="*60)

def check_critical_data_issues():
    """
    Quick check for critical data issues that could cause optimization failure
    Returns list of warning messages
    """
    warnings = []
    
    try:
        # Add src to path if needed
        from src.demand_validation_viz import DemandValidationViz
        
        # Initialize validator and load data
        validator = DemandValidationViz()
        if not validator.load_data():
            warnings.append("Failed to load validation data")
            return warnings
        
        # Quick validation check
        validation_df = validator.validate_all_products()
        summary_stats = validator.get_summary_statistics(validation_df)
        
        # Check for critical issues
        if summary_stats['no_line_assignment'] > 0:
            warnings.append(f"{summary_stats['no_line_assignment']} products missing line assignments")
        
        if summary_stats['no_staffing'] > 0:
            warnings.append(f"{summary_stats['no_staffing']} products missing staffing requirements")
        
        if summary_stats['no_speed'] > 0:
            warnings.append(f"{summary_stats['no_speed']} products missing production speed data")
        
        # Calculate failure risk
        # invalid_ratio = summary_stats['invalid_products'] / summary_stats['total_products']
        # if invalid_ratio > 0.5:
        #     warnings.append(f"High failure risk: {invalid_ratio:.0%} of products have data issues")
        
        return warnings
        
    except Exception as e:
        warnings.append(f"Validation check failed: {str(e)}")
        return warnings

