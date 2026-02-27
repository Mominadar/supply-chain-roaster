"""
Kit Relationship Visualization
Shows the actual dependency relationships between kits in production
based on kit_hierarchy.json data
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import sys

from src.config.constants import ShiftType, LineType, KitLevel

# Optional networkx for advanced network layouts
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None

def load_kit_hierarchy():
    """Load kit hierarchy data from JSON file"""
    try:
        with open('data/hierarchy_exports/kit_hierarchy.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Kit hierarchy file not found. Please ensure kit_hierarchy.json exists in data/hierarchy_exports/")
        return {}
    except json.JSONDecodeError:
        st.error("Invalid kit hierarchy JSON format")
        return {}

def display_kit_relationships_dashboard(results):
    """Main dashboard showing kit relationships in production"""
    st.header("🔗 Kit Relationship Dashboard")
    st.markdown("Visualizing dependencies between kits being produced")
    st.markdown("---")
    
    # Load hierarchy data
    hierarchy_data = load_kit_hierarchy()
    
    if not hierarchy_data:
        st.warning("No kit hierarchy data available")
        return
    
    # Get produced kits from results
    produced_kits = set()
    if 'weekly_production' in results:
        produced_kits = set(results['weekly_production'].keys())
    elif 'run_schedule' in results:
        produced_kits = set(row['product'] for row in results['run_schedule'])
    
    if not produced_kits:
        st.warning("No production data available")
        return
    
    # Create tabs for different relationship views
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌐 Dependency Network", 
        "📊 Relationship Matrix",
        "🎯 Production Flow",
        "⚠️ Dependency Analysis"
    ])
    
    with tab1:
        display_dependency_network(hierarchy_data, produced_kits, results)
    
    with tab2:
        display_relationship_matrix(hierarchy_data, produced_kits, results)
    
    with tab3:
        display_production_flow_relationships(hierarchy_data, produced_kits, results)
    
    with tab4:
        display_dependency_analysis(hierarchy_data, produced_kits, results)

def display_dependency_network(hierarchy_data, produced_kits, results):
    """Show interactive network graph of kit dependencies"""
    st.subheader("🌐 Kit Dependency Network")
    st.markdown("Interactive graph showing which kits depend on other kits")
    
    # Build relationship data for produced kits only
    relationships = build_relationship_data(hierarchy_data, produced_kits)
    
    if not relationships:
        st.info("No dependency relationships found between produced kits")
        return
    
    # Get production timing data
    production_timing = get_production_timing(results)
    
    # Create network visualization
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if NETWORKX_AVAILABLE:
            fig = create_interactive_network_graph(relationships, production_timing)
            st.plotly_chart(fig, use_container_width=True)
        else:
            fig = create_simple_dependency_chart(relationships, production_timing)
            st.plotly_chart(fig, use_container_width=True)
            st.info("💡 Install networkx for advanced network layouts: `pip install networkx`")
    
    with col2:
        # Network statistics
        st.subheader("📈 Network Stats")
        
        all_kits = set()
        for rel in relationships:
            all_kits.add(rel['source'])
            all_kits.add(rel['target'])
        
        st.metric("Total Kits", len(all_kits))
        st.metric("Dependencies", len(relationships))
        
        # Dependency depth analysis
        max_depth = calculate_dependency_depth(relationships)
        st.metric("Max Dependency Depth", max_depth)
        
        # Most dependent kits
        dependent_kits = get_most_dependent_kits(relationships)
        st.subheader("🔗 Most Dependencies")
        for kit, count in dependent_kits[:5]:
            st.write(f"**{kit}**: {count} dependencies")

def display_relationship_matrix(hierarchy_data, produced_kits, results):
    """Show dependency matrix heatmap"""
    st.subheader("📊 Kit Dependency Matrix")
    st.markdown("Heatmap showing which kits (rows) depend on which other kits (columns)")
    
    # Build dependency matrix
    matrix_data = build_dependency_matrix(hierarchy_data, produced_kits)
    
    if matrix_data.empty:
        st.info("No dependency relationships to visualize in matrix form")
        return
    
    # Create heatmap
    fig = px.imshow(matrix_data.values,
                   x=matrix_data.columns,
                   y=matrix_data.index,
                   color_continuous_scale='Blues',
                   title='Kit Dependency Matrix (1 = depends on, 0 = no dependency)',
                   labels=dict(x="Dependency (what is needed)", 
                              y="Kit (what depends on others)", 
                              color="Dependency"))
    
    fig.update_layout(height=600)
    st.plotly_chart(fig, use_container_width=True)
    
    # Show matrix as table
    with st.expander("📋 View Dependency Matrix as Table"):
        st.dataframe(matrix_data, use_container_width=True)

def display_production_flow_relationships(hierarchy_data, produced_kits, results):
    """Show how relationships affect production timing"""
    st.subheader("🎯 Production Flow with Relationships")
    st.markdown("Timeline showing when dependent kits are produced")
    
    # Get production timing and relationships
    production_timing = get_production_timing(results)
    relationships = build_relationship_data(hierarchy_data, produced_kits)
    
    if not production_timing or not relationships:
        st.info("Insufficient data for production flow analysis")
        return
    
    # Create timeline with dependency arrows
    fig = create_production_timeline_with_dependencies(production_timing, relationships)
    st.plotly_chart(fig, use_container_width=True)
    
    # Timing analysis table
    st.subheader("⏰ Dependency Timing Analysis")
    timing_analysis = analyze_dependency_timing(production_timing, relationships)
    
    if timing_analysis:
        df = pd.DataFrame(timing_analysis)
        st.dataframe(df, use_container_width=True)

def display_dependency_analysis(hierarchy_data, produced_kits, results):
    """Analyze dependency fulfillment and violations"""
    st.subheader("⚠️ Dependency Analysis & Violations")
    
    production_timing = get_production_timing(results)
    relationships = build_relationship_data(hierarchy_data, produced_kits)
    
    # Analyze violations
    violations = find_dependency_violations(production_timing, relationships)
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_deps = len(relationships)
        st.metric("Total Dependencies", total_deps)
    
    with col2:
        violated_deps = len(violations)
        st.metric("Violations", violated_deps, 
                 delta=f"-{violated_deps}" if violated_deps > 0 else None)
    
    with col3:
        if total_deps > 0:
            success_rate = ((total_deps - violated_deps) / total_deps) * 100
            st.metric("Success Rate", f"{success_rate:.1f}%")
        else:
            st.metric("Success Rate", "N/A")
    
    with col4:
        if violations:
            avg_violation = sum(v['days_early'] for v in violations) / len(violations)
            st.metric("Avg Days Early", f"{avg_violation:.1f}")
        else:
            st.metric("Avg Days Early", "0")
    
    # Violation details
    if violations:
        st.subheader("🚨 Dependency Violations")
        st.markdown("Cases where kits were produced before their dependencies")
        
        violation_df = pd.DataFrame(violations)
        
        # Violation severity chart
        fig = px.scatter(violation_df,
                        x='dependency_day', y='kit_day',
                        size='days_early', color='severity',
                        hover_data=['kit', 'dependency'],
                        title='Dependency Violations (Below diagonal = violation)',
                        labels={'dependency_day': 'When Dependency Was Made',
                               'kit_day': 'When Kit Was Made'})
        
        # Add diagonal line showing ideal timing
        max_day = max(violation_df['dependency_day'].max(), violation_df['kit_day'].max())
        fig.add_shape(type="line", x0=0, y0=0, x1=max_day, y1=max_day,
                     line=dict(dash="dash", color="green"),
                     name="Ideal Timeline")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed violation table
        st.dataframe(violation_df[['kit', 'dependency', 'kit_day', 'dependency_day', 
                                  'days_early', 'severity']], use_container_width=True)
    else:
        st.success("🎉 No dependency violations found! All kits produced in correct order.")
    
    # Recommendations
    st.subheader("💡 Recommendations")
    recommendations = generate_dependency_recommendations(violations, relationships, production_timing)
    for rec in recommendations:
        st.info(f"💡 {rec}")

# Helper Functions

def build_relationship_data(hierarchy_data, produced_kits):
    """Build relationship data for visualization"""
    relationships = []
    
    for kit_id, kit_info in hierarchy_data.items():
        if kit_id not in produced_kits:
            continue
            
        # Add direct dependencies
        dependencies = kit_info.get('dependencies', [])
        for dep in dependencies:
            if dep in produced_kits:  # Only show relationships between produced kits
                relationships.append({
                    'source': dep,  # Dependency (what's needed)
                    'target': kit_id,  # Kit that depends on it
                    'type': 'direct',
                    'source_type': hierarchy_data.get(dep, {}).get('type', 'unknown'),
                    'target_type': kit_info.get('type', 'unknown')
                })
    
    return relationships

def build_dependency_matrix(hierarchy_data, produced_kits):
    """Build dependency matrix for heatmap"""
    produced_list = sorted(list(produced_kits))
    
    if len(produced_list) == 0:
        return pd.DataFrame()
    
    # Initialize matrix
    matrix = pd.DataFrame(0, index=produced_list, columns=produced_list)
    
    # Fill matrix with dependencies
    for kit_id in produced_list:
        kit_info = hierarchy_data.get(kit_id, {})
        dependencies = kit_info.get('dependencies', [])
        
        for dep in dependencies:
            if dep in produced_list:
                matrix.loc[kit_id, dep] = 1  # kit_id depends on dep
    
    return matrix

def get_production_timing(results):
    """Extract production timing for each kit"""
    timing = {}
    
    if 'run_schedule' in results:
        for run in results['run_schedule']:
            kit = run['product']
            day = run['day']
            
            # Use earliest day if kit is produced multiple times
            if kit not in timing or day < timing[kit]:
                timing[kit] = day
    
    return timing

def create_interactive_network_graph(relationships, production_timing):
    """Create interactive network graph using NetworkX layout"""
    if not NETWORKX_AVAILABLE:
        return create_simple_dependency_chart(relationships, production_timing)
    
    # Create NetworkX graph
    G = nx.DiGraph()
    
    # Add edges (relationships)
    for rel in relationships:
        G.add_edge(rel['source'], rel['target'], type=rel['type'])
    
    if len(G.nodes()) == 0:
        return go.Figure().add_annotation(
            text="No relationships to display",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
        )
    
    # Calculate layout
    pos = nx.spring_layout(G, k=3, iterations=50)
    
    # Create edge traces
    edge_x, edge_y = [], []
    edge_info = []
    
    for edge in G.edges():
        source, target = edge
        x0, y0 = pos[source]
        x1, y1 = pos[target]
        
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        
        # Add arrow annotation
        edge_info.append({
            'x': (x0 + x1) / 2,
            'y': (y0 + y1) / 2, 
            'text': '→',
            'source': source,
            'target': target
        })
    
    edge_trace = go.Scatter(x=edge_x, y=edge_y,
                           line=dict(width=2, color='#888'),
                           hoverinfo='none',
                           mode='lines')
    
    # Create node traces
    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    node_info = []
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        
        # Node size based on number of connections
        in_degree = G.in_degree(node)
        out_degree = G.out_degree(node)
        total_degree = in_degree + out_degree
        node_size.append(20 + total_degree * 5)
        
        # Color by production timing
        prod_day = production_timing.get(node, 0)
        if prod_day == 1:
            node_color.append('#90EE90')  # Light green for early
        elif prod_day <= 3:
            node_color.append('#FFD700')  # Gold for middle
        else:
            node_color.append('#FF6347')  # Tomato for late
        
        # Node text and info
        short_name = node[:12] + "..." if len(node) > 12 else node
        node_text.append(short_name)
        
        node_info.append(f"{node}<br>Day: {prod_day}<br>In: {in_degree}, Out: {out_degree}")
    
    node_trace = go.Scatter(x=node_x, y=node_y,
                           mode='markers+text',
                           text=node_text,
                           textposition='middle center',
                           hovertext=node_info,
                           hoverinfo='text',
                           marker=dict(size=node_size, 
                                     color=node_color,
                                     line=dict(width=2, color='black')))
    
    # Create figure
    fig = go.Figure(data=[edge_trace, node_trace],
                   layout=go.Layout(
                       title='Kit Dependency Network (Size=Connections, Color=Production Day)',
                       showlegend=False,
                       hovermode='closest',
                       margin=dict(b=20,l=5,r=5,t=40),
                       annotations=[
                           dict(text="Green=Early, Gold=Middle, Red=Late production",
                                showarrow=False,
                                xref="paper", yref="paper",
                                x=0.005, y=-0.002,
                                xanchor='left', yanchor='bottom',
                                font=dict(size=12))
                       ],
                       xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                       yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)))
    
    return fig

def create_simple_dependency_chart(relationships, production_timing):
    """Create simple dependency chart without NetworkX"""
    if not relationships:
        return go.Figure().add_annotation(
            text="No dependencies to display", 
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False
        )
    
    # Create a simple directed graph visualization
    # Group kits by their role (sources, targets)
    sources = set(rel['source'] for rel in relationships)
    targets = set(rel['target'] for rel in relationships)
    
    # Create positions
    all_kits = list(sources | targets)
    positions = {kit: (i, production_timing.get(kit, 0)) for i, kit in enumerate(all_kits)}
    
    # Create traces
    edge_x, edge_y = [], []
    for rel in relationships:
        source_pos = positions[rel['source']]
        target_pos = positions[rel['target']]
        
        edge_x.extend([source_pos[0], target_pos[0], None])
        edge_y.extend([source_pos[1], target_pos[1], None])
    
    # Edge trace
    edge_trace = go.Scatter(x=edge_x, y=edge_y,
                           line=dict(width=2, color='#888'),
                           hoverinfo='none',
                           mode='lines')
    
    # Node trace
    node_x = [positions[kit][0] for kit in all_kits]
    node_y = [positions[kit][1] for kit in all_kits]
    node_text = [kit[:10] + "..." if len(kit) > 10 else kit for kit in all_kits]
    
    node_trace = go.Scatter(x=node_x, y=node_y,
                           mode='markers+text',
                           text=node_text,
                           textposition='top center',
                           marker=dict(size=15, color='lightblue',
                                     line=dict(width=2, color='black')),
                           hovertext=all_kits,
                           hoverinfo='text')
    
    fig = go.Figure(data=[edge_trace, node_trace],
                   layout=go.Layout(
                       title='Kit Dependencies (Y-axis = Production Day)',
                       showlegend=False,
                       xaxis=dict(title='Kits'),
                       yaxis=dict(title='Production Day')))
    
    return fig

def create_production_timeline_with_dependencies(production_timing, relationships):
    """Create timeline showing production order with dependency arrows"""
    if not production_timing:
        return go.Figure()
    
    # Prepare data
    timeline_data = []
    for kit, day in production_timing.items():
        timeline_data.append({
            'Kit': kit,
            'Day': day,
            'Short_Name': kit[:15] + "..." if len(kit) > 15 else kit
        })
    
    df = pd.DataFrame(timeline_data)
    
    # Create scatter plot
    fig = px.scatter(df, x='Day', y='Kit', 
                    hover_data=['Kit'],
                    title='Production Timeline with Dependencies')
    
    # Add dependency arrows
    for rel in relationships:
        source_day = production_timing.get(rel['source'], 0)
        target_day = production_timing.get(rel['target'], 0)
        
        # Add arrow if both kits are in timeline
        if source_day > 0 and target_day > 0:
            fig.add_annotation(
                x=target_day, y=rel['target'],
                ax=source_day, ay=rel['source'],
                arrowhead=2, arrowsize=1, arrowwidth=2,
                arrowcolor="red" if source_day > target_day else "green"
            )
    
    fig.update_layout(height=max(400, len(df) * 20))
    return fig

def calculate_dependency_depth(relationships):
    """Calculate maximum dependency depth"""
    if not NETWORKX_AVAILABLE or not relationships:
        return 0
    
    G = nx.DiGraph()
    for rel in relationships:
        G.add_edge(rel['source'], rel['target'])
    
    try:
        return nx.dag_longest_path_length(G)
    except:
        return 0

def get_most_dependent_kits(relationships):
    """Get kits with most dependencies"""
    dependency_counts = {}
    
    for rel in relationships:
        target = rel['target']
        dependency_counts[target] = dependency_counts.get(target, 0) + 1
    
    return sorted(dependency_counts.items(), key=lambda x: x[1], reverse=True)

def find_dependency_violations(production_timing, relationships):
    """Find cases where kits were produced before their dependencies"""
    violations = []
    
    for rel in relationships:
        source = rel['source']  # dependency
        target = rel['target']  # kit that depends on it
        
        source_day = production_timing.get(source, 0)
        target_day = production_timing.get(target, 0)
        
        if source_day > 0 and target_day > 0 and source_day > target_day:
            days_early = source_day - target_day
            severity = 'high' if days_early > 2 else 'medium' if days_early > 1 else 'low'
            
            violations.append({
                'kit': target,
                'dependency': source,
                'kit_day': target_day,
                'dependency_day': source_day,
                'days_early': days_early,
                'severity': severity
            })
    
    return violations

def analyze_dependency_timing(production_timing, relationships):
    """Analyze timing of all dependency relationships"""
    timing_analysis = []
    
    for rel in relationships:
        source = rel['source']
        target = rel['target']
        
        source_day = production_timing.get(source, 0)
        target_day = production_timing.get(target, 0)
        
        if source_day > 0 and target_day > 0:
            timing_diff = target_day - source_day
            status = "✅ Correct" if timing_diff >= 0 else "❌ Violation"
            
            timing_analysis.append({
                'Kit': target[:20] + "..." if len(target) > 20 else target,
                'Dependency': source[:20] + "..." if len(source) > 20 else source,
                'Kit Day': target_day,
                'Dep Day': source_day,
                'Gap (Days)': timing_diff,
                'Status': status
            })
    
    return sorted(timing_analysis, key=lambda x: x['Gap (Days)'])

def generate_dependency_recommendations(violations, relationships, production_timing):
    """Generate recommendations based on dependency analysis"""
    recommendations = []
    
    if not violations:
        recommendations.append("Excellent! All dependencies are being fulfilled in the correct order.")
        return recommendations
    
    # Group violations by severity
    high_severity = [v for v in violations if v['severity'] == 'high']
    medium_severity = [v for v in violations if v['severity'] == 'medium']
    
    if high_severity:
        recommendations.append(
            f"🚨 High Priority: {len(high_severity)} critical dependency violations found. "
            "Consider rescheduling production to ensure dependencies are produced first."
        )
    
    if medium_severity:
        recommendations.append(
            f"⚠️ Medium Priority: {len(medium_severity)} moderate dependency timing issues. "
            "Review production sequence for optimization opportunities."
        )
    
    # Most problematic kits
    problem_kits = {}
    for v in violations:
        kit = v['kit']
        problem_kits[kit] = problem_kits.get(kit, 0) + 1
    
    if problem_kits:
        worst_kit = max(problem_kits.items(), key=lambda x: x[1])
        recommendations.append(
            f"🎯 Focus Area: Kit {worst_kit[0]} has {worst_kit[1]} dependency issues. "
            "Consider moving its production later in the schedule."
        )
    
    return recommendations