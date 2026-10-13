
from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
WORKBOOK = (
    PROJECT_DIR
    / "Data"
    / "Source"
    / "03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx"
)
RAW_DIR = PROJECT_DIR / "Data" / "Raw"
DOCS_DIR = PROJECT_DIR / "Docs"


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    contracts = None

    # Prefer the original workbook when it is available.
    if WORKBOOK.exists():
        with pd.ExcelFile(WORKBOOK) as excel:
            if "data_contracts" not in excel.sheet_names:
                raise ValueError(
                    "Sheet 'data_contracts' was not found in the workbook."
                )
            contracts = pd.read_excel(
                excel, sheet_name="data_contracts"
            )

    # CI can use the exported CSV if the workbook is not available.
    elif (RAW_DIR / "data_contracts.csv").exists():
        contracts = pd.read_csv(RAW_DIR / "data_contracts.csv")

    elif (DOCS_DIR / "data_contracts_full.csv").exists():
        contracts = pd.read_csv(
            DOCS_DIR / "data_contracts_full.csv"
        )

    else:
        raise FileNotFoundError(
            "Contract source not found. Provide the workbook at "
            f"{WORKBOOK} or export data_contracts.csv into {RAW_DIR}."
        )

    output_path = DOCS_DIR / "data_contracts_full.csv"
    contracts.to_csv(output_path, index=False)

    print(f"Contract rows: {len(contracts)}")
    print(f"Contract columns: {contracts.columns.tolist()}")
    print(f"Contract report saved to: {output_path}")


if __name__ == "__main__":
    main()
