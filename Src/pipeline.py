
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

SCRIPTS = [
    ("Export Workbook Datasets", "export_datasets.py"),
    ("Inspect Dataset Inventory", "inspect_dataset.py"),
    ("Classify Datasets", "classify_datasets.py"),
    ("Validate Raw Datasets", "validate_datasets.py"),
    ("Inspect Data Contracts", "inspect_contracts.py"),
    ("ETL Processing", "etl.py"),
    ("Summary Report", "report.py"),
    ("Data Quality Check", "data_quality.py"),
    ("Build Validation Report", "build_validation_report.py"),
]


def run_pipeline():
    print("=" * 60)
    print("       PULSEIQ-ETL AUTOMATED PIPELINE")
    print("=" * 60)

    for step_name, script_name in SCRIPTS:
        script_path = PROJECT_DIR / "Src" / script_name

        if not script_path.exists():
            print(f"\nFAILED: Script not found: {script_path}")
            sys.exit(1)

        print(f"\nStarting: {step_name}")

        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=PROJECT_DIR,
            check=False,
        )

        if result.returncode != 0:
            print(f"FAILED: {step_name}")
            print("Pipeline stopped because a step failed.")
            sys.exit(result.returncode)

        print(f"COMPLETED: {step_name}")

    print("\nPipeline finished successfully!")


if __name__ == "__main__":
    run_pipeline()
