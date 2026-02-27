"""
File system monitoring utility for Streamlit apps.
Allows Streamlit to react to file changes in monitored directories.
"""

import datetime as dt
import os
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import streamlit as st


class StreamlitFileWatcher(FileSystemEventHandler):
    """
    File system event handler that triggers Streamlit reruns.
    """
    
    def __init__(self, hook, file_extensions=None):
        """
        Initialize the file watcher.
        
        Args:
            hook: Callback function to execute when files are modified
            file_extensions: List of file extensions to monitor (e.g., ['.csv', '.xlsx'])
                           If None, monitors all files
        """
        super().__init__()
        self.hook = hook
        self.file_extensions = file_extensions or []
        self.last_modified = dt.datetime.now()
        
    def on_modified(self, event):
        """
        Called when a file or directory is modified.
        
        Args:
            event: FileSystemEvent object containing event information
        """
        # Ignore directory events
        if event.is_directory:
            return
            
        # Check if file extension matches (if filter is specified)
        if self.file_extensions:
            file_ext = os.path.splitext(event.src_path)[1]
            if file_ext not in self.file_extensions:
                return
        
        # Debounce: Ignore events that happen too quickly
        now = dt.datetime.now()
        if now - self.last_modified < dt.timedelta(seconds=1):
            return
            
        self.last_modified = now
        
        # Log the event
        print(f"[Watchdog] File modified: {event.src_path}")
        
        # Trigger the hook to rerun Streamlit
        self.hook()


def update_dummy_module():
    """
    Update dummy.py to trigger a Streamlit rerun.
    This works because Streamlit monitors imported modules.
    """
    dummy_path = Path(__file__).parent / "dummy.py"
    
    # Create dummy file if it doesn't exist
    if not dummy_path.exists():
        dummy_path.parent.mkdir(parents=True, exist_ok=True)
        
    # Write timestamp to force file change
    with open(dummy_path, "w") as fp:
        fp.write(
            f'"""Auto-generated file for Streamlit file watching."""\n'
            f'# Last updated: {dt.datetime.now()}\n'
            f'timestamp = "{dt.datetime.now().isoformat()}"\n'
        )


@st.cache_resource
def install_file_monitor(watch_paths, file_extensions=None, recursive=True):
    """
    Install a file system monitor for specified paths.
    Uses st.cache_resource to ensure the observer is created only once.
    
    Args:
        watch_paths: Single path (str) or list of paths to monitor
        file_extensions: List of file extensions to monitor (e.g., ['.csv', '.xlsx'])
                        If None, monitors all files
        recursive: Whether to monitor subdirectories recursively
        
    Returns:
        Observer: The watchdog Observer instance
        
    Example:
        >>> # Monitor CSV files in data directory
        >>> install_file_monitor(
        ...     "data/real_data_excel/production_data",
        ...     file_extensions=['.csv'],
        ...     recursive=False
        ... )
        
        >>> # Monitor multiple directories
        >>> install_file_monitor(
        ...     ["data/hierarchy_exports", "data/real_data_excel"],
        ...     file_extensions=['.json', '.csv', '.xlsx']
        ... )
    """
    # Ensure watch_paths is a list
    if isinstance(watch_paths, str):
        watch_paths = [watch_paths]
    
    # Create observer
    observer = Observer()
    
    # Create event handler
    handler = StreamlitFileWatcher(
        hook=update_dummy_module,
        file_extensions=file_extensions
    )
    
    # Schedule monitoring for each path
    for path in watch_paths:
        abs_path = os.path.abspath(path)
        
        # Check if path exists
        if not os.path.exists(abs_path):
            print(f"[Watchdog] Warning: Path does not exist: {abs_path}")
            continue
            
        observer.schedule(handler, path=abs_path, recursive=recursive)
        print(f"[Watchdog] Monitoring: {abs_path} (recursive={recursive})")
    
    # Start the observer
    observer.start()
    print(f"[Watchdog] Observer started at {dt.datetime.now()}")
    
    return observer


def get_monitor_status():
    """
    Get the status of the file monitor.
    
    Returns:
        dict: Status information including monitored paths and file count
    """
    # This is a simple implementation
    # You can expand it to return more detailed information
    return {
        "active": True,
        "timestamp": dt.datetime.now().isoformat()
    }

