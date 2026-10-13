
from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent

WORKBOOK = (
    PROJECT_DIR
    / "Data"
    / "Source"
    / "03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx"
)

TARGET_SHEETS = [
    "data_contracts",
    "data_dictionary",
    "dq_checks_catalog",
    "dq_known_issues",
    "metric_dictionary",
    "data_contracts",
]


def main():
    if not WORKBOOK.exists():
        raise FileNotFoundError(f"Workbook not found: {WORKBOOK}")

    output_dir = PROJECT_DIR / "Docs"
    output_dir.mkdir(parents=True, exist_ok=True)

    with pd.ExcelFile(WORKBOOK) as excel:
        available = excel.sheet_names

        for sheet in TARGET_SHEETS:
            if sheet not in available:
                print(f"\nSheet not found: {sheet}")
                continue

            df = pd.read_excel(excel, sheet_name=sheet)

            print(f"\n{'=' * 60}")
            print(f"SHEET: {sheet}")
            print(f"Rows: {len(df)}")
            print(f"Columns: {list(df.columns)}")
            print(df.head(10).to_string(index=False))

            output_file = output_dir / f"{sheet}_inspection.csv"
            df.to_csv(output_file, index=False)
            print(f"Saved: {output_file}")

    print("\nContract inspection completed.")


if __name__ == "__main__":
    main()
