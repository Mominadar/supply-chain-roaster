"""
Optimization Results Display Functions for Streamlit
Handles visualization of optimization results with charts and tables
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
import json
import base64
from ui.reports.optimization_pdf import generate_optimization_report

# Load hierarchy data for enhanced visualization
def load_kit_hierarchy():
    """Load kit hierarchy data from JSON file"""
    try:
        with open('data/hierarchy_exports/kit_hierarchy.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def get_kit_hierarchy_info(product):
    """Get hierarchy level and dependencies for a product using main optimization system"""
    try:
        # Import from the main optimization system
        from src.config.optimization_config import KIT_LEVELS, KIT_DEPENDENCIES
        from src.config.constants import KitLevel
        
        # Use the same hierarchy system as the optimizer
        if product in KIT_LEVELS:
            level = KIT_LEVELS[product]
            level_name = KitLevel.get_name(level)
            dependencies = KIT_DEPENDENCIES.get(product, [])
            return level_name, dependencies
        else:
            return 'unknown', []
            
    except Exception as e:
        print(f"Error getting hierarchy info for {product}: {e}")
        return 'unknown', []


def parse_schedule_from_json(results):
    """
    Parse the nested schedule structure from JSON into a flat list format.
    This makes it compatible with existing visualization functions.
    
    Returns:
        list: Flattened schedule data with each row representing a production run
    """
    schedule_list = []
    
    # Check if results has the nested schedule structure
    if 'results' not in results or 'schedule' not in results['results']:
        return []
    
    schedule_data = results['results']['schedule']
    
    # Iterate through each day
    for day_key, day_data in schedule_data.items():
        # Extract day number from 'day_1' format
        day_id = day_data.get('day_id', int(day_key.split('_')[1]))
        
        # Iterate through each line (skip 'day_id' key)
        for line_key, line_data in day_data.items():
            if line_key == 'day_id':
                continue
                
            line_type = line_data.get('line_type', 'Unknown')
            line_type_id = line_data.get('line_type_id', 0)
            line_idx = line_data.get('line_idx', 0)
            
            # Iterate through each shift
            for shift_key, shift_data in line_data.items():
                if shift_key in ['line_type', 'line_type_id', 'line_idx']:
                    continue
                
                # Extract shift number from 'shift_1' format
                shift_id = int(shift_key.split('_')[1])
                shift_name = shift_data.get('shift_name', 'Unknown')
                
                # Iterate through products in this shift
                products = shift_data.get('products', [])
                for product_data in products:
                    schedule_list.append({
                        'day': day_id,
                        'line_type': line_type,
                        'line_type_id': line_type_id,
                        'line_idx': line_idx,
                        'shift': shift_id,
                        'shift_name': shift_name,
                        'product': product_data.get('product', ''),
                        'run_hours': product_data.get('run_hours', 0),
                        'units': product_data.get('units', 0),
                        'employees': product_data.get('employees', {})
                    })
    
    return schedule_list


def parse_production_from_json(results):
    """
    Parse the production data from JSON into a simple dictionary format.
    
    Returns:
        dict: Product -> units_produced mapping
    """
    production_dict = {}
    
    # Check if results has the nested production structure
    if 'results' not in results or 'production' not in results['results']:
        return {}
    
    production_data = results['results']['production']
    
    # Extract by_product data
    by_product = production_data.get('by_product', {})
    for product, product_data in by_product.items():
        production_dict[product] = product_data.get('units_produced', 0)
    
    return production_dict


def get_compatible_results(results):
    """
    Convert new JSON structure to format compatible with existing visualization functions.
    This function checks which format the results are in and converts if necessary.
    
    Returns:
        dict: Results with 'run_schedule', 'weekly_production', and all nested 'results' data
    """
    # Check if already in old format
    if 'run_schedule' in results and 'weekly_production' in results:
        return results
    
    # Convert from new format to old format (preserve all original data)
    compatible_results = results.copy()
    compatible_results['run_schedule'] = parse_schedule_from_json(results)
    compatible_results['weekly_production'] = parse_production_from_json(results)
    
    # Also ensure objective is available
    if 'objective' not in compatible_results:
        if 'metadata' in results and 'optimal_cost' in results['metadata']:
            compatible_results['objective'] = results['metadata']['optimal_cost']
        else:
            compatible_results['objective'] = 0
    
    # Preserve the entire 'results' section (includes cost_breakdown, employee_allocation, etc.)
    # This is already preserved by results.copy() since it's a shallow copy
    
    return compatible_results


def display_optimization_results(results):
    """Display comprehensive optimization results with visualizations"""
    st.header("📊 Optimization Results")
    
    # Export Button
    col_head, col_btn = st.columns([6, 1])
    with col_btn:
        if st.button("📄 Export PDF"):
            try:
                pdf_bytes = generate_optimization_report(results)
                b64 = base64.b64encode(pdf_bytes).decode()
                href = f'<a href="data:application/pdf;base64,{b64}" download="optimization_results.pdf" style="text-decoration:none;">' \
                       f'<button style="background-color:#FF4B4B;color:white;border:none;padding:0.5rem 1rem;border-radius:0.3rem;cursor:pointer;">' \
                       f'⬇️ Download PDF</button></a>'
                st.markdown(href, unsafe_allow_html=True)
                st.toast("PDF generated successfully!", icon="✅")
            except Exception as e:
                st.error(f"Error generating PDF: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📈 Weekly Summary", 
        "📅 Daily Deep Dive", 
        "🏭 Line Schedules", 
        "📦 Kit Production", 
        "💰 Cost Analysis",
        "🔍 Input Data",
        "📋 Demand Validation"
    ])
    
    with tab1:
        display_weekly_summary(results)
    
    with tab2:
        display_daily_deep_dive(results)
    
    with tab3:
        display_line_schedules(results)
    
    with tab4:
        display_kit_production(results)
    
    with tab5:
        display_cost_analysis(results)
    
    with tab6:
        display_input_data_inspection()
    
    with tab7:
        display_demand_validation_tab()

def display_weekly_summary(results):
    """Display weekly summary with key metrics and charts"""
    # Convert to compatible format if needed
    results = get_compatible_results(results)
    
    st.subheader("📈 Weekly Performance Summary")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_cost = results['objective']
        st.metric("Total Cost", f"€{total_cost:,.2f}")
    
    with col2:
        total_production = sum(results['weekly_production'].values())
        st.metric("Total Production", f"{total_production:,.0f} units")
    
    with col3:
        # Calculate fulfillment rate
        from src.config.optimization_config import get_demand_dictionary
        DEMAND_DICTIONARY = get_demand_dictionary()
        total_demand = sum(DEMAND_DICTIONARY.values())
        fulfillment_rate = (total_production / total_demand * 100) if total_demand > 0 else 0
        st.metric("Fulfillment Rate", f"{fulfillment_rate:.1f}%")
    
    with col4:
        # Calculate cost per unit
        cost_per_unit = total_cost / total_production if total_production > 0 else 0
        st.metric("Cost per Unit", f"€{cost_per_unit:.2f}")
    
    # Production vs Demand Chart
    st.subheader("🎯 Production vs Demand")
    
    from src.config.optimization_config import get_demand_dictionary
    DEMAND_DICTIONARY = get_demand_dictionary()
    prod_demand_data = []
    for product, production in results['weekly_production'].items():
        demand = DEMAND_DICTIONARY.get(product, 0)
        prod_demand_data.append({
            'Product': product,
            'Production': production,
            'Demand': demand,
            'Gap': production - demand
        })
    
    df_prod = pd.DataFrame(prod_demand_data)
    
    if not df_prod.empty:
        # Bar chart comparing production vs demand
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Production', x=df_prod['Product'], y=df_prod['Production'], 
                            marker_color='lightblue'))
        fig.add_trace(go.Bar(name='Demand', x=df_prod['Product'], y=df_prod['Demand'],
                            marker_color='orange'))
        
        fig.update_layout(
            title='Weekly Production vs Demand by Product',
            xaxis_title='Product',
            yaxis_title='Units',
            barmode='group',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True, key="weekly_prod_vs_demand")

def display_daily_deep_dive(results):
    """Display daily breakdown with employee counts by type and shift"""
    # Convert to compatible format if needed
    results = get_compatible_results(results)
    
    st.subheader("📅 Daily Employee Count by Type and Shift")
    st.markdown("""
    This visualization shows the **EMPLOYEE_COUNT[e, s, t]** optimization variable values.
    This is the actual optimized employee count for each employee type (e), shift (s), and day (t).
    """)
    
    # Extract EMPLOYEE_COUNT optimization variable data
    employee_count_data_raw = []
    
    # Check if data is in the results structure
    if 'results' in results and 'employee_count_optimized' in results['results']:
        employee_count_data_raw = results['results']['employee_count_optimized']
    elif 'employee_count_optimized' in results:
        employee_count_data_raw = results['employee_count_optimized']
    
    # If EMPLOYEE_COUNT data is available, use it; otherwise fall back to schedule data
    using_employee_count_optimized = False
    df_employees = None
    
    if employee_count_data_raw:
        # Use EMPLOYEE_COUNT optimization variable
        using_employee_count_optimized = True
        employee_count_list = []
        for emp_data in employee_count_data_raw:
            day = f"Day {emp_data['day']}"
            employee_count_list.append({
                'Day': day,
                'Employee Type': emp_data['employee_type'],
                'Shift': emp_data['shift_name'],
                'Employee Count': emp_data['employee_count'],
                'Max Available': emp_data.get('max_available', 0)
            })
        
        df_summary = pd.DataFrame(employee_count_list)
        

        
        # Create stacked bar chart showing employee counts by shift
        fig = px.bar(df_summary, 
                    x='Day', 
                    y='Employee Count', 
                    color='Shift',
                    facet_col='Employee Type',
                    title='Daily Employee Count by Type and Shift (EMPLOYEE_COUNT Variable)',
                    color_discrete_map={
                        'Regular': '#32CD32',    # Green
                        'Overtime': '#FF8C00',   # Orange
                        'Evening': '#4169E1'     # Blue
                    },
                    text='Employee Count',  # Add numbers on bars
                    height=500)
        
        # Update text position and format
        fig.update_traces(texttemplate='%{text}', textposition='inside')
        
        fig.update_layout(
            yaxis_title='Number of Employees',
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True, key="daily_employee_count")
        
        # Detailed breakdown table
        st.subheader("📋 Employee Allocation Details")
        
        # Show summary by day and shift with capacity context
        st.markdown("**Summary by Day and Shift:**")
        summary_pivot = df_summary.pivot_table(
            values='Employee Count', 
            index=['Day', 'Shift'], 
            columns='Employee Type', 
            aggfunc='sum', 
            fill_value=0
        ).reset_index()
        
        # Add capacity information
        try:
            from src.config.optimization_config import get_max_employee_per_type_on_day
            MAX_EMPLOYEE_PER_TYPE_ON_DAY = get_max_employee_per_type_on_day()  # Dynamic call
            
            # Add capacity columns (removed utilization percentage)
            for emp_type in ['UNICEF Fixed term', 'Humanizer']:
                if emp_type in summary_pivot.columns:
                    capacity_col = f'{emp_type} Capacity'
                    
                    # Extract day number from 'Day X' format
                    summary_pivot['Day_Num'] = summary_pivot['Day'].str.extract(r'(\d+)').astype(int)
                    
                    # Get capacity for each day
                    summary_pivot[capacity_col] = summary_pivot['Day_Num'].apply(
                        lambda day: MAX_EMPLOYEE_PER_TYPE_ON_DAY.get(emp_type, {}).get(day, 0)
                    )
            
            # Drop temporary column
            summary_pivot = summary_pivot.drop('Day_Num', axis=1)
            
        except Exception as e:
            print(f"Could not add capacity information: {e}")
        
        st.dataframe(summary_pivot, use_container_width=True)
        
        # Show detailed breakdown (only if we have product-level data from schedule)
        if not using_employee_count_optimized and df_employees is not None and 'Product' in df_employees.columns:
            st.markdown("**Detailed Production Assignments:**")
            df_detailed = df_employees[['Day', 'Employee Type', 'Shift', 'Product', 'Employee Count', 'Hours Worked']].copy()
            df_detailed = df_detailed.sort_values(['Day', 'Shift', 'Employee Type'])
            st.dataframe(df_detailed, use_container_width=True)
        else:
            # Show EMPLOYEE_COUNT detailed data
            st.markdown("**Detailed EMPLOYEE_COUNT Data:**")
            df_detailed = df_summary[['Day', 'Employee Type', 'Shift', 'Employee Count']].copy()
            if 'Max Available' in df_summary.columns:
                df_detailed['Max Available'] = df_summary['Max Available']
                df_detailed['Utilization %'] = (df_detailed['Employee Count'] / df_detailed['Max Available'] * 100).round(1)
            df_detailed = df_detailed.sort_values(['Day', 'Employee Type', 'Shift'])
            st.dataframe(df_detailed, use_container_width=True)
        
    else:
        st.info("📭 No employees scheduled - All production runs have zero hours and zero units")
        
        # Show debug info about filtered rows
        total_schedule_rows = len(results.get('run_schedule', []))
        if total_schedule_rows > 0:
            st.markdown(f"*Note: {total_schedule_rows} schedule entries exist but all have zero production activity*")

def display_line_schedules(results):
    """Display line schedules showing what runs when and with how many workers"""
    # Convert to compatible format if needed
    results = get_compatible_results(results)
    
    st.subheader("🏭 Production Line Schedules")
    
    # Extract line-level employee allocation from cost_breakdown
    line_employee_allocation = {}  # {(day, line_type_id, line_idx, shift): {emp_type: count}}
    
    if 'results' in results and 'cost_breakdown' in results['results']:
        for detail in results['results']['cost_breakdown'].get('detailed_costs', []):
            key = (detail['day'], detail['line_type_id'], detail['line_idx'], detail['shift'])
            if key not in line_employee_allocation:
                line_employee_allocation[key] = {}
            line_employee_allocation[key][detail['employee_type']] = detail.get('max_employees_on_line', 0)
    
    schedule_data = []
    from src.config.optimization_config import get_demand_dictionary, shift_code_to_name, line_code_to_name
    DEMAND_DICTIONARY = get_demand_dictionary()
    
    # Get the mapping dictionaries
    shift_names = shift_code_to_name()
    line_names = line_code_to_name()
    
    for row in results['run_schedule']:
        # Get team requirements from employees data (product-level)
        employees_dict = row.get('employees', {})
        product_unicef = employees_dict.get('UNICEF Fixed term', 0)
        product_humanizer = employees_dict.get('Humanizer', 0)
        product_total = product_unicef + product_humanizer
        
        # Get line-level employee allocation (actual workers assigned to this line)
        line_key = (row['day'], row['line_type_id'], row['line_idx'], row['shift'])
        line_employees = line_employee_allocation.get(line_key, {})
        line_unicef = line_employees.get('UNICEF Fixed term', 0)
        line_humanizer = line_employees.get('Humanizer', 0)
        line_total = line_unicef + line_humanizer
        
        # Get demand for this product
        kit_total_demand = DEMAND_DICTIONARY.get(row['product'], 0)
        
        # Convert codes to readable names
        line_name = line_names.get(row['line_type_id'], f"Line {row['line_type_id']}")
        shift_name = shift_names.get(row['shift'], f"Shift {row['shift']}")
        
        schedule_data.append({
            'Day': f"Day {row['day']}",
            'Line': f"{line_name} {row['line_idx']}",
            'Line_Type_ID': row['line_type_id'],
            'Shift': shift_name,
            'Shift_ID': row['shift'],  # Store original shift number for timing comparison
            'Product': row['product'],
            'Kit Total Demand': kit_total_demand,
            'Hours': round(row['run_hours'], 2),
            'Units': round(row['units'], 0),
            # Product-level workers (for this specific product)
            'Product UNICEF': product_unicef,
            'Product Humanizer': product_humanizer,
            'Product Workers': product_total,
            # Line-level workers (total assigned to this line for the shift)
            'Line UNICEF': int(line_unicef),
            'Line Humanizer': int(line_humanizer),
            'Line Total Workers': int(line_total)
        })
    
    # --- ADDED: Process schedule data to include padding ---
    # To visualize padding, we need to insert "Padding" entries between products on the same line/shift
    
    # Get padding duration in hours
    try:
        if 'time_padding' in st.session_state:
            padding_minutes = st.session_state.time_padding
        else:
            from src.config.constants import DefaultConfig
            padding_minutes = DefaultConfig.DEFAULT_TIME_PADDING
            
        padding_hours = padding_minutes / 60.0
    except:
        padding_hours = 0
        
    final_schedule_data = []

    # --- REFACTORED: Process schedule data using Queue and Real Dates ---
    # User Request: Use better data structure (Queue) and remove dummy dates
    
    from collections import deque
    import datetime
    
    # Get Real Start Date
    try:
        from src.config.optimization_config import get_date_configuration
        _, production_start_date, _, _, _ = get_date_configuration()
        # Ensure it's a datetime object
        if isinstance(production_start_date, datetime.date) and not isinstance(production_start_date, datetime.datetime):
             base_production_date = datetime.datetime.combine(production_start_date, datetime.time(8, 0)) # Default 08:00 AM start
        elif isinstance(production_start_date, datetime.datetime):
             base_production_date = production_start_date.replace(hour=8, minute=0, second=0, microsecond=0)
        else:
             base_production_date = datetime.datetime(2025, 1, 1, 8, 0, 0) # Fallback
    except:
        base_production_date = datetime.datetime(2025, 1, 1, 8, 0, 0)
        
    final_schedule_data = []

    # Helper: Extract day number
    def get_day_num(day_str):
        try:
            return int(day_str.replace('Day ', ''))
        except:
            return 1

    # Helper: Sort key
    def sort_key(item):
        # Sort by Shift (1,2,3) then Hierarchy
        shift_val = item.get('Shift_ID', 99)
        prod = item.get('Product', '')
        if 'level' not in item:
            lev, _ = get_kit_hierarchy_info(prod)
            item['_sort_level'] = lev
        lev_map = {'prepack': 0, 'subkit': 1, 'master': 2, 'unknown': 3}
        lev_val = lev_map.get(item.get('_sort_level', 'unknown'), 3)
        return (shift_val, lev_val)

    # 1. Group by (Line, Day)
    grouped_items = {}
    for item in schedule_data:
        # Filter out zero-activity items (ghost tasks) to prevent phantom padding
        if item.get('Hours', 0) <= 0 and item.get('Units', 0) <= 0:
            continue
            
        # Use tuple key for grouping
        key = (item['Line'], item['Day'])
        if key not in grouped_items:
            grouped_items[key] = []
        grouped_items[key].append(item)
    
    # 2. Process each group as a Queue
    for (line_name, day_str), items in grouped_items.items():
        # Sort to ensure logical order (Shift -> Hierarchy)
        items.sort(key=sort_key)
        
        # Convert to Queue
        task_queue = deque(items)
        
        # Determine actual calendar date for this Day
        day_offset = get_day_num(day_str) - 1
        current_time = base_production_date + datetime.timedelta(days=day_offset)
        
        while task_queue:
            # Pop task
            item = task_queue.popleft()
            
            # Start/End calculation
            duration_hours = item['Hours']
            start_dt = current_time
            end_dt = start_dt + datetime.timedelta(hours=duration_hours)
            
            item['Start_Time'] = start_dt
            item['End_Time'] = end_dt
            
            final_schedule_data.append(item)
            current_time = end_dt
            
            # Insert Padding if queue is not empty (i.e., there is a next task)
            if padding_hours > 0 and task_queue:
                # Create padding item
                padding_item = item.copy()
                padding_item['Product'] = "Time Padding"
                padding_item['Hours'] = padding_hours
                padding_item['Units'] = 0
                padding_item['Kit Total Demand'] = 0
                padding_item['Product Workers'] = 0
                padding_item['Product UNICEF'] = 0
                padding_item['Product Humanizer'] = 0
                padding_item['_sort_level'] = 'padding'
                
                # Set times
                p_start = current_time
                p_end = p_start + datetime.timedelta(hours=padding_hours)
                padding_item['Start_Time'] = p_start
                padding_item['End_Time'] = p_end
                
                final_schedule_data.append(padding_item)
                current_time = p_end

    # If no data
    if not final_schedule_data:
        final_schedule_data = schedule_data

    # --- Add hierarchy information to the list data (before DataFrame creation) ---
    for item in final_schedule_data:
        if item.get('Product') == "Time Padding":
            item['Hierarchy_Level'] = "padding"
            item['Dependencies'] = []
        else:
            hierarchy_level, dependencies = get_kit_hierarchy_info(item.get('Product', ''))
            item['Hierarchy_Level'] = hierarchy_level
            if 'Dependencies' not in item or not isinstance(item.get('Dependencies'), list):
                item['Dependencies'] = dependencies

    df_schedule = pd.DataFrame(final_schedule_data)
    
    if not df_schedule.empty:
        # Timeline view with hierarchy levels
        st.subheader("⏰ Production Line by Line and Day")
        
        # Debug: Show line assignment for prepacks
        prepack_assignments = df_schedule[df_schedule['Hierarchy_Level'] == 'prepack'][['Product', 'Line', 'Line_Type_ID', 'Day']].drop_duplicates()
        if not prepack_assignments.empty:
            with st.expander("🔍 Debug: Prepack Line Assignments", expanded=False):
                st.write("Prepacks should be assigned to **Mini Load** lines (Line_Type_ID = 7):")
                st.dataframe(prepack_assignments)
        
        # Create enhanced timeline chart
        fig = create_enhanced_timeline_with_relationships(df_schedule)
        
        if fig:
            st.plotly_chart(fig, use_container_width=True, key="enhanced_timeline")
        else:
            st.warning("Could not create enhanced timeline chart")
            
        # Add hierarchy legend (updated to match fixed system)
        st.markdown("""
        **🎨 Hierarchy Level Colors:**
        - 🟢 **Prepack**: Level 0 - Dependencies produced first (Lime Green)
        - 🔵 **Subkit**: Level 1 - Intermediate assemblies (Royal Blue)
        - 🟠 **Master**: Level 2 - Final products (Dark Orange)
        - ⚪ **Padding**: Buffer time between tasks (Light Gray)
        """)
        
        # Line employee allocation from cost breakdown
        st.subheader("👥 Line Employee Allocation (Cost Breakdown)")
        
        # if 'results' in results:
            # and 'cost_breakdown' in results['results']
        detailed_costs = results.get('cost_breakdown', {}).get('detailed_costs', [])
        if detailed_costs:
            cost_df = pd.DataFrame(detailed_costs)
            st.dataframe(cost_df, use_container_width=True)
        #     else:
        #         st.info("No cost breakdown data available")
        # else:
        #     st.info("Cost breakdown not found - please re-run optimization")
        
        # Detailed schedule table (filtered to show only meaningful rows)
        st.subheader("📋 Detailed Production Schedule")
        
        # Filter out rows with zero hours AND zero units (not useful)
        df_schedule_filtered = df_schedule[
            (df_schedule['Hours'] > 0) | (df_schedule['Units'] > 0)
        ].copy()
        
        if df_schedule_filtered.empty:
            st.warning("No production activity scheduled (all hours and units are zero)")
        else:
            # Show count of filtered vs total rows
            filtered_count = len(df_schedule_filtered)
            total_count = len(df_schedule)
            if filtered_count < total_count:
                st.info(f"Showing {filtered_count} active production entries (filtered out {total_count - filtered_count} zero-activity rows)")
            
            st.dataframe(df_schedule_filtered, use_container_width=True)

def create_enhanced_timeline_with_relationships(df_schedule):
    """Create enhanced timeline chart with hierarchy colors and relationship lines"""
    if df_schedule.empty:
        return None
    
    # Define hierarchy colors (using proper hierarchy levels with visible colors)
    hierarchy_colors = {
        'prepack': '#32CD32',         # Lime Green - Level 0 (dependencies)
        'subkit': '#4169E1',          # Royal Blue - Level 1 (intermediate)
        'master': '#FF8C00',          # Dark Orange - Level 2 (final products)
        'padding': '#D3D3D3',         # Light Gray - Time Padding
        'unknown': '#8B0000'          # Dark Red - fallback (should not appear now)
    }
    
    # Create the base chart using hierarchy levels for colors
    # Include both product-level and line-level worker information
    hover_data_dict = {
        'Product': True,
        'Units': True,
        'Hierarchy_Level': False  # Don't show twice
    }
    
    # Add line-level worker info if available
    if 'Line Total Workers' in df_schedule.columns:
        hover_data_dict['Line UNICEF'] = True
        hover_data_dict['Line Humanizer'] = True
        hover_data_dict['Line Total Workers'] = True
    
    # Add product-level worker info if available
    if 'Product Workers' in df_schedule.columns:
        hover_data_dict['Product UNICEF'] = True
        hover_data_dict['Product Humanizer'] = True
    
    fig = px.timeline(df_schedule, 
                x_start='Start_Time', 
                x_end='End_Time', 
                y='Line', 
                color='Hierarchy_Level',
                facet_col='Day', 
                # orientation='h', # implicit in timeline
                title='Production Schedule by Line and Day (with Time Padding)',
                height=500,
                color_discrete_map=hierarchy_colors,
                hover_data=hover_data_dict)
    
    # Improve visibility with stronger borders and opacity
    fig.update_traces(
        marker_line_color='black',  # Add black borders
        marker_line_width=1.0,      # Make borders visible
        opacity=0.9                 # Slightly transparent but not too much
    )
    
    # Improve layout with better text visibility
    fig.update_layout(
        showlegend=True,
        plot_bgcolor='white',       # White background
        paper_bgcolor='white',
        font=dict(size=12, color='#000000', family='Arial, sans-serif'),  # Black text, clear font
        title_font=dict(color='#000000', size=14, family='Arial Bold'),      # Bold black title
        legend_title_text='Hierarchy Level',
        legend=dict(
            font=dict(size=11, color='#000000'),  # Black legend text
            bgcolor='rgba(255,255,255,0.8)',      # Semi-transparent white background
            bordercolor='#000000',                # Black border around legend
            borderwidth=1
        ),
        xaxis=dict(
            tickformat="%H:%M", # Show hours only
        )
    )
    
    # Allow independent x-axes for facets (important for Real Dates across different days)
    fig.update_xaxes(matches=None)
    
    # Improve axes with dark, bold text
    fig.update_xaxes(
        showgrid=True, 
        gridwidth=0.5, 
        gridcolor='lightgray',
        title_font=dict(size=12, color='#000000'),
        tickfont=dict(color='#000000', size=10)
    )
    fig.update_yaxes(
        showgrid=True, 
        gridwidth=0.5, 
        gridcolor='lightgray',
        title_font=dict(size=12, color='#000000'),
        tickfont=dict(color='#000000', size=10)
    )
    
    # Add dependency arrows/lines between related kits
    try:
        fig = add_dependency_connections(fig, df_schedule)
    except Exception as e:
        print(f"Could not add dependency connections: {e}")
    
    return fig

def add_dependency_connections(fig, df_schedule):
    """Add arrows or lines showing dependencies between kits"""
    # Create a mapping of product to its position in the chart
    product_positions = {}
    
    def extract_day_number(day_str):
        """Extract day number from 'Day X' string format"""
        if isinstance(day_str, str) and day_str.startswith('Day '):
            try:
                return int(day_str.replace('Day ', ''))
            except ValueError:
                return 0
        elif isinstance(day_str, (int, float)):
            return int(day_str)
        return 0
    
    def is_later_timing(day1, shift_id1, day2, shift_id2):
        """Check if (day1, shift_id1) is later than (day2, shift_id2)"""
        day1_num = extract_day_number(day1)
        day2_num = extract_day_number(day2)
        if day1_num > day2_num:
            return True
        elif day1_num < day2_num:
            return False
        else:
            # Same day: compare shift order (larger shift ID = later)
            return shift_id1 > shift_id2
    
    for _, row in df_schedule.iterrows():
        product = row['Product']
        day = row['Day']
        line = row['Line']
        shift_id = row.get('Shift_ID', 1)  # Default to 1 (Regular) if not found
        
        # Store latest production timing for each product
        # If product appears multiple times, keep the latest one
        # This is important: dependency must be produced before the LAST production of the product
        if product not in product_positions:
            product_positions[product] = {
                'day': day,
                'line': line,
                'shift_id': shift_id,
                'dependencies': row.get('Dependencies', [])
            }
        else:
            # Update if this is a later production time
            if is_later_timing(day, shift_id, 
                               product_positions[product]['day'], 
                               product_positions[product]['shift_id']):
                product_positions[product]['day'] = day
                product_positions[product]['line'] = line
                product_positions[product]['shift_id'] = shift_id
                # Dependencies should be consistent, but keep from first occurrence
                if not product_positions[product].get('dependencies'):
                    product_positions[product]['dependencies'] = row.get('Dependencies', [])
    
    # Count relationships for display
    relationship_count = 0
    dependency_details = []
    
    def compare_timing(dep_day, dep_shift_id, product_day, product_shift_id):
        """
        Compare timing: returns True if dependency is produced before or same time as product
        Shift order: Regular (1) < Evening (2) < Overtime (3)
        """
        dep_day_num = extract_day_number(dep_day)
        product_day_num = extract_day_number(product_day)
        
        # First compare days
        if dep_day_num < product_day_num:
            return True  # Dependency is earlier day
        elif dep_day_num > product_day_num:
            return False  # Dependency is later day
        else:
            # Same day: compare shift order (smaller shift ID = earlier)
            return dep_shift_id <= product_shift_id
    
    for product, pos_info in product_positions.items():
        dependencies = pos_info['dependencies']
        
        for dep in dependencies:
            if dep in product_positions:
                # Both product and dependency are in production
                dep_pos = product_positions[dep]
                relationship_count += 1
                
                # Compare timing considering both day and shift order
                is_correct = compare_timing(
                    dep_pos['day'], dep_pos['shift_id'],
                    pos_info['day'], pos_info['shift_id']
                )
                
                dependency_details.append({
                    'product': product,
                    'dependency': dep,
                    'product_day': pos_info['day'],
                    'dependency_day': dep_pos['day'],
                    'product_shift': pos_info.get('shift_id', 1),
                    'dependency_shift': dep_pos.get('shift_id', 1),
                    'timing': 'correct' if is_correct else 'violation'
                })
    
    # Add annotations about relationships
    if relationship_count > 0:
        violations = len([d for d in dependency_details if d['timing'] == 'violation'])
        
        fig.add_annotation(
            text=f"🔗 {relationship_count} dependencies | {'⚠️ ' + str(violations) + ' violations' if violations > 0 else '✅ All correct'}",
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            showarrow=False,
            font=dict(size=10, color="purple"),
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="purple",
            borderwidth=1
        )
        
        # Add dependency info box
        if dependency_details:
            dependency_text = "\\n".join([
                f"• {d['dependency']} → {d['product']} ({'✅' if d['timing'] == 'correct' else '⚠️'})"
                for d in dependency_details[:5]  # Show first 5
            ])
            
            if len(dependency_details) > 5:
                dependency_text += f"\\n... and {len(dependency_details) - 5} more"
                
            fig.add_annotation(
                text=dependency_text,
                xref="paper", yref="paper",
                x=0.02, y=0.02,
                showarrow=False,
                font=dict(size=8, color="navy"),
                bgcolor="rgba(240,248,255,0.9)",
                bordercolor="navy",
                borderwidth=1,
                align="left"
            )
    
    return fig

def display_kit_production(results):
    """Display kit production details"""
    # Convert to compatible format if needed
    results = get_compatible_results(results)
    
    st.subheader("📦 Kit Production Analysis")
    
    # Load product name mapping from COOIS Planned Prod Orders CSV
    product_name_map = {}
    try:
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        coois_path = os.path.join(project_root, "data/real_data_excel/production_data/COOIS_Planned_and_Released.csv")
        coois_df = pd.read_csv(coois_path)
        # Create mapping from Material Number to Material description (drop duplicates)
        product_name_map = dict(zip(coois_df['Material Number'], coois_df['Material description']))
    except Exception as e:
        st.warning(f"Could not load product names: {e}")
    
    # Weekly production summary
    production_data = []
    from src.config.optimization_config import get_demand_dictionary
    DEMAND_DICTIONARY = get_demand_dictionary()
    
    for product, production in results['weekly_production'].items():
        demand = DEMAND_DICTIONARY.get(product, 0)
        production_data.append({
            'Product': product,
            'Product Name': product_name_map.get(product, 'N/A'),
            'Production': production,
            'Demand': demand,
            'Fulfillment %': (production / demand * 100) if demand > 0 else 0,
            'Over/Under': production - demand
        })
    
    df_production = pd.DataFrame(production_data)
    
    if not df_production.empty:
        # Fulfillment rate chart
        fig = px.bar(df_production, x='Product', y='Fulfillment %',
                    title='Kit Fulfillment Rate by Product',
                    color='Fulfillment %',
                    color_continuous_scale=['red', 'yellow', 'green'],
                    height=400)
        fig.add_hline(y=100, line_dash="dash", line_color="black", 
                     annotation_text="100% Target")
        st.plotly_chart(fig, use_container_width=True, key="fulfillment_rate")
        
        # Production summary table
        st.subheader("📋 Kit Production Summary")
        st.dataframe(df_production, use_container_width=True)

def display_cost_analysis(results):
    """Display cost breakdown and analysis"""
    # Convert to compatible format if needed
    results = get_compatible_results(results)
    
    st.subheader("💰 Cost Breakdown Analysis")
    
    # Use pre-calculated cost breakdown from JSON (if available)
    # Otherwise fall back to calculating it (for backward compatibility)
    if 'results' in results and 'cost_breakdown' in results['results']:
        # New format: use pre-calculated data
        cost_breakdown = results['results']['cost_breakdown']
        total_cost_by_type = cost_breakdown['by_employee_type']
        
        # Convert detailed costs to DataFrame format
        cost_data = []
        for detail in cost_breakdown['detailed_costs']:
            payment_indicator = f" ({detail['payment_mode']})" if detail['payment_mode'] == 'bulk' else ""
            
            # Handle both old format (product) and new format (products list)
            if 'products' in detail:
                products_str = ', '.join(detail['products']) if detail['products'] else 'No production'
            else:
                products_str = detail.get('product', 'Unknown')
            
            # cost_data.append({
            #     'Employee Type': detail['employee_type'],
            #     'Day': f"Day {detail['day']}",
            #     'Shift': f"{detail['shift_name']}{payment_indicator}",
            #     'Line': detail['line_name'],
            #     'Product(s)': products_str,
            #     'Actual Hours': round(detail['actual_hours'], 2),
            #     'Paid Hours': round(detail['paid_hours'], 2),
            #     'Max Workers on Line': detail.get('max_employees_on_line', detail.get('workers', 0)),
            #     'Hourly Rate': f"€{detail['hourly_rate']:.2f}",
            #     'Cost': round(detail['cost'], 2)
            # })
    else:
        # Fallback: calculate from run_schedule (backward compatibility)
        st.warning("⚠️ Cost breakdown not found in results - calculating from schedule (consider re-running optimization)")
        
        from src.config.optimization_config import get_cost_list_per_emp_shift, get_team_requirements, shift_code_to_name, line_code_to_name
        from src.config.optimization_config import get_payment_mode_config, get_max_hour_per_shift_per_person
        
        COST_LIST_PER_EMP_SHIFT = get_cost_list_per_emp_shift()
        TEAM_REQ_PER_PRODUCT = get_team_requirements()
        PAYMENT_MODE_CONFIG = get_payment_mode_config()
        MAX_HOUR_PER_SHIFT_PER_PERSON = get_max_hour_per_shift_per_person()
        shift_names = shift_code_to_name()
        line_names = line_code_to_name()
        
        # cost_data = []
        # total_cost_by_type = {}
        
        # for row in results['run_schedule']:
        #     product = row['product']
        #     hours = row['run_hours']
        #     shift = row['shift']
        #     shift_name = shift_names.get(shift, f"Shift {shift}")
        #     line_name = line_names.get(row['line_type_id'], f"Line {row['line_type_id']}")
            
        #     for emp_type in ['UNICEF Fixed term', 'Humanizer']:
        #         workers_needed = TEAM_REQ_PER_PRODUCT.get(emp_type, {}).get(product, 0)
        #         hourly_rate = COST_LIST_PER_EMP_SHIFT.get(emp_type, {}).get(shift, 0)
        #         payment_mode = PAYMENT_MODE_CONFIG.get(shift, "partial")
                
        #         if payment_mode == "bulk" and hours > 0:
        #             shift_hours = MAX_HOUR_PER_SHIFT_PER_PERSON.get(shift, hours)
        #             cost = workers_needed * shift_hours * hourly_rate
        #             display_hours = shift_hours
        #         else:
        #             cost = workers_needed * hours * hourly_rate
        #             display_hours = hours
                
                
                
        #         if cost > 0:
        #             payment_indicator = f" ({payment_mode})" if payment_mode == "bulk" else ""
        #             cost_data.append({
        #                 'Employee Type': emp_type,
        #                 'Day': f"Day {row['day']}",
        #                 'Shift': f"{shift_name}{payment_indicator}",
        #                 'Line': f"{line_name} {row['line_idx']}",
        #                 'Product(s)': product,
        #                 'Actual Hours': round(hours, 2),
        #                 'Paid Hours': round(display_hours, 2),
        #                 'Max Workers on Line': workers_needed,
        #                 'Hourly Rate': f"€{hourly_rate:.2f}",
        #                 'Cost': round(cost, 2)
        #             })
    
    # Total cost metrics
    total_cost = results['objective']
    col1, col2, col3, col4 = st.columns(4)
    detailed_costs = results.get('cost_breakdown', {}).get('detailed_costs', [])
    cost_df = pd.DataFrame(detailed_costs)
    with col1:
        st.metric("Total Cost", f"€{total_cost:,.2f}")
    
    with col2:
        unicef_cost = cost_df[cost_df['employee_type'] == 'UNICEF Fixed term']['cost'].sum()
        st.metric("UNICEF Cost", f"€{unicef_cost:,.2f}")
    
    with col3:
        humanizer_cost = cost_df[cost_df['employee_type'] == 'Humanizer']['cost'].sum()
        st.metric("Humanizer Cost", f"€{humanizer_cost:,.2f}")
    
    with col4:
        avg_daily_cost = total_cost / len(set(row['day'] for row in results['run_schedule'])) if results['run_schedule'] else 0
        st.metric("Avg Daily Cost", f"€{avg_daily_cost:,.2f}")
    
    # Cost breakdown pie chart
    if not cost_df.empty:
        fig = px.pie(values=cost_df['cost'].values, 
                    names=cost_df['employee_type'].values,
                    title='Cost Distribution by Employee Type')
        st.plotly_chart(fig, use_container_width=True, key="cost_distribution_pie")
    
    # Detailed cost table
    if not cost_df.empty:
        
        # Add total row
        total_cost = cost_df['cost'].sum()
        total_paid_hours = cost_df['paid_hours'].sum()
        
        # Get the correct column name for workers (support both old and new format)
        workers_col = 'max_employees_on_line'
        product_col = 'products'
        
        
        
        # Combine original data with total row
        # cost_df_with_total = pd.concat([cost_df, total_row], ignore_index=True)
        
        # st.subheader("📋 Detailed Cost Breakdown")
        st.dataframe(cost_df, use_container_width=True)


def display_input_data_inspection():
    """
    Display comprehensive input data inspection showing what was fed into the optimizer
    """
    st.subheader("🔍 Input Data Inspection")
    st.markdown("This section shows all the input data and parameters that were fed into the optimization model.")
    
    # Import the optimization config to get current values
    try:
        from src.config import optimization_config
        from src.config.constants import ShiftType, LineType, KitLevel
        
        # Create expandable sections for different data categories
        with st.expander("📅 **Schedule & Time Parameters**", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Date Range:**")
                # Get date configuration from SINGLE SOURCE OF TRUTH
                from src.config.optimization_config import get_date_configuration
                _, _, _, planning_days, date_span = get_date_configuration()
                st.write(f"• Planning Period: {len(date_span)} days")
                st.write(f"• Date Span: {date_span}")
                
                st.write("**Shift Configuration:**")
                shift_list = optimization_config.get_shift_list()
                for shift in shift_list:
                    shift_name = ShiftType.get_name(shift)
                    st.write(f"• {shift_name} (ID: {shift})")
            
            with col2:
                st.write("**Work Hours Configuration:**")
                max_hours_shift = optimization_config.get_max_hour_per_shift_per_person()
                for shift_id, hours in max_hours_shift.items():
                    shift_name = ShiftType.get_name(shift_id)
                    st.write(f"• {shift_name}: {hours} hours/shift")
                
                from src.config.optimization_config import MAX_HOUR_PER_PERSON_PER_DAY
                max_daily_hours = MAX_HOUR_PER_PERSON_PER_DAY
                st.write(f"• Maximum daily hours per person: {max_daily_hours}")
        
        with st.expander("👥 **Workforce Parameters**", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Employee Types:**")
                from src.config.constants import DefaultConfig
                emp_types = DefaultConfig.EMPLOYEE_TYPE_LIST
                for emp_type in emp_types:
                    st.write(f"• {emp_type}")
                
                st.write("**Daily Workforce Capacity:**")
                max_emp_per_day = optimization_config.get_max_employee_per_type_on_day()
                for emp_type, daily_caps in max_emp_per_day.items():
                    st.write(f"**{emp_type}:**")
                    for day, count in daily_caps.items():
                        st.write(f"  - Day {day}: {count} employees")
            
            with col2:
                st.write("**Team Requirements per Product:**")
                team_req = optimization_config.get_team_requirements()
                st.write("*Sample products:*")
                # Show first few products as examples
                sample_products = list(team_req.get('UNICEF Fixed term', {}).keys())[:5]
                for product in sample_products:
                    st.write(f"**{product}:**")
                    for emp_type in emp_types:
                        req = team_req.get(emp_type, {}).get(product, 0)
                        if req > 0:
                            st.write(f"  - {emp_type}: {req}")
                
                if len(team_req.get('UNICEF Fixed term', {})) > 5:
                    remaining = len(team_req.get('UNICEF Fixed term', {})) - 5
                    st.write(f"... and {remaining} more products")
        
        with st.expander("🏭 **Production & Line Parameters**", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Line Configuration:**")
                from src.config.optimization_config import get_line_list, get_line_cnt_per_type
                line_list = get_line_list()
                line_cnt = get_line_cnt_per_type()
                
                for line_type in line_list:
                    line_name = LineType.get_name(line_type)
                    count = line_cnt.get(line_type, 0)
                    st.write(f"• {line_name} (ID: {line_type}): {count} lines")
                
                st.write("**Maximum Workers per Line:**")
                max_workers = optimization_config.get_max_parallel_workers()
                for line_type, max_count in max_workers.items():
                    line_name = LineType.get_name(line_type)
                    st.write(f"• {line_name}: {max_count} workers max")
            
            with col2:
                st.write("**Product-Line Matching:**")
                from src.config.optimization_config import KIT_LINE_MATCH_DICT
                kit_line_match = KIT_LINE_MATCH_DICT
                st.write("*Sample mappings:*")
                sample_items = list(kit_line_match.items())[:10]
                for product, line_type in sample_items:
                    line_name = LineType.get_name(line_type)
                    st.write(f"• {product}: {line_name}")
                
                if len(kit_line_match) > 10:
                    remaining = len(kit_line_match) - 10
                    st.write(f"... and {remaining} more product mappings")
        
        with st.expander("📦 **Product & Demand Data**", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Product List:**")
                product_list = optimization_config.get_product_list()
                st.write(f"• Total products: {len(product_list)}")
                st.write("*Sample products:*")
                for product in product_list[:10]:
                    st.write(f"  - {product}")
                if len(product_list) > 10:
                    st.write(f"  ... and {len(product_list) - 10} more")
                
                st.write("**Production Speed (units/hour):**")
                from src.preprocess import extract
                speed_data = extract.read_package_speed_data()
                st.write("*Sample speeds:*")
                sample_speeds = list(speed_data.items())[:5]
                for product, speed in sample_speeds:
                    st.write(f"• {product}: {speed:.1f} units/hour")
                if len(speed_data) > 5:
                    remaining = len(speed_data) - 5
                    st.write(f"... and {remaining} more products")
            
            with col2:
                st.write("**Weekly Demand:**")
                demand_dict = optimization_config.get_demand_dictionary()
                st.write(f"• Total products with demand: {len(demand_dict)}")
                
                # Calculate total demand
                total_demand = sum(demand_dict.values())
                st.write(f"• Total weekly demand: {total_demand:,.0f} units")
                
                st.write("*Sample demands:*")
                # Sort by demand to show highest first
                sorted_demands = sorted(demand_dict.items(), key=lambda x: x[1], reverse=True)[:10]
                for product, demand in sorted_demands:
                    st.write(f"• {product}: {demand:,.0f} units")
                
                if len(demand_dict) > 10:
                    remaining = len(demand_dict) - 10
                    st.write(f"... and {remaining} more products")
        
        with st.expander("🏗️ **Kit Hierarchy & Dependencies**", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Kit Levels:**")
                kit_levels = optimization_config.get_kit_levels()
                
                # Count by level
                level_counts = {}
                for kit, level in kit_levels.items():
                    level_name = KitLevel.get_name(level)
                    if level_name not in level_counts:
                        level_counts[level_name] = 0
                    level_counts[level_name] += 1
                
                for level_name, count in level_counts.items():
                    st.write(f"• {level_name}: {count} kits")
                
                st.write("*Sample kit levels:*")
                sample_levels = list(kit_levels.items())[:10]
                for kit, level in sample_levels:
                    level_name = KitLevel.get_name(level)
                    st.write(f"  - {kit}: {level_name}")
                
                if len(kit_levels) > 10:
                    remaining = len(kit_levels) - 10
                    st.write(f"  ... and {remaining} more kits")
            
            with col2:
                st.write("**Dependencies:**")
                kit_deps = optimization_config.get_kit_dependencies()
                
                # Count dependencies
                total_deps = sum(len(deps) for deps in kit_deps.values())
                kits_with_deps = len([k for k, deps in kit_deps.items() if deps])
                
                st.write(f"• Total dependency relationships: {total_deps}")
                st.write(f"• Kits with dependencies: {kits_with_deps}")
                
                st.write("*Sample dependencies:*")
                sample_deps = [(k, deps) for k, deps in kit_deps.items() if deps][:5]
                for kit, deps in sample_deps:
                    st.write(f"• {kit}:")
                    for dep in deps[:3]:  # Show max 3 deps per kit
                        st.write(f"  - depends on: {dep}")
                    if len(deps) > 3:
                        st.write(f"  - ... and {len(deps) - 3} more")
                
                if len(sample_deps) > 5:
                    remaining = len([k for k, deps in kit_deps.items() if deps]) - 5
                    st.write(f"... and {remaining} more kits with dependencies")
        
        with st.expander("💰 **Cost & Payment Configuration**", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Hourly Cost Rates:**")
                cost_rates = optimization_config.get_cost_list_per_emp_shift()
                
                for emp_type, shift_costs in cost_rates.items():
                    st.write(f"**{emp_type}:**")
                    for shift_id, cost in shift_costs.items():
                        shift_name = ShiftType.get_name(shift_id)
                        st.write(f"  - {shift_name}: €{cost:.2f}/hour")
            
            with col2:
                st.write("**Payment Mode Configuration:**")
                payment_config = optimization_config.get_payment_mode_config()
                
                payment_descriptions = {
                    'bulk': 'Full shift payment (even for partial hours)',
                    'partial': 'Pay only for actual hours worked'
                }
                
                for shift_id, mode in payment_config.items():
                    shift_name = ShiftType.get_name(shift_id)
                    description = payment_descriptions.get(mode, mode)
                    st.write(f"• **{shift_name}:** {mode.title()}")
                    st.caption(f"  {description}")
        
        with st.expander("⚙️ **Additional Configuration**", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Schedule Mode:**")
                schedule_mode = "weekly"  # Fixed to weekly only
                st.write(f"• Planning mode: {schedule_mode}")
            
            with col2:
                st.write("**Fixed Staffing:**")
                fixed_min_unicef = optimization_config.get_fixed_min_unicef_per_day()
                st.write(f"• Minimum UNICEF staff per day: {fixed_min_unicef}")
                
                st.write("**Data Sources:**")
                st.write("• Kit hierarchy: kit_hierarchy.json")
                st.write("• Production orders: CSV files")
                st.write("• Personnel data: WH_Workforce CSV")
                st.write("• Speed data: Kits_Calculation CSV")
        
    except Exception as e:
        st.error(f"❌ Error loading input data inspection: {str(e)}")
        st.info("💡 This may happen if the optimization configuration is not properly loaded. Please check the Settings page first.")
    
    # Add refresh button
    st.markdown("---")
    if st.button("🔄 Refresh Input Data", help="Reload the current configuration data"):
        st.rerun()


def display_demand_validation_tab():
    """
    Display demand validation in the optimization results tab
    """
    try:
        from src.demand_validation_viz import display_demand_validation
        display_demand_validation()
    except ImportError as e:
        st.error(f"❌ Error loading demand validation module: {str(e)}")
        st.info("💡 Please ensure the demand validation module is properly installed.")
    except Exception as e:
        st.error(f"❌ Error in demand validation: {str(e)}")
        st.info("💡 Please check the data files and configuration.")