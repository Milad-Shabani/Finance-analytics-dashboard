"""
TelNova Communications - Finance Analytics
Full Build Pipeline
=================================================
Runs the entire pipeline in one command:
    1. generate_finance_data.py  -> synthetic 3-statement financial model
    2. forecast_engine.py        -> revenue/EBITDA/cashflow forecast, capex plan, budget risk
    3. build_workbook.py         -> assembles data/Finance_Analytics_Workbook.xlsx
    4. (optional) LibreOffice recalculation, if installed
    5. export_dashboard_data.py  -> embeds data + Chart.js + SheetJS into dashboard/index.html

Author: Milad Shabani
"""

import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
STEPS = ["generate_finance_data.py", "forecast_engine.py", "build_workbook.py"]
POST_RECALC_STEPS = ["export_dashboard_data.py"]
WORKBOOK_PATH = os.path.join(PROJECT_ROOT, "data", "Finance_Analytics_Workbook.xlsx")
RECALC_SCRIPT_CANDIDATES = [
    "/mnt/skills/public/xlsx/scripts/recalc.py",  # available in Claude's sandbox
]


def try_recalculate():
    has_soffice = subprocess.run(["which", "soffice"], capture_output=True).returncode == 0
    if not has_soffice:
        print("\n(Optional) LibreOffice ('soffice') not found -- skipping formula recalculation.")
        print("The workbook's raw values are already correct (computed in Python); this step")
        print("just bakes cached values into the few live Excel formulas for viewers that don't")
        print("auto-calculate. Open the workbook in Excel/LibreOffice once and save it, or")
        print("install LibreOffice and re-run this script, if you want that step done too.")
        return
    for candidate in RECALC_SCRIPT_CANDIDATES:
        if os.path.exists(candidate):
            print("\n>>> Recalculating formulas with LibreOffice ...")
            subprocess.run([sys.executable, candidate, WORKBOOK_PATH, "90"])
            return


def main():
    print("=" * 70)
    print("TelNova Communications - Finance Analytics: Build Pipeline")
    print("=" * 70)
    for step in STEPS:
        path = os.path.join(SCRIPT_DIR, step)
        print(f"\n>>> Running {step} ...")
        result = subprocess.run([sys.executable, path], cwd=SCRIPT_DIR)
        if result.returncode != 0:
            print(f"\nPipeline stopped: {step} exited with code {result.returncode}")
            sys.exit(result.returncode)

    try_recalculate()

    for step in POST_RECALC_STEPS:
        path = os.path.join(SCRIPT_DIR, step)
        print(f"\n>>> Running {step} ...")
        result = subprocess.run([sys.executable, path], cwd=SCRIPT_DIR)
        if result.returncode != 0:
            print(f"\nPipeline stopped: {step} exited with code {result.returncode}")
            sys.exit(result.returncode)

    print("\n" + "=" * 70)
    print("Done. Workbook written to data/Finance_Analytics_Workbook.xlsx")
    print("Dashboard data snapshot written to dashboard/data.js")
    print("Open dashboard/index.html directly in a browser -- no server required.")
    print("(Use the 'Reload live from Excel' button when serving this project over http/https.)")
    print("=" * 70)


if __name__ == "__main__":
    main()
