import sys
import os
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

# Add parent directory to path to import LaborOptimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from optimization.labor_optimizer import LaborOptimizer


def get_available_dates(data_path):
    """Load the orders data and extract unique dates"""
    try:
        orders_file = os.path.join(data_path, "orders.csv")
        if os.path.exists(orders_file):
            orders_df = pd.read_csv(orders_file)
            if "due_date" in orders_df.columns:
                # Convert to datetime and extract unique dates
                dates = pd.to_datetime(orders_df["due_date"]).dt.date.unique()
                # Sort dates in descending order (most recent first)
                dates = sorted(dates, reverse=True)
                return dates
    except Exception as e:
        st.error(f"Error loading dates: {str(e)}")
    return []


def get_metadata_stats(optimizer, target_date=None):
    """
    Aggregate metadata statistics about employee costs and availability
    
    Args:
        optimizer: LaborOptimizer instance
        target_date: Target date for availability analysis
    
    Returns:
        dict: Dictionary containing various statistics
    """
    try:
        # Employee type costs
        employee_types_df = optimizer.employee_types_df
        costs_data = []
        for _, row in employee_types_df.iterrows():
            costs_data.append({
                'Employee Type': row['type_name'].title(),
                'Usual Cost ($/hr)': f"${row['usual_cost']:.2f}",
                'Overtime Cost ($/hr)': f"${row['overtime_cost']:.2f}",
                'Evening Shift Cost ($/hr)': f"${row['evening_shift_cost']:.2f}",
                'Max Hours': row['max_hours'],
                'Unit Manpower/Hr': row['unit_productivity_per_hour']
            })
        
        # Shift hours information
        shift_hours = optimizer._get_shift_hours()
        shift_data = []
        for shift_type, hours in shift_hours.items():
            shift_data.append({
                'Shift Type': shift_type.replace('_', ' ').title(),
                'Duration (hours)': f"{hours:.1f}"
            })
        
        # Employee availability for target date
        availability_data = []
        if target_date:
            target_date_str = pd.to_datetime(target_date).strftime("%Y-%m-%d")
        else:
            # Use most recent date if no target date specified, but show warning
            target_date_str = pd.to_datetime(optimizer.orders_df["due_date"]).max().strftime("%Y-%m-%d")
            st.warning("⚠️ No target date specified. Using the most recent order date for analysis. Please select a specific target date for accurate availability data.")
        
        availability_target_date = optimizer.employee_availability_df[
            optimizer.employee_availability_df["date"] == target_date_str
        ]
        
        employee_availability = optimizer.employees_df.merge(
            availability_target_date, left_on="id", right_on="employee_id", how="left"
        )
        
        for emp_type in optimizer.employee_types_df["type_name"]:
            emp_type_data = employee_availability[
                employee_availability["type_name"] == emp_type
            ]
            
            if not emp_type_data.empty:
                first_shift_available = emp_type_data["first_shift_available"].sum()
                second_shift_available = emp_type_data["second_shift_available"].sum()
                overtime_available = emp_type_data["overtime_available"].sum()
                total_employees = len(emp_type_data)
            else:
                first_shift_available = second_shift_available = overtime_available = total_employees = 0
            
            availability_data.append({
                'Employee Type': emp_type.title(),
                'Total Employees': total_employees,
                'Usual Time Available': first_shift_available,
                'Evening Shift Available': second_shift_available,
                'Overtime Available': overtime_available
            })
        
        # Overall statistics
        total_employees = len(optimizer.employees_df)
        total_employee_types = len(optimizer.employee_types_df)
        total_orders = len(optimizer.orders_df)
        
        return {
            'costs_data': costs_data,
            'shift_data': shift_data,
            'availability_data': availability_data,
            'overall_stats': {
                'Total Employees': total_employees,
                'Employee Types': total_employee_types,
                'Total Orders': total_orders,
                'Analysis Date': target_date_str,
                'is_default_date': not bool(target_date)
            }
        }
        
    except Exception as e:
        st.error(f"Error generating metadata: {str(e)}")
        return None


