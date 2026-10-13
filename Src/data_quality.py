
import json
from pathlib import Path
from datetime import datetime

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "Data" / "Raw"
CLEAN_DIR = PROJECT_DIR / "Data" / "Clean"
REPORT_DIR = PROJECT_DIR / "Docs"

REPORT_DIR.mkdir(parents=True, exist_ok=True)


def check_data_quality(file_path):
    df = pd.read_csv(file_path, low_memory=False)

    missing_values = {
        str(column): int(count)
        for column, count in df.isnull().sum().items()
        if count > 0
    }

    duplicate_rows = int(df.duplicated().sum())

    invalid_salary = 0
    if "salary" in df.columns:
        salary = pd.to_numeric(df["salary"], errors="coerce")
        invalid_salary = int(
            (salary.isna() | (salary <= 0)).sum()
        )

    duplicate_columns = int(df.columns.duplicated().sum())
    empty_columns = int(
        sum(not str(column).strip() for column in df.columns)
    )

    issues = []
    if missing_values:
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
        "missing_cells": sum(missing_values.values()),
        "missing_values_by_column": missing_values,
        "duplicate_rows": duplicate_rows,
        "invalid_salary_rows": invalid_salary,
        "duplicate_column_names": duplicate_columns,
        "empty_column_names": empty_columns,
        "issues_detected": issues,
        "quality_status": "CHECK" if issues else "PASS",
    }


def main():
    files = sorted(RAW_DIR.glob("*.csv"))

    if not files:
        print(f"No raw CSV files found in {RAW_DIR}")
        return

    results = []
    failures = []

    for file_path in files:
        try:
            result = check_data_quality(file_path)
            results.append(result)

            print(
                f"{result['file']}: "
                f"{result['total_rows']} rows, "
                f"{result['missing_cells']} missing cells, "
                f"{result['duplicate_rows']} duplicate rows, "
                f"status={result['quality_status']}"
            )
        except Exception as exc:
            failures.append({
                "file": file_path.name,
                "error": str(exc),
            })
            print(f"ERROR: {file_path.name}: {exc}")

    report = {
        "project": "PulseIQ-ETL",
        "generated_at": datetime.now().astimezone().isoformat(),
        "source_folder": str(RAW_DIR),
        "files_checked": len(results),
        "files_failed_to_read": len(failures),
        "results": results,
        "read_errors": failures,
        "note": (
            "Initial profiling only. Missing values and duplicates "
            "must be evaluated against each dataset's data contract."
        ),
    }

    json_path = REPORT_DIR / "data_quality_report.json"
    csv_path = REPORT_DIR / "raw_data_quality_report.csv"

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    summary_rows = []
    for result in results:
        summary_rows.append({
            "file": result["file"],
            "dataset_type": result["dataset_type"],
            "total_rows": result["total_rows"],
            "total_columns": result["total_columns"],
            "missing_cells": result["missing_cells"],
            "duplicate_rows": result["duplicate_rows"],
            "invalid_salary_rows": result["invalid_salary_rows"],
            "quality_status": result["quality_status"],
            "issues_detected": "; ".join(result["issues_detected"]),
        })

    pd.DataFrame(summary_rows).to_csv(csv_path, index=False)

    print(f"\nFiles checked: {len(results)}")
    print(f"Files failed to read: {len(failures)}")
    print(f"JSON report: {json_path}")
    print(f"CSV report: {csv_path}")


if __name__ == "__main__":
    main()
