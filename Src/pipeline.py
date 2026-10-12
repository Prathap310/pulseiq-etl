
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

SCRIPTS = [
    ("ETL Processing", "etl.py"),
    ("Summary Report", "report.py"),
    ("Data Quality Check", "data_quality.py"),
]


def run_pipeline():
    print("=" * 50)
    print("       PULSEIQ-ETL AUTOMATED PIPELINE")
    print("=" * 50)

    for step_name, script_name in SCRIPTS:
        script_path = PROJECT_DIR / "Src" / script_name

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
