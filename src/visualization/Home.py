import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Supply Roster Tool",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for shared variables
if 'data_path' not in st.session_state:
    st.session_state.data_path = "data/my_roster_data"
if 'target_date' not in st.session_state:
    st.session_state.target_date = ""

# Main page content
st.title("🏠 Supply Roster Optimization Tool")
st.markdown("---")

# Welcome section


col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("""
    ## 📋 Welcome to Supply Roster Tool

    """)

with col2:
    st.image("images/POC_page/POC_SupplyRoster_image.png", 
             caption="Supply Roster Tool Overview", 
             use_container_width=True)

# Global settings in sidebar
with st.sidebar:
    st.markdown("## 🌐 Global Settings")
    st.markdown("The setting will be shared across all pages")
    
    # Data path setting
    new_data_path = st.text_input(
        "📁 Data Path", 
        value=st.session_state.data_path,
        help="The data path will be shared across all pages"
    )
    
    if new_data_path != st.session_state.data_path:
        st.session_state.data_path = new_data_path
        st.success("✅ Data path updated!")
    
    st.markdown(f"**Current data path:** `{st.session_state.data_path}`")
    
    # Quick navigation
    st.markdown("## 🧭 Quick Navigation")
    if st.button("🎯 Go to Optimization", use_container_width=True):
        st.switch_page("pages/optimize_viz.py")
    
    if st.button("📊 Go to Dataset Overview", use_container_width=True):
        st.switch_page("pages/metadata.py")

# Main content area
st.markdown("---")


# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <small>Supply Roster Optimization Tool | Built with Streamlit</small>
</div>
""", unsafe_allow_html=True) 