#!/usr/bin/env python3
"""
Demand Data Validation Visualization Module

Provides Streamlit visualization for demand data validation.
Shows which products are included/excluded from optimization and why.
"""

import pandas as pd
import streamlit as st
from typing import Dict
from src.config.constants import LineType
from src.demand_filtering import DemandFilter


# Simple mapping for product level names
LEVEL_NAMES = {
    'prepack': 'prepack',
    'subkit': 'subkit',
    'master': {
        'non_virtual': 'non_virtual_master',
        'with_hierarchy': 'master_with_hierarchy'
    },
    'unclassified': 'no_hierarchy_data'
}


class DemandValidationViz:
    """
    Simple visualization wrapper for demand filtering results.
    All filtering logic is in DemandFilter - this just displays the results.
    """
    
    def __init__(self):
        self.filter_instance = DemandFilter()
        self.speed_data = None
        
    def load_data(self):
        """Load all data needed for visualization"""
        try:
            import streamlit as st
            from src.config.optimization_config import get_date_configuration
            from src.preprocess import extract
            
            # Get date range from SINGLE SOURCE OF TRUTH
            demand_start_date, _, _, _, _ = get_date_configuration()
            
            self.speed_data = extract.read_package_speed_data()
            return self.filter_instance.load_data(start_date=demand_start_date)
        except Exception as e:
            error_msg = f"Error loading data: {str(e)}"
            print(error_msg)
            if st:
                st.error(error_msg)
            return False
    
    def validate_all_products(self) -> pd.DataFrame:
        """
        Create DataFrame with validation results for all products.
        Main visualization method - converts filtering results to displayable format.
        """
        # Get analysis from filtering module
        analysis = self.filter_instance.get_complete_product_analysis()
        product_details = analysis['product_details']
        
        results = []
        for product_id, details in product_details.items():
            # Calculate production hours if speed data available
            speed = self.speed_data.get(product_id) if self.speed_data else None
            production_hours = (details['demand'] / speed) if speed and speed > 0 else None
            material_description = details['material_description']
            # Get line type name
            line_type_id = details['line_assignment']
            line_name = LineType.get_name(line_type_id) if line_type_id is not None else "no_assignment"
            
            # Get level name (simplified)
            ptype = details['product_type']
            if ptype == 'unclassified':
                level_name = LEVEL_NAMES['unclassified']
            elif ptype == 'master':
                level_name = LEVEL_NAMES['master']['non_virtual' if details['is_non_virtual_master'] else 'with_hierarchy']
            else:
                level_name = LEVEL_NAMES.get(ptype, f"level_{ptype}")
            
            # Build validation status message
            if not details['is_included_in_optimization']:
                validation_status = f"🚫 Excluded: {', '.join(details['exclusion_reasons'])}"
            else:
                issues = []
                if speed is None:
                    issues.append("missing_speed_data")
                if not details['has_hierarchy']:
                    issues.append("no_hierarchy_data")
                validation_status = f"⚠️ Data Issues: {', '.join(issues)}" if issues else "✅ Ready for optimization"



            if details['has_too_high_demand']:
                issues.append("too_high_demand")
                validation_status = f"⚠️ Data Issues: {', '.join(issues)}" if issues else "✅ Ready for optimization"
            results.append({
                'Product ID': product_id,
                'Material description': material_description,
                'Demand': details['demand'],
                'Product Type': ptype.title(),
                'Level': level_name,
                'Is non_virtual Master': "Yes" if details['is_non_virtual_master'] else "No",
                'Line Type ID': line_type_id if line_type_id else "N/A",
                'Line Type': line_name,
                'UNICEF Staff': details['unicef_staff'],
                'Humanizer Staff': details['humanizer_staff'],
                'Total Staff': details['total_staff'],
                'Production Speed (units/hour)': f"{speed:.1f}" if speed else "N/A",
                'Production Hours Needed': f"{production_hours:.1f}" if production_hours else "N/A",
                'Has Line Assignment': "✅" if details['has_line_assignment'] else "❌",
                'Has Staffing Data': "✅" if details['has_staffing'] else "❌", 
                'Has Speed Data': "✅" if speed is not None else "❌ ",
                'Has Hierarchy Data': "✅" if details['has_hierarchy'] else "❌",
                'Excluded from Optimization': not details['is_included_in_optimization'],
                'Exclusion Reasons': ', '.join(details['exclusion_reasons']) if details['exclusion_reasons'] else '',
                'Data Quality Issues': ', '.join(issues) if details['is_included_in_optimization'] and 'issues' in locals() and issues else '',
                'Has Too High Demand': "✅" if details['has_too_high_demand'] else "❌",
                'Validation Status': validation_status
            })
        
        df = pd.DataFrame(results)
        df = df.sort_values(['Excluded from Optimization', 'Demand'], ascending=[False, False])
        return df
    
    def get_summary_statistics(self, df: pd.DataFrame) -> Dict:
        """Calculate summary statistics from validation results"""
        analysis = self.filter_instance.get_complete_product_analysis()
        included_df = df[df['Excluded from Optimization'] == False]
        
        return {
            'total_products': analysis['total_products'],
            'total_demand': analysis['total_demand'],
            'included_products': analysis['included_count'],
            'excluded_products': analysis['excluded_count'],
            'included_demand': analysis['included_demand'],
            'excluded_demand': analysis['excluded_demand'],
            'type_counts': df['Product Type'].value_counts().to_dict(),
            'no_line_assignment': len(included_df[included_df['Has Line Assignment'] == "❌"]),
            'no_staffing': len(included_df[included_df['Has Staffing Data'] == "❌"]),
            'no_speed': len(included_df[included_df['Has Speed Data'].str.contains("❌")]),
            'no_hierarchy': len(included_df[included_df['Has Hierarchy Data'] == "❌"]),
            'non_virtual_masters': analysis['non_virtual_masters_count'],
            'excluded_with_too_high_demand': analysis['excluded_with_too_high_demand_count']
        }


