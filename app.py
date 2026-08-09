"""Streamlit entry point for Healthcare IT market intelligence."""

import os

from src.healthcare.ui import run_healthcare_app


database_path = os.getenv("HEALTHCARE_DATABASE_PATH", "").strip()
if database_path:
    run_healthcare_app(database_path)
else:
    run_healthcare_app()
