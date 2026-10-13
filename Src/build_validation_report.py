
from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_DIR / "Docs"

INPUT_FILES = [
    DOCS_DIR / "dataset_inventory.csv",
    DOCS_DIR / "dataset_classification.csv",
    DOCS_DIR / "raw_data_quality_report.csv",
]


def main():
    reports = {}

    for path in INPUT_FILES:
        if path.exists():
            df = pd.read_csv(path)
            reports[path.name] = df
            print(f"Loaded {path.name}: {len(df)} rows")
        else:
            print(f"Not available yet: {path.name}")

    if not reports:
        raise FileNotFoundError(
            "No inspection reports found. "
            "Run the previous inspection scripts first."
        )

    output_path = DOCS_DIR / "task1_validation_summary.txt"

    with output_path.open("w", encoding="utf-8") as output:
        output.write("PULSEIQ TASK 1 - VALIDATION SUMMARY\n")
        output.write("=" * 45 + "\n\n")

        for name, df in reports.items():
            output.write(f"\nREPORT: {name}\n")
            output.write("-" * 45 + "\n")
            output.write(df.to_string(index=False))
            output.write("\n")

    print(f"\nSummary saved to: {output_path}")


if __name__ == "__main__":
    main()
