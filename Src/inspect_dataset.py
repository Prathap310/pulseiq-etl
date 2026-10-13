
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent.parent

WORKBOOK_PATH = (
    PROJECT_DIR
    / "Data"
    / "Source"
    / "03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx"
)

REPORT_DIR = PROJECT_DIR / "Docs"
REPORT_PATH = REPORT_DIR / "dataset_inventory.csv"


def main():
    if not WORKBOOK_PATH.exists():
        raise FileNotFoundError(
            f"Workbook not found: {WORKBOOK_PATH}"
        )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    inventory = []

    excel_file = pd.ExcelFile(WORKBOOK_PATH)

    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(
            excel_file,
            sheet_name=sheet_name,
        )

        inventory.append(
            {
                "sheet_name": sheet_name,
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": ", ".join(
                    str(column) for column in df.columns
                ),
            }
        )

        print(f"\nSheet: {sheet_name}")
        print(f"Rows: {len(df)}")
        print(f"Columns: {list(df.columns)}")

    pd.DataFrame(inventory).to_csv(
        REPORT_PATH,
        index=False,
    )

    print(f"\nTotal sheets: {len(inventory)}")
    print(f"Inventory saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
