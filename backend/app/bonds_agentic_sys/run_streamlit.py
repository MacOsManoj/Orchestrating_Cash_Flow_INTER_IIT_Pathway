#!/usr/bin/env python3
"""
Simple script to run the Streamlit app
"""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    script_path = Path(__file__).parent / "streamlit_app.py"

    print(" Starting Agent Bond Streamlit UI...")
    print(" Make sure you have set OPENAI_API_KEY in your .env file")
    print(" The app will open in your browser at http://localhost:8501\n")

    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(script_path)], check=True
        )
    except KeyboardInterrupt:
        print("\nShutting down...")
    except subprocess.CalledProcessError as e:
        print(f" Error running Streamlit: {e}")
        sys.exit(1)
