
from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "Data" / "Raw"
DOCS_DIR = PROJECT_DIR / "Docs"


def validate_csv(path):
    df = pd.read_csv(path)

    return {
        "file_name": path.name,
        "row_count": len(df),
        "column_count": len(df.columns),
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_cells": int(df.isna().sum().sum()),
        "duplicate_column_names": int(
            df.columns.duplicated().sum()
        ),
        "empty_column_names": int(
            sum(not str(c).strip() for c in df.columns)
        ),
    }


def main():
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"Folder not found: {RAW_DIR}")

    files = sorted(RAW_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError(
            f"No CSV files found in {RAW_DIR}"
        )

    results = []

    for path in files:
        try:
            result = validate_csv(path)
            results.append(result)
            print(
                f"{path.name}: "
                f"{result['row_count']} rows, "
                f"{result['duplicate_rows']} duplicate rows, "
                f"{result['missing_cells']} missing cells"
            )
        except Exception as exc:
            results.append({
                "file_name": path.name,
                "error": str(exc),
            })
            print(f"ERROR: {path.name}: {exc}")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DOCS_DIR / "raw_data_quality_report.csv"

    pd.DataFrame(results).to_csv(report_path, index=False)
    print(f"\nQuality report saved to: {report_path}")


if __name__ == "__main__":
    main()
