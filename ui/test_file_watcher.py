"""
Test script to verify file watcher functionality.
Run this with: streamlit run ui/test_file_watcher.py

Then modify any CSV file in data/real_data_excel/production_data/
and watch the app automatically reload!
"""

import streamlit as st
import sys
import os
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from ui.file_watcher import install_file_monitor, get_monitor_status
import ui.dummy  # CRITICAL: This import enables the rerun mechanism

# Page configuration
st.set_page_config(
    page_title="File Watcher Test",
    page_icon="👀",
    layout="wide"
)

# Setup file monitoring
TEST_DATA_DIR = os.path.join(project_root, "data/real_data_excel/production_data")

st.title("👀 File Watcher Test")
st.markdown("---")

# Install monitor
try:
    observer = install_file_monitor(
        watch_paths=TEST_DATA_DIR,
        file_extensions=['.csv', '.json', '.xlsx'],
        recursive=False
    )
    st.success("✅ File monitor successfully installed!")
except Exception as e:
    st.error(f"❌ Error installing monitor: {e}")
    observer = None

# Display current status
st.header("📊 Monitoring Status")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Status", "🟢 Active" if observer else "🔴 Inactive")

with col2:
    st.metric("Directory", "production_data")

with col3:
    st.metric("Extensions", "csv, json, xlsx")

# Display monitored path
st.info(f"**Monitoring:** `{TEST_DATA_DIR}`")

# Instructions
st.markdown("---")
st.header("🧪 How to Test")

st.markdown("""
1. **Keep this page open** in your browser
2. **Open any CSV file** in `data/real_data_excel/production_data/`
3. **Make a small change** (add a space, modify a value, etc.)
4. **Save the file**
5. **Watch this page** - it should automatically reload within 1-2 seconds!

### Expected Behavior:
- ✅ Terminal shows: `[Watchdog] File modified: /path/to/file.csv`
- ✅ This page automatically reloads
- ✅ "Last Reload" timestamp below updates
""")

# Live reload indicator
st.markdown("---")
st.header("⏰ Live Status")

current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

col1, col2 = st.columns(2)

with col1:
    st.success(f"**Last Reload:** {current_time}")

with col2:
    status = get_monitor_status()
    st.info(f"**Monitor Check:** {status['timestamp'][:19]}")

# Counter to show app has rerun
if 'reload_count' not in st.session_state:
    st.session_state.reload_count = 0

st.session_state.reload_count += 1

st.metric(
    "Total Reloads",
    st.session_state.reload_count,
    help="This counter increments each time the app reruns"
)

# Debug information
with st.expander("🔍 Debug Information"):
    st.code(f"""
Directory exists: {os.path.exists(TEST_DATA_DIR)}
Observer active: {observer is not None}
Dummy module imported: {'ui.dummy' in sys.modules}
Current time: {current_time}
Project root: {project_root}
    """)

# Footer
st.markdown("---")
st.caption("💡 Tip: Check your terminal for [Watchdog] log messages when files change!")

