#!/usr/bin/env python3
"""
Supply Roster Optimization Tool - Main Entry Point
Run this file to start the Streamlit application
"""

import sys
import os
import subprocess

def main():
    """Main entry point for the Supply Roster Optimization Tool"""
    
    # Get the directory where this script is located
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Add project root to Python path
    sys.path.insert(0, project_root)
    
    # Path to the Streamlit app
    app_path = os.path.join(project_root, 'ui', 'app.py')
    
    # Check if the app file exists
    if not os.path.exists(app_path):
        print(f"❌ Error: Could not find app.py at {app_path}")
        print("Please ensure the project structure is correct.")
        sys.exit(1)
    
    print("🚀 Starting Supply Roster Optimization Tool...")
    print(f"📁 Project root: {project_root}")
    print(f"🎯 App path: {app_path}")
    print("🌐 Opening in browser...")
    
    # Run Streamlit
    try:
        subprocess.run([
            sys.executable, '-m', 'streamlit', 'run', app_path,
            '--server.headless', 'false',
            '--server.address', 'localhost',
            '--server.port', '8501'
        ], cwd=project_root)
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