def display_metadata_section(metadata):
    """Display metadata in organized sections"""
    if not metadata:
        return
        
    # Make the entire Dataset Overview section collapsible
    # with st.expander("📊 Dataset Overview", expanded=False):
    
    with st.expander("📊 Dataset Overview", expanded=False):
        st.write(f"Data path: {st.session_state.data_path}")
        # Overall statistics
        st.write("Information on the date chosen - not an optimization report") # df, err, func, keras!
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Employees Available", metadata['overall_stats']['Total Employees'])
        with col2:
            st.metric("Employee Types Available", metadata['overall_stats']['Employee Types'])
        with col3:
            st.metric("Total Orders", metadata['overall_stats']['Total Orders'])
        with col4:
            analysis_date = metadata['overall_stats']['Analysis Date']
            if metadata['overall_stats'].get('is_default_date', False):
                st.metric("Analysis Date", f"{analysis_date} ⚠️", help="Using most recent order date - select specific date for accurate analysis")
            else:
                st.metric("Analysis Date", analysis_date)
        
        # Create tabs for different metadata sections
        tab1, tab2, tab3 = st.tabs(["💰 Employee Costs", "🕐 Shift Information", "👥 Availability"])
        
        with tab1:
            st.subheader("Employee Type Costs")
            costs_df = pd.DataFrame(metadata['costs_data'])
            st.dataframe(costs_df, use_container_width=True)
            
            # Cost comparison chart
            costs_for_chart = []
            for item in metadata['costs_data']:
                emp_type = item['Employee Type']
                costs_for_chart.extend([
                    {'Employee Type': emp_type, 'Cost Type': 'Usual', 'Cost': float(item['Usual Cost ($/hr)'].replace('$', ''))},
                    {'Employee Type': emp_type, 'Cost Type': 'Overtime', 'Cost': float(item['Overtime Cost ($/hr)'].replace('$', ''))},
                    {'Employee Type': emp_type, 'Cost Type': 'Evening', 'Cost': float(item['Evening Shift Cost ($/hr)'].replace('$', ''))}
                ])
            
            chart_df = pd.DataFrame(costs_for_chart)
            fig = px.bar(chart_df, x='Employee Type', y='Cost', color='Cost Type',
                        title='Hourly Costs by Employee Type and Shift',
                        barmode='group')
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.subheader("Shift Duration Information")
            shift_df = pd.DataFrame(metadata['shift_data'])
            st.dataframe(shift_df, use_container_width=True)
            
            # Shift duration chart
            fig2 = px.bar(shift_df, x='Shift Type', y='Duration (hours)',
                            title='Shift Duration by Type')
            st.plotly_chart(fig2, use_container_width=True)
        
        with tab3:
            st.subheader("Employee Availability")
            availability_df = pd.DataFrame(metadata['availability_data'])
            st.dataframe(availability_df, use_container_width=True)
            
            # # Availability chart
            # availability_chart_data = []
            # for item in metadata['availability_data']:
            #     emp_type = item['Employee Type']
            #     availability_chart_data.extend([
            #         {'Employee Type': emp_type, 'Shift Type': 'Usual Time', 'Available': item['Usual Time Available']},
            #         {'Employee Type': emp_type, 'Shift Type': 'Evening Shift', 'Available': item['Evening Shift Available']},
            #         {'Employee Type': emp_type, 'Shift Type': 'Overtime', 'Available': item['Overtime Available']}
            #     ])
            
            # chart_df2 = pd.DataFrame(availability_chart_data)
            # fig3 = px.bar(chart_df2, x='Employee Type', y='Available', color='Shift Type',
            #              title='Available Workers by Employee Type and Shift',
            #              barmode='group')
            # st.plotly_chart(fig3, use_container_width=True)
