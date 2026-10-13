
import json
from pathlib import Path
from datetime import datetime

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "Data" / "Raw"
REPORT_DIR = PROJECT_DIR / "Docs"

SUMMARY_COLUMNS = [
    "file",
    "dataset_type",
    "total_rows",
    "total_columns",
    "missing_cells",
    "duplicate_rows",
    "invalid_salary_rows",
    "quality_status",
    "issues_detected",
]


def check_data_quality(file_path):
    df = pd.read_csv(file_path, low_memory=False)

    missing_cells = int(df.isnull().sum().sum())
    duplicate_rows = int(df.duplicated().sum())

    invalid_salary = 0
    if "salary" in df.columns:
        salary = pd.to_numeric(df["salary"], errors="coerce")
        invalid_salary = int((salary.isna() | (salary <= 0)).sum())

    duplicate_columns = int(df.columns.duplicated().sum())
    empty_columns = sum(not str(c).strip() for c in df.columns)

    issues = []
    if missing_cells:
        issues.append("Missing values")
    if duplicate_rows:
        issues.append("Duplicate rows")
    if invalid_salary:
        issues.append("Invalid salary values")
    if duplicate_columns:
        issues.append("Duplicate column names")
    if empty_columns:
        issues.append("Empty column names")

    return {
        "file": file_path.name,
        "dataset_type": file_path.stem.split("_")[0],
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "missing_cells": missing_cells,
        "duplicate_rows": duplicate_rows,
        "invalid_salary_rows": invalid_salary,
        "quality_status": "CHECK" if issues else "PASS",
        "issues_detected": "; ".join(issues),
    }


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(RAW_DIR.glob("*.csv")) if RAW_DIR.exists() else []

    results = []
    read_errors = []

    for file_path in files:
        try:
            result = check_data_quality(file_path)
            results.append(result)
            print(
                f"{result['file']}: {result['total_rows']} rows, "
                f"status={result['quality_status']}"
            )
        except Exception as exc:
            read_errors.append({
                "file": file_path.name,
                "error": str(exc),
            })
            print(f"ERROR: {file_path.name}: {exc}")

    csv_path = REPORT_DIR / "raw_data_quality_report.csv"
    pd.DataFrame(results, columns=SUMMARY_COLUMNS).to_csv(
        csv_path, index=False
    )

    json_path = REPORT_DIR / "data_quality_report.json"
    report = {
        "project": "PulseIQ-ETL",
        "generated_at": datetime.now().astimezone().isoformat(),
        "files_checked": len(results),
        "files_failed_to_read": len(read_errors),
        "results": results,
        "read_errors": read_errors,
        "note": (
            "Initial profiling only. Evaluate findings against "
            "each dataset's data contract."
        ),
    }

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)

    print(f"CSV report: {csv_path}")
    print(f"JSON report: {json_path}")


if __name__ == "__main__":
    main()
