
import json
from pathlib import Path
from datetime import datetime

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
CLEAN_DIR = PROJECT_DIR / "Data" / "Clean"
REPORT_DIR = PROJECT_DIR / "Docs"

REPORT_DIR.mkdir(parents=True, exist_ok=True)


def check_data_quality(file_path):
    df = pd.read_csv(file_path)

    # Check for missing values
    missing_values = {
        str(column): int(count)
        for column, count in df.isnull().sum().items()
    }

    # Count duplicate rows
    duplicate_rows = int(df.duplicated().sum())

    # Check salary values when the column exists
    invalid_salary = 0

    if "salary" in df.columns:
        salary = pd.to_numeric(df["salary"], errors="coerce")
        invalid_salary = int(
            (salary.isna() | (salary <= 0)).sum()
        )

    return {
        "file": file_path.name,
        "total_rows": len(df),
        "missing_values": missing_values,
        "duplicate_rows": duplicate_rows,
        "invalid_salary_rows": invalid_salary,
        "quality_status": (
            "PASS"
            if (
                not df.isnull().any().any()
                and duplicate_rows == 0
                and invalid_salary == 0
            )
            else "CHECK"
        ),
    }


def main():
    files = list(CLEAN_DIR.glob("*_cleaned.csv"))

    if not files:
        print("No cleaned CSV files found.")
        return

    results = [
        check_data_quality(file_path)
        for file_path in files
    ]

    report = {
        "project": "PulseIQ-ETL",
        "generated_at": datetime.now().astimezone().isoformat(),
        "files_checked": len(results),
        "results": results,
    }

    report_path = REPORT_DIR / "data_quality_report.json"

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    for result in results:
        print(f"\nFile: {result['file']}")
        print(f"Rows: {result['total_rows']}")
        print(f"Duplicate rows: {result['duplicate_rows']}")
        print(f"Invalid salary rows: {result['invalid_salary_rows']}")
        print(f"Quality status: {result['quality_status']}")

    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
