
import json
from pathlib import Path
from datetime import datetime

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent

CLEAN_DIR = PROJECT_DIR / "Data" / "Clean"
REJECTED_DIR = PROJECT_DIR / "Data" / "Rejected"
REPORT_DIR = PROJECT_DIR / "Docs"

REPORT_DIR.mkdir(parents=True, exist_ok=True)


def generate_report():
    clean_files = list(CLEAN_DIR.glob("*_cleaned.csv"))
    rejected_files = list(REJECTED_DIR.glob("*_rejected.csv"))

    total_valid = 0
    total_rejected = 0
    results = []

    for file_path in clean_files:
        df = pd.read_csv(file_path)
        total_valid += len(df)

        results.append({
            "file": file_path.name,
            "valid_records": len(df),
        })

    for file_path in rejected_files:
        df = pd.read_csv(file_path)
        total_rejected += len(df)

        results.append({
            "file": file_path.name,
            "rejected_records": len(df),
        })

    report = {
        "project": "PulseIQ-ETL",
        "generated_at": datetime.now().astimezone().isoformat(),
        "total_valid_records": total_valid,
        "total_rejected_records": total_rejected,
        "total_processed_records": total_valid + total_rejected,
        "files": results,
    }

    report_file = REPORT_DIR / "etl_summary.json"

    with open(report_file, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print("ETL summary report generated successfully.")
    print(f"Valid records: {total_valid}")
    print(f"Rejected records: {total_rejected}")
    print(f"Report saved to: {report_file}")


if __name__ == "__main__":
    generate_report()