def display_demand(optimizer):
    with st.expander("📊 Demand", expanded=False):
        demand_df = optimizer.orders_df
        st.header("Demand")
        daily_demand = demand_df.groupby('date_of_order').sum()['order_amount'].reset_index()
        st.plotly_chart(px.bar(daily_demand, x='date_of_order', y='order_amount', title='Demand by Date'), use_container_width=True)
        st.markdown("### Demand for the selected date")
        st.dataframe(demand_df[demand_df['date_of_order']==st.session_state.target_date], use_container_width=True)

def display_employee_availability(optimizer):
    with st.expander("👥 Employee Availability", expanded=False):
        st.header("Employee Availability")
        employee_availability_df = optimizer.employee_availability_df
        employee_availability_df['date'] = pd.to_datetime(employee_availability_df['date'])
        employee_availability_target_date = employee_availability_df[employee_availability_df['date']==st.session_state.target_date]
        employee_availability_target_date = pd.merge(employee_availability_target_date, optimizer.employees_df, left_on='employee_id', right_on='id', how='left')
        st.dataframe(employee_availability_target_date[['name', 'employee_id', 'type_name', 'first_shift_available', 'second_shift_available', 'overtime_available']], use_container_width=True)
        # Group by type_name and sum the availability columns
        available_employee_grouped = employee_availability_target_date.groupby('type_name')[
            ['first_shift_available', 'second_shift_available', 'overtime_available']
        ].sum().reset_index()
        
        st.markdown("### Employee Availability for the selected date")
        # Create non-stacked (grouped) bar chart using plotly
        fig = px.bar(
            available_employee_grouped.melt(id_vars=['type_name'], var_name='shift_type', value_name='count'),
            x='type_name',
            y='count', 
            color='shift_type',
            barmode='group',  # This makes it non-stacked
            title='Available Employee Count by Type and Shift',
            labels={'type_name': 'Employee Type', 'count': 'Available Count', 'shift_type': 'Shift Type'}
        )
        st.plotly_chart(fig, use_container_width=True)

    # st.dataframe(employee_availability_target_date, use_container_width=True)
    # st.plotly_chart(px.bar(employee_availability_target_date, x='employee_id', y='availability', title='Employee Availability by Date'), use_container_width=True)
    
    # st.dataframe(employee_availability_df[employee_availability_df['date']==st.session_state.target_date], use_container_width=True)


    
def main():
    """Main function for metadata page"""
    st.set_page_config(page_title="Dataset Metadata", layout="wide")
    st.title("📊 Dataset Metadata Overview")
    
    # Get data_path from session state if available, otherwise create input
    if 'data_path' in st.session_state:
        # Using shared data_path from optimize_viz.py
        data_path = st.session_state.data_path
        
        st.sidebar.info(f"📁 Using shared data path: `{data_path}`")
    else:
        st.error("No data path found. Please select a data path in the sidebar.")
        

    if 'target_date' in st.session_state:
            target_date = st.session_state.target_date
            st.sidebar.info(f"📅 Using shared target date: `{target_date}`")
    else:
        st.error("No target date found. Please select a target date in the sidebar.")
    
    #If the date selection needs to be individualized per page, uncomment the following code
    # with st.sidebar:
    #     # Date selection
    #     available_dates = get_available_dates(data_path)
    #     if available_dates:
    #         date_options = [""] + [str(date) for date in available_dates]
    #         target_date = st.selectbox(
    #             "Target Date (select empty for latest date)",
    #             options=date_options,
    #             index=0,
    #         )
    #     else:
    #         target_date = st.text_input(
    #             "Target Date (YYYY-MM-DD, leave empty for latest)"
    #         )

    try:
        optimizer = LaborOptimizer(data_path)
        
        # Show warning if no target date is selected
        if not target_date:
            st.info("💡 **Tip**: Select a specific target date from the sidebar to see accurate availability data for that date. Currently showing data for the most recent order date.")
        
        metadata = get_metadata_stats(optimizer, target_date if target_date else None)
        display_metadata_section(metadata)
        display_demand(optimizer)
        display_employee_availability(optimizer)
    except Exception as e:
        st.error(f"Error loading metadata: {str(e)}")


if __name__ == "__main__":
    main()
