"""
Hierarchy-Based Production Flow Visualization
Shows how kits flow through production based on dependency hierarchy
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None

import numpy as np
import sys

from src.config.optimization_config import (
    KIT_LEVELS, KIT_DEPENDENCIES, TEAM_REQ_PER_PRODUCT, 
    shift_code_to_name, line_code_to_name
)
from src.config.constants import ShiftType, LineType, KitLevel

# Import kit relationships dashboard
try:
    from src.visualization.kit_relationships import display_kit_relationships_dashboard
except ImportError:
    display_kit_relationships_dashboard = None

def display_hierarchy_operations_dashboard(results):
    """Enhanced operations dashboard showing hierarchy-based production flow"""
    st.header("🏭 Hierarchy-Based Operations Dashboard")
    st.markdown("---")
    
    # Create main dashboard tabs
    tab1, tab2, tab3 = st.tabs([
        "🔄 Production Flow", 
        "📊 Hierarchy Analytics", 
        "🔗 Kit Relationships"
    ])
    
    with tab1:
        display_production_flow_visualization(results)
    
    with tab2:
        display_hierarchy_analytics(results)
    
    with tab3:
        # Kit relationships from actual hierarchy data
        if display_kit_relationships_dashboard:
            display_kit_relationships_dashboard(results)
        else:
            st.error("Kit relationships dashboard not available. Please check installation.")

def display_production_flow_visualization(results):
    """Show how products flow through production lines by hierarchy"""
    st.subheader("🔄 Kit Production Flow by Hierarchy")
    
    # Get production sequence data
    flow_data = prepare_hierarchy_flow_data(results)
    
    if not flow_data:
        st.warning("No production data available for flow visualization")
        return
    
    # Create flow diagram
    
    

    # Hierarchy level summary - horizontal layout
    st.subheader("📦 Production by Level")
    level_summary = get_hierarchy_level_summary(flow_data)
    
    # Create horizontal columns for each level
    level_names = ['prepack', 'subkit', 'master']
    available_levels = [level for level in level_names if level in level_summary]
    
    if available_levels:
        cols = st.columns(len(available_levels))
        
        for i, level_name in enumerate(available_levels):
            data = level_summary[level_name]
            with cols[i]:
                # Use custom styling instead of st.metric to avoid delta arrows
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #f0f8ff, #e6f3ff);
                    padding: 1rem;
                    border-radius: 0.5rem;
                    text-align: center;
                    border-left: 4px solid {'#90EE90' if level_name == 'prepack' else '#FFD700' if level_name == 'subkit' else '#FF6347'};
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    <div style="font-size: 0.8rem; color: #666; text-transform: uppercase; letter-spacing: 1px;">
                        {level_name.title()} Kits
                    </div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #333; margin: 0.2rem 0;">
                        {data['count']} products
                    </div>
                    <div style="font-size: 1rem; color: #555;">
                        {data['total_units']:,.0f} units
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Timeline view of hierarchy production
    st.subheader("📅 Hierarchy Production Timeline")
    try:
        fig_timeline = create_hierarchy_timeline(flow_data)
        st.plotly_chart(fig_timeline, use_container_width=True)
    except Exception as e:
        st.warning(f"Timeline chart temporarily unavailable. Showing alternative visualization.")
        # Fallback: Simple bar chart by day
        if flow_data:
            df_simple = pd.DataFrame([{
                'Day': f"Day {row['day']}",
                'Level': row['level_name'].title(),
                'Units': row['units'],
                'Product': row['product']
            } for row in flow_data])
            
            fig_simple = px.bar(df_simple, x='Day', y='Units', color='Level',
                               title='Production Volume by Day and Hierarchy Level',
                               color_discrete_map={
                                   'Prepack': '#90EE90',
                                   'Subkit': '#FFD700', 
                                   'Master': '#FF6347'
                               })
            st.plotly_chart(fig_simple, use_container_width=True)

def display_hierarchy_analytics(results):
    """Deep dive analytics on hierarchy production performance"""
    st.subheader("📊 Hierarchy Performance Analytics")
    
    # Prepare analytics data
    analytics_data = prepare_hierarchy_analytics_data(results)
    
    if not analytics_data:
        st.warning("No hierarchy data available for analytics")
        return
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        prepack_efficiency = analytics_data.get('prepack_efficiency', 0)
        st.metric("Prepack Efficiency", f"{prepack_efficiency:.1f}%", 
                 delta=f"{prepack_efficiency-95:.1f}%" if prepack_efficiency != 95 else None)
    
    with col2:
        dependency_violations = analytics_data.get('dependency_violations', 0)
        st.metric("Dependency Violations", f"{dependency_violations}", 
                 delta=f"-{dependency_violations}" if dependency_violations > 0 else None)
    
    with col3:
        avg_lead_time = analytics_data.get('avg_lead_time', 0)
        st.metric("Avg Lead Time", f"{avg_lead_time:.1f} days")
    
    with col4:
        hierarchy_cost_efficiency = analytics_data.get('cost_efficiency', 0)
        st.metric("Cost Efficiency", f"﹩{hierarchy_cost_efficiency:.2f}/unit")
    
    # Dependency flow chart
    st.subheader("🔗 Dependency Network Analysis")
    fig_network = create_dependency_network_chart(analytics_data)
    st.plotly_chart(fig_network, use_container_width=True)
    
    # Production heatmap
    st.subheader("🔥 Hierarchy Production Heatmap")
    heatmap_fig = create_hierarchy_heatmap(results)
    st.plotly_chart(heatmap_fig, use_container_width=True)
    


# Removed display_enhanced_line_utilization function - utilization concept removed

def display_production_sequence_analysis(results):
    """Analyze production sequence and timing"""
    st.subheader("🎯 Production Sequence Analysis")
    
    
    if not sequence_data:
        st.warning("No sequence data available")
        return
    
    # Sequence adherence metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sequence_score = sequence_data.get('sequence_adherence_score', 0)
        st.metric("Sequence Adherence", f"{sequence_score:.1f}%",
                 help="How well production follows optimal hierarchy sequence")
    
    with col2:
        early_productions = sequence_data.get('early_productions', 0)
        st.metric("Early Productions", f"{early_productions}",
                 help="Products produced before their dependencies")
    
    with col3:
        optimal_sequences = sequence_data.get('optimal_sequences', 0)
        st.metric("Optimal Sequences", f"{optimal_sequences}%",
                 help="Percentage of products following optimal sequence")
    
    # Sequence violation chart
    if sequence_data.get('violations'):
        st.subheader("⚠️ Sequence Violations")
        violations_df = pd.DataFrame(sequence_data['violations'])
        
        fig = px.scatter(violations_df, 
                        x='production_day', y='dependency_day', 
                        color='severity', size='impact',
                        hover_data=['product', 'dependency'],
                        title='Production vs Dependency Timing (Violations in Red)',
                        labels={'production_day': 'When Product Was Made',
                               'dependency_day': 'When Dependency Was Made'})
        
        # Add diagonal line (should be above this line)
        max_day = max(violations_df['production_day'].max(), violations_df['dependency_day'].max())
        fig.add_shape(type="line", x0=0, y0=0, x1=max_day, y1=max_day,
                     line=dict(dash="dash", color="gray"),
                     name="Ideal Sequence Line")
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Sequence optimization suggestions
    st.subheader("💡 Optimization Suggestions")
    suggestions = generate_sequence_suggestions(sequence_data)
    for suggestion in suggestions:
        st.info(f"💡 {suggestion}")

# Helper Functions

def prepare_hierarchy_flow_data(results):
    """Prepare data for hierarchy flow visualization"""
    flow_data = []
    
    for row in results['run_schedule']:
        product = row['product']
        level = KIT_LEVELS.get(product, KitLevel.MASTER)
        level_name = KitLevel.get_name(level)
        
        flow_data.append({
            'product': product,
            'level': level,
            'level_name': level_name,
            'day': row['day'],
            'shift': row['shift'],
            'line_type': row['line_type_id'],
            'line_idx': row['line_idx'],
            'hours': row['run_hours'],
            'units': row['units'],
            'dependencies': KIT_DEPENDENCIES.get(product, [])
        })
    
    return flow_data

def create_hierarchy_timeline(flow_data):
    """Create timeline showing hierarchy production sequence"""
    if not flow_data:
        return go.Figure()
    
    # Prepare timeline data with proper datetime conversion
    timeline_data = []
    
    from datetime import datetime, timedelta
    base_date = datetime(2025, 1, 1)  # Base date for timeline
    
    for row in flow_data:
        shift_name = ShiftType.get_name(row['shift'])
        line_name = LineType.get_name(row['line_type'])
        
        # Create start and end times for the production run
        start_date = base_date + timedelta(days=row['day']-1)
        end_date = start_date + timedelta(hours=row['hours'])
        
        timeline_data.append({
            'Product': row['product'],
            'Level': row['level_name'].title(),
            'Start': start_date,
            'End': end_date,
            'Day': f"Day {row['day']}",
            'Shift': shift_name,
            'Line': f"{line_name} {row['line_idx']}",
            'Units': row['units'],
            'Hours': row['hours'],
            'Priority': row['level']  # For sorting
        })
    
    df = pd.DataFrame(timeline_data)
    
    if df.empty:
        return go.Figure()
    
    # Create timeline chart with proper datetime columns
    fig = px.timeline(df, 
                     x_start='Start', x_end='End',
                     y='Line', 
                     color='Level',
                     hover_data=['Product', 'Units', 'Hours', 'Shift', 'Day'],
                     title='Production Timeline by Hierarchy Level',
                     color_discrete_map={
                         'Prepack': '#90EE90',
                         'Subkit': '#FFD700', 
                         'Master': '#FF6347'
                     })
    
    fig.update_layout(
        height=500,
        xaxis_title='Production Timeline',
        yaxis_title='Production Line'
    )
    
    return fig

def prepare_hierarchy_analytics_data(results):
    """Prepare analytics data for hierarchy performance"""
    analytics = {
        'prepack_efficiency': 0,
        'dependency_violations': 0,
        'avg_lead_time': 0,
        'cost_efficiency': 0,
        'violations': [],
        'dependencies': KIT_DEPENDENCIES
    }
    
    # Calculate metrics
    total_cost = results.get('objective', 0)
    total_units = sum(results.get('weekly_production', {}).values())
    
    if total_units > 0:
        analytics['cost_efficiency'] = total_cost / total_units
    
    # Analyze dependency violations
    production_times = {}
    for row in results['run_schedule']:
        product = row['product']
        day = row['day']
        if product not in production_times or day < production_times[product]:
            production_times[product] = day
    
    violations = 0
    violation_details = []
    
    for product, prod_day in production_times.items():
        dependencies = KIT_DEPENDENCIES.get(product, [])
        for dep in dependencies:
            if dep in production_times:
                dep_day = production_times[dep]
                if dep_day > prod_day:  # Dependency produced after product
                    violations += 1
                    violation_details.append({
                        'product': product,
                        'dependency': dep,
                        'production_day': prod_day,
                        'dependency_day': dep_day,
                        'severity': 'high' if dep_day - prod_day > 1 else 'medium',
                        'impact': abs(dep_day - prod_day)
                    })
    
    analytics['dependency_violations'] = violations
    analytics['violations'] = violation_details
    
    return analytics

# Removed calculate_hierarchy_line_utilization and create_utilization_gauge functions
# - utilization concept removed from dashboard

def create_hierarchy_heatmap(results):
    """Create heatmap showing hierarchy production by line and day"""
    # Prepare heatmap data
    heatmap_data = []
    
    for row in results['run_schedule']:
        product = row['product']
        level_name = KitLevel.get_name(KIT_LEVELS.get(product, KitLevel.MASTER))
        line_name = f"{LineType.get_name(row['line_type_id'])} {row['line_idx']}"
        
        heatmap_data.append({
            'Line': line_name,
            'Day': f"Day {row['day']}",
            'Level': level_name,
            'Units': row['units'],
            'Hours': row['run_hours']
        })
    
    if not heatmap_data:
        return go.Figure()
    
    df = pd.DataFrame(heatmap_data)
    
    # Pivot for heatmap
    pivot_df = df.pivot_table(
        values='Units', 
        index='Line', 
        columns='Day', 
        aggfunc='sum', 
        fill_value=0
    )
    
    fig = px.imshow(pivot_df.values, 
                   x=pivot_df.columns, 
                   y=pivot_df.index,
                   color_continuous_scale='Blues',
                   title='Production Volume Heatmap (Units per Day)',
                   labels=dict(x="Day", y="Production Line", color="Units"))
    
    return fig

def create_dependency_network_chart(analytics_data):
    """Create network chart showing dependency relationships"""
    dependencies = analytics_data.get('dependencies', {})
    
    if not dependencies or not NETWORKX_AVAILABLE:
        return go.Figure().add_annotation(
            text="Dependency network visualization requires 'networkx' package. Install with: pip install networkx" if not NETWORKX_AVAILABLE else "No dependency relationships to display",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    # Create network graph
    G = nx.DiGraph()
    
    # Add nodes and edges
    for product, deps in dependencies.items():
        if product and deps:  # Only if product has dependencies
            G.add_node(product)
            for dep in deps:
                if dep:  # Only if dependency exists
                    G.add_node(dep)
                    G.add_edge(dep, product)  # Dependency -> Product
    
    if len(G.nodes()) == 0:
        return go.Figure().add_annotation(
            text="No dependency relationships to display",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    # Calculate layout
    pos = nx.spring_layout(G, k=3, iterations=50)
    
    # Create edge traces
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    edge_trace = go.Scatter(x=edge_x, y=edge_y,
                           line=dict(width=0.5, color='#888'),
                           hoverinfo='none',
                           mode='lines')
    
    # Create node traces
    node_x = []
    node_y = []
    node_text = []
    node_color = []
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
        
        # Color by hierarchy level
        level = KIT_LEVELS.get(node, KitLevel.MASTER)
        if level == KitLevel.PREPACK:
            node_color.append('#90EE90')
        elif level == KitLevel.SUBKIT:
            node_color.append('#FFD700')
        else:
            node_color.append('#FF6347')
    
    node_trace = go.Scatter(x=node_x, y=node_y,
                           mode='markers+text',
                           text=node_text,
                           textposition='middle center',
                           marker=dict(size=20, color=node_color, line=dict(width=2, color='black')),
                           hoverinfo='text',
                           hovertext=node_text)
    
    fig = go.Figure(data=[edge_trace, node_trace],
                   layout=go.Layout(
                       title='Kit Dependency Network',
                       titlefont_size=16,
                       showlegend=False,
                       hovermode='closest',
                       margin=dict(b=20,l=5,r=5,t=40),
                       annotations=[ dict(
                           text="Green=Prepack, Gold=Subkit, Red=Master",
                           showarrow=False,
                           xref="paper", yref="paper",
                           x=0.005, y=-0.002,
                           xanchor='left', yanchor='bottom',
                           font=dict(size=12)
                       )],
                       xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                       yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)))
    
    return fig





def generate_sequence_suggestions(sequence_data):
    """Generate optimization suggestions based on sequence analysis"""
    suggestions = []
    
    adherence = sequence_data.get('sequence_adherence_score', 0)
    violations = sequence_data.get('early_productions', 0)
    
    if adherence < 80:
        suggestions.append(
            "Consider adjusting production sequence to better follow hierarchy dependencies. "
            "Current adherence is below optimal (80%)."
        )
    
    if violations > 0:
        suggestions.append(
            f"Found {violations} dependency violations. Review production scheduling to ensure "
            "prepacks are produced before subkits, and subkits before masters."
        )
    
    if adherence >= 95:
        suggestions.append(
            "Excellent sequence adherence! Production is following optimal hierarchy flow."
        )
    
    if not suggestions:
        suggestions.append("Production sequence analysis complete. No major issues detected.")
    
    return suggestions

def get_hierarchy_level_summary(flow_data):
    """Get summary statistics for each hierarchy level"""
    summary = {}
    
    for level_name in ['prepack', 'subkit', 'master']:
        level_products = [row for row in flow_data if row['level_name'] == level_name]
        
        summary[level_name] = {
            'count': len(set(row['product'] for row in level_products)),
            'total_units': sum(row['units'] for row in level_products),
            'total_hours': sum(row['hours'] for row in level_products)
        }
    
    return summary