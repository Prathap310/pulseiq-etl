
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent.parent

WORKBOOK_PATH = (
    PROJECT_DIR
    / "Data"
    / "Source"
    / "03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx"
)

RAW_DIR = PROJECT_DIR / "Data" / "Raw"


def main():
    if not WORKBOOK_PATH.exists():
        raise FileNotFoundError(
            f"Workbook not found: {WORKBOOK_PATH}"
        )

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    with pd.ExcelFile(WORKBOOK_PATH) as workbook:
        for sheet_name in workbook.sheet_names:
            df = pd.read_excel(
                workbook,
                sheet_name=sheet_name,
            )

            # Make sheet names safe for filenames.
            safe_name = "".join(
                char if char.isalnum() or char in "-_"
                else "_"
                for char in sheet_name
            )

            output_path = RAW_DIR / f"{safe_name}.csv"

            df.to_csv(output_path, index=False)

            print(
                f"Exported {sheet_name}: "
                f"{len(df)} rows -> {output_path.name}"
            )

    print("\nDataset export completed.")


if __name__ == "__main__":
    main()
