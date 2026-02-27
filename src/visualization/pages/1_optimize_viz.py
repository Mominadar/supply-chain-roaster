import sys
import os
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

# Add parent directory to path to import LaborOptimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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
    with st.expander("📊 Dataset Overview", expanded=False):
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


def main():
    st.set_page_config(page_title="Labor Optimization Tool", layout="wide")
    st.title("Labor Optimization Visualization Tool")

    # Initialize session state
    if 'data_path' not in st.session_state:
        st.session_state.data_path = "data/my_roster_data"

    # Sidebar for inputs
    with st.sidebar:
        st.header("Optimization Parameters")
        data_path = st.text_input("Data Path", value=st.session_state.data_path)
        # Update session state when user changes data_path
        st.session_state.data_path = data_path

        # Load available dates from the dataset
        available_dates = get_available_dates(data_path)
        

        if available_dates:
            date_options = [""] + [str(date) for date in available_dates]
            target_date = st.selectbox(
                "Target Date (select empty for latest date)",
                options=date_options,
                index=0,
            )
            st.session_state.target_date = target_date
        else:
            target_date = st.text_input(
                "Target Date (YYYY-MM-DD, leave empty for latest)"
            )
            if available_dates == []:
                st.warning("No order dates found in dataset. Check the data path.")

        st.header("Advanced Options")
        st.caption("Set to 0 to use all available workers")
        max_workers_permanent = st.number_input(
            "Max Permanent Workers", min_value=0, value=0
        )
        max_workers_contract = st.number_input(
            "Max Contract Workers", min_value=0, value=0
        )
        max_workers_temporary = st.number_input(
            "Max Temporary Workers", min_value=0, value=0
        )

        # Add button to show metadata
        show_metadata = st.checkbox("Show Dataset Overview", value=True)
        optimize_btn = st.button("Run Optimization")

    # Main area for optimization results
    if optimize_btn:
        try:
            with st.spinner("Running optimization..."):
                optimizer = LaborOptimizer(data_path)

                # Prepare override dict if values are provided
                max_workers_override = {}
                if max_workers_permanent > 0:
                    max_workers_override["permanent"] = max_workers_permanent
                if max_workers_contract > 0:
                    max_workers_override["contract"] = max_workers_contract
                if max_workers_temporary > 0:
                    max_workers_override["temporary"] = max_workers_temporary

                # If no overrides provided, pass None instead of empty dict
                if not max_workers_override:
                    max_workers_override = None

                results = optimizer.optimize(target_date, max_workers_override)

                if isinstance(results, str):
                    st.error(results)
                else:
                    # Wrap optimization results in an expander
                    with st.expander("🎯 Optimization Results", expanded=True):
                        # Split the page into sections
                        summary_col, allocation_col = st.columns([1, 1])

                        with summary_col:
                            st.subheader("Optimization Summary")
                            st.write(f"**Target Date:** {results['target_date']}")
                            st.write(
                                f"**Total Labor Hours:** {results['total_labor_hours_needed']:.2f}"
                            )
                            st.write(f"**Total Cost:** ${results['total_cost']:.2f}")

                        with allocation_col:
                            st.subheader("Employee Allocation")
                            allocation_data = results["allocation"]

                            # Create a DataFrame for easier visualization
                            allocation_df = pd.DataFrame.from_dict(
                                {
                                    emp_type: {
                                        shift: int(val) for shift, val in shifts.items()
                                    }
                                    for emp_type, shifts in allocation_data.items()
                                },
                                orient="index",
                            )
                            allocation_df.index.name = "Employee Type"
                            allocation_df.columns = [
                                col.replace("_", " ").title()
                                for col in allocation_df.columns
                            ]

                            st.dataframe(allocation_df)

                        # Cost visualization
                        st.subheader("Cost Visualization")

                        # Prepare data for visualization
                        cost_data = []
                        for emp_type, shifts in allocation_data.items():
                            shift_hours = results["shift_hours"]
                            costs = optimizer.employee_types_df.set_index("type_name")

                            shift_cost_mapping = {
                                "usual_time": "usual_cost",
                                "overtime": "overtime_cost",
                                "evening_shift": "evening_shift_cost",
                            }

                            for shift in shifts:
                                cost = (
                                    shifts[shift]
                                    * shift_hours[shift]
                                    * costs.loc[emp_type, shift_cost_mapping[shift]]
                                )
                                if cost > 0:  # Only add non-zero costs
                                    cost_data.append(
                                        {
                                            "Employee Type": emp_type.title(),
                                            "Shift": shift.replace("_", " ").title(),
                                            "Cost": cost,
                                            "Workers": int(shifts[shift]),
                                        }
                                    )

                        cost_df = pd.DataFrame(cost_data)

                        col1, col2 = st.columns([3, 2])

                        with col1:
                            # Bar chart for costs
                            if not cost_df.empty:
                                fig = px.bar(
                                    cost_df,
                                    x="Shift",
                                    y="Cost",
                                    color="Employee Type",
                                    title="Labor Cost by Employee Type and Shift",
                                    labels={"Cost": "Cost ($)"},
                                )
                                st.plotly_chart(fig, use_container_width=True)

                        with col2:
                            # Pie chart for total cost by employee type
                            if not cost_df.empty:
                                total_by_type = (
                                    cost_df.groupby("Employee Type")["Cost"]
                                    .sum()
                                    .reset_index()
                                )
                                fig2 = px.pie(
                                    total_by_type,
                                    values="Cost",
                                    names="Employee Type",
                                    title="Total Cost by Employee Type",
                                )
                                st.plotly_chart(fig2, use_container_width=True)

                        # Worker allocation visualization
                        st.subheader("Worker Allocation")
                        worker_data = []
                        for emp_type, shifts in allocation_data.items():
                            for shift, count in shifts.items():
                                if count > 0:  # Only add non-zero allocations
                                    worker_data.append(
                                        {
                                            "Employee Type": emp_type.title(),
                                            "Shift": shift.replace("_", " ").title(),
                                            "Workers": int(count),
                                        }
                                    )

                        worker_df = pd.DataFrame(worker_data)

                        if not worker_df.empty:
                            fig3 = px.bar(
                                worker_df,
                                x="Shift",
                                y="Workers",
                                color="Employee Type",
                                title="Worker Allocation by Shift and Employee Type",
                                barmode="group",
                            )
                            st.plotly_chart(fig3, use_container_width=True)

        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.exception(e)

    # Display metadata section if requested - moved below optimization results
    if show_metadata:
        try:
            optimizer = LaborOptimizer(data_path)
            
            # Show warning if no target date is selected
            if not target_date:
                st.info("💡 **Tip**: Select a specific target date from the sidebar to see accurate availability data for that date. Currently showing data for the most recent order date.")
            
        except Exception as e:
            st.error(f"Error loading metadata: {str(e)}")


if __name__ == "__main__":
    main()
