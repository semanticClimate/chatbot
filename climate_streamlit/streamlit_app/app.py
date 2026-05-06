"""Streamlit entrypoint in separated streamlit_app directory."""

import os
from pathlib import Path
import runpy


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[1]
    os.chdir(base_dir)
    app_path = Path(base_dir, "app.py")
    runpy.run_path(str(app_path), run_name="__main__")
