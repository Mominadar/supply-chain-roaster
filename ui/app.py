"""
Supply Roster Optimization Tool - Streamlit App
Simplified version with configuration and optimization results
"""

import streamlit as st
import sys
import os

# Add project root to path BEFORE imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from ui.views.config_page import render_config_page
from ui.views.optimization_results import display_optimization_results
from src.demand_validation_viz import display_demand_validation

# Import authentication module
from ui.auth import require_authentication, render_logout_button, get_manager

# Import file watcher utilities
from ui.file_watcher import install_file_monitor, get_monitor_status
import ui.dummy  # IMPORTANT: This import is required for the watchdog to trigger reruns

# Set page config
st.set_page_config(
    page_title="Supply Roster Optimization Tool",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==============================================================================
# FILE MONITORING SETUP
# ==============================================================================
# Install file monitor to watch for data file changes
# This will automatically reload the app when monitored files are modified

# Define paths to monitor (relative to project root)
DATA_DIRS_TO_MONITOR = [
    os.path.join(project_root, "data/real_data_excel/production_data"),
    os.path.join(project_root, "data/hierarchy_exports"),
]

# Define file extensions to monitor (set to None to monitor all files)
MONITORED_EXTENSIONS = ['.csv', '.json', '.xlsx']

# Install the file monitor (runs only once due to @st.cache_resource)
try:
    install_file_monitor(
        watch_paths=DATA_DIRS_TO_MONITOR,
        file_extensions=MONITORED_EXTENSIONS,
        recursive=False  # Set to True to monitor subdirectories
    )
except Exception as e:
    # Silently handle errors - monitoring is optional
    print(f"[Watchdog] Error installing file monitor: {e}")

# ==============================================================================

# Initialize cookie manager ONCE
cookie_manager = get_manager()

# Check authentication before showing the app
if not require_authentication(cookie_manager):
    st.stop()  # Stop execution if not authenticated

# Render logout button at top right
render_logout_button(cookie_manager)

# Main title
st.title("📦 Supply Roster Optimization Tool")

# ==============================================================================
# TAB NAVIGATION
# ==============================================================================
tab_settings, tab_results, tab_validation = st.tabs([
    "⚙️ Settings",
    "📊 Optimization Results", 
    "📋 Demand Validation"
])

# Settings Tab
with tab_settings:
    st.markdown("---")
    render_config_page()

# Optimization Results Tab
with tab_results:
    st.markdown("---")
    # Check if we have results in session state
    if 'optimization_results' in st.session_state and st.session_state.optimization_results:
        display_optimization_results(st.session_state.optimization_results)
    else:
        st.info("🔄 No optimization results available yet.")
        st.markdown("Please run an optimization from the **⚙️ Settings** tab first to see results here.")
        
        # Add helpful instructions
        st.markdown("### 📋 How to Get Results:")
        st.markdown("1. Go to **⚙️ Settings** tab")
        st.markdown("2. Configure your optimization parameters")
        st.markdown("3. Click **🚀 Optimize Schedule**")
        st.markdown("4. Return here to view detailed results and input data inspection")

# Demand Validation Tab
with tab_validation:
    st.markdown("---")
    try:
        display_demand_validation()
    except ImportError as e:
        st.error(f"❌ Error loading demand validation module: {str(e)}")
        st.info("💡 Please ensure the demand validation module is properly installed.")
    except Exception as e:
        st.error(f"❌ Error in demand validation: {str(e)}")
        st.info("💡 Please check the data files and configuration.")

# ==============================================================================
# FILE MONITORING STATUS (collapsible footer)
# ==============================================================================
with st.expander("🔍 File Monitoring Status", expanded=False):
    status = get_monitor_status()
    if status["active"]:
        st.success("✅ Active")
        st.caption(f"Monitoring {len(DATA_DIRS_TO_MONITOR)} directories")
        st.caption(f"Extensions: {', '.join(MONITORED_EXTENSIONS)}")
        st.caption(f"Last check: {status['timestamp'][:19]}")
    else:
        st.warning("⚠️ Inactive")
