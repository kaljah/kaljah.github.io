import sys
import os

sys.path.insert(0, os.path.abspath("new/server"))
from app import app
from background_processor import run_file_check

with app.app_context():
    # Make a copy because run_file_check might consume it
    import shutil
    shutil.copy("berkine_2022_all_68_sources.csv", "temp_check.csv")
    result = run_file_check(app, "temp_check.csv", "berkine_2022_all_68_sources.csv", 1, "auto")
    print("Errors:", result.get("errors"))
    print("Warnings:", result.get("warnings"))
    print("Parsed count:", result.get("total_rows"))
    print("Sample preview:", result.get("preview_rows", [])[:2])
