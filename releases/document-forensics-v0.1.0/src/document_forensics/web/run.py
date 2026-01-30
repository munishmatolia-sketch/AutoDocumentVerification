#!/usr/bin/env python3
"""Entry point for running the Streamlit web interface."""

import sys
import subprocess
from pathlib import Path

def main():
    """Run the Streamlit web interface."""
    # Get the path to the streamlit app
    app_path = Path(__file__).parent / "streamlit_app.py"
    
    # Run streamlit with the app
    cmd = [
        sys.executable, "-m", "streamlit", "run", 
        str(app_path),
        "--server.port", "8501",
        "--server.address", "0.0.0.0",
        "--browser.gatherUsageStats", "false"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 Shutting down web interface...")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running web interface: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()