
from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent

WORKBOOK = (
    PROJECT_DIR
    / "Data"
    / "Source"
    / "03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx"
)

DOCS_DIR = PROJECT_DIR / "Docs"


def main():
    if not WORKBOOK.exists():
        raise FileNotFoundError(f"Workbook not found: {WORKBOOK}")

    with pd.ExcelFile(WORKBOOK) as excel:
        if "data_contracts" not in excel.sheet_names:
            raise ValueError(
                "Sheet 'data_contracts' was not found."
            )

        contracts = pd.read_excel(
            excel,
            sheet_name="data_contracts",
        )

    print("Contract rows:", len(contracts))
    print("Contract columns:", contracts.columns.tolist())

    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = DOCS_DIR / "data_contracts_full.csv"
    contracts.to_csv(output_path, index=False)

    print("\nFirst 15 contract rows:")
    print(contracts.head(15).to_string(index=False))
    print(f"\nFull contract report saved to: {output_path}")


if __name__ == "__main__":
    main()
