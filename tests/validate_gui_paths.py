"""Run original/fixed source path behavior on the Actions macOS Tk runtime."""
import argparse
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--baseline-root")
parser.add_argument("--report", required=True)
args = parser.parse_args()
sys.path.insert(0, str(root))
import path_ui_checks
if args.baseline_root:
    sys.path.insert(0, args.baseline_root)
import gui
raise SystemExit(path_ui_checks.run_checks(gui, args.report, baseline=bool(args.baseline_root)))