def display_demand_validation():
    """
    Display demand validation analysis in Streamlit.
    Main entry point for the validation page.
    """
    st.header("📋 Demand Data Validation")
    st.markdown("Analysis showing which products are included/excluded from optimization and data quality status.")
    
    # Load and analyze data
    validator = DemandValidationViz()
    with st.spinner("Loading and analyzing data..."):
        if not validator.load_data():
            st.error("Failed to load data for validation.")
            return
        validation_df = validator.validate_all_products()
        stats = validator.get_summary_statistics(validation_df)
    
    # ===== SUMMARY METRICS =====
    st.subheader("📊 Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Products", stats['total_products'])
    col1.metric("Included in Optimization", stats['included_products'], delta="Ready")
    col2.metric("Total Demand", f"{stats['total_demand']:,}")
    col2.metric("Excluded from Optimization", stats['excluded_products'], delta="Omitted")
    col3.metric("Included Demand", f"{stats['included_demand']:,}", delta="Will be optimized")
    col4.metric("Excluded Demand", f"{stats['excluded_demand']:,}", delta="Omitted")
    
    # ===== PRODUCT TYPE DISTRIBUTION =====
    st.subheader("📈 Product Type Distribution")
    if stats['type_counts']:
        col1, col2 = st.columns(2)
        with col1:
            type_df = pd.DataFrame(list(stats['type_counts'].items()), columns=['Product Type', 'Count'])
            st.bar_chart(type_df.set_index('Product Type'))
        with col2:
            for ptype, count in stats['type_counts'].items():
                percentage = (count / stats['total_products']) * 100
                st.write(f"**{ptype}:** {count} products ({percentage:.1f}%)")
    
    # ===== DATA QUALITY ISSUES (for included products only) =====
    st.subheader("⚠️ Data Quality Issues (Included Products)")
    st.write("Issues affecting products that **will be** included in optimization:")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("No Line Assignment", stats['no_line_assignment'], 
                delta=None if stats['no_line_assignment'] == 0 else "Issue")
    col2.metric("No Staffing Data", stats['no_staffing'],
                delta=None if stats['no_staffing'] == 0 else "Issue")
    col3.metric("No Speed Data", stats['no_speed'],
                delta=None if stats['no_speed'] == 0 else "Will use default")
    col4.metric("No Hierarchy Data", stats['no_hierarchy'],
                delta=None if stats['no_hierarchy'] == 0 else "Issue")
    # col5.metric("Excluded: Too High Demand", stats['excluded_with_too_high_demand'],
    #             delta=None if stats['excluded_with_too_high_demand'] == 0 else "Excluded")
    # # ===== INCLUDED PRODUCTS TABLE =====
    included_df = validation_df[validation_df['Excluded from Optimization'] == False].copy()
    excluded_df = validation_df[validation_df['Excluded from Optimization'] == True].copy()
    
    st.subheader("✅ Products Included in Optimization")
    st.write(f"**{len(included_df)} products** with total demand of **{included_df['Demand'].sum():,} units**")
    
    if len(included_df) > 0:
        # Filters
        col1, col2 = st.columns(2)
        type_filter = col1.selectbox("Filter by type", ["All"] + list(included_df['Product Type'].unique()), key="inc_filter")
        min_demand = col2.number_input("Minimum demand", min_value=0, value=0, key="inc_demand")
        
        # Apply filters
        filtered = included_df.copy()
        if type_filter != "All":
            filtered = filtered[filtered['Product Type'] == type_filter]
        if min_demand > 0:
            filtered = filtered[filtered['Demand'] >= min_demand]
        
        # Display table
        display_cols = ['Product ID', 'Material description','Demand', 'Product Type', 'Line Type', 'UNICEF Staff', 
                       'Humanizer Staff', 'Production Speed (units/hour)', 'Data Quality Issues', 'Validation Status']
        st.dataframe(filtered[display_cols], use_container_width=True, height=300)
    else:
        st.warning("No products are included in optimization!")
    
    # ===== EXCLUDED PRODUCTS TABLE =====
    st.subheader("🚫 Products Excluded from Optimization")
    st.write(f"**{len(excluded_df)} products** with total demand of **{excluded_df['Demand'].sum():,} units**")
    st.info("Excluded due to: missing line assignments, zero staffing, or virtual masters")
    
    if len(excluded_df) > 0:
        # Show exclusion breakdown
        st.write("**Exclusion reasons:**")
        for reason, count in excluded_df['Exclusion Reasons'].value_counts().items():
            st.write(f"• {reason}: {count} products")
        
        # Display table
        display_cols = ['Product ID', 'Demand', 'Product Type', 'Exclusion Reasons', 
                       'UNICEF Staff', 'Humanizer Staff', 'Line Type']
        st.dataframe(excluded_df[display_cols], use_container_width=True, height=200)
        
        # Export button
        if st.button("📥 Export Validation Results to CSV"):
            st.download_button("Download CSV", validation_df.to_csv(index=False),
                             file_name="demand_validation_results.csv", mime="text/csv")
    
    # ===== RECOMMENDATIONS =====
    st.subheader("💡 Recommendations")
    
    if stats['excluded_products'] > 0:
        st.warning(f"**{stats['excluded_products']} products** ({stats['excluded_demand']:,} units) excluded from optimization")
    
    # Show data quality issues for included products
    if stats['no_line_assignment'] > 0:
        st.info(f"**Line Assignment**: {stats['no_line_assignment']} included products missing line assignments")
    if stats['no_staffing'] > 0:
        st.info(f"**Staffing Data**: {stats['no_staffing']} included products missing staffing requirements")
    if stats['no_speed'] > 0:
        st.info(f"**Speed Data**: {stats['no_speed']} included products missing speed data (will use default 106.7 units/hour)")
    if stats['no_hierarchy'] > 0:
        st.info(f"**Hierarchy Data**: {stats['no_hierarchy']} included products not in kit hierarchy")
    
    # Overall status
    if stats['included_products'] > 0:
        st.success(f"✅ **{stats['included_products']} products** with {stats['included_demand']:,} units demand ready for optimization!")
        if stats['no_speed'] == 0 and stats['no_hierarchy'] == 0:
            st.info("🎉 All included products have complete data!")
    else:
        st.error("❌ No products passed filtering. Review exclusion reasons and check data configuration.")


if __name__ == "__main__":
    # For testing
    display_demand_validation()
