
from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "Data" / "Raw"
DOCS_DIR = PROJECT_DIR / "Docs"

DIMENSION_PREFIXES = ("dim_",)
FACT_PREFIXES = ("fact_",)
REFERENCE_NAMES = (
    "README",
    "data_dictionary",
    "metric_dictionary",
    "data_contracts",
    "dq_checks_catalog",
    "dq_known_issues",
    "reconciliation_answer_key",
    "reference_summary_dept_month",
    "budget_payroll_dept_month",
    "kpi_targets",
)


def classify(filename):
    name = Path(filename).stem.lower()

    if name.startswith(DIMENSION_PREFIXES):
        return "dimension"
    if name.startswith(FACT_PREFIXES):
        return "fact"
    if name in REFERENCE_NAMES:
        return "reference_or_validation"
    return "review_required"


def main():
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"Missing folder: {RAW_DIR}")

    files = sorted(RAW_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError(
            f"No CSV files found in {RAW_DIR}"
        )

    records = []

    for path in files:
        df = pd.read_csv(path, nrows=5)
        records.append({
            "file_name": path.name,
            "category": classify(path.name),
            "column_count": len(df.columns),
            "columns": ", ".join(map(str, df.columns)),
        })

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    output = DOCS_DIR / "dataset_classification.csv"
    pd.DataFrame(records).to_csv(output, index=False)

    print(pd.DataFrame(records)[
        ["file_name", "category", "column_count"]
    ].to_string(index=False))
    print(f"\nClassification saved to: {output}")


if __name__ == "__main__":
    main()
