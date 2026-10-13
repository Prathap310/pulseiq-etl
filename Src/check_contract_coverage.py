
from pathlib import Path
import pandas as pd
import re

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "Data" / "Raw"
DOCS_DIR = PROJECT_DIR / "Docs"
CONTRACT_FILE = DOCS_DIR / "data_contracts_full.csv"


def normalize(value):
    value = str(value).strip().lower()
    return re.sub(r"[^a-z0-9]+", "", value)


def main():
    if not CONTRACT_FILE.exists():
        raise FileNotFoundError(
            f"Contract file not found: {CONTRACT_FILE}. "
            "Run python Src/validate_contracts.py first."
        )

    contracts = pd.read_csv(CONTRACT_FILE, dtype=str).fillna("")
    datasets = sorted(RAW_DIR.glob("*.csv"))

    if not datasets:
        raise FileNotFoundError(
            f"No raw CSV datasets found in {RAW_DIR}"
        )

    # Collect all contract values without assuming column names.
    contract_values = set()
    for column in contracts.columns:
        for value in contracts[column]:
            value = normalize(value)
            if value:
                contract_values.add(value)

    results = []

    for dataset in datasets:
        dataset_name = dataset.stem
        normalized_name = normalize(dataset_name)

        # Exact matching only; avoid claiming a match from
        # unrelated partial text.
        matched = normalized_name in contract_values

        results.append({
            "dataset": dataset_name,
            "contract_name_exact_match": matched,
            "validation_status": (
                "NAME_MATCH_REVIEW_REQUIRED"
                if matched
                else "NO_EXACT_NAME_MATCH"
            ),
        })

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    output = DOCS_DIR / "contract_coverage.csv"
    pd.DataFrame(results).to_csv(output, index=False)

    print("Datasets checked:", len(results))
    print("Exact name matches:", sum(
        row["contract_name_exact_match"] for row in results
    ))
    print("Report saved to:", output)
    print(
        "Note: name matching alone does not validate "
        "columns, data types, or business rules."
    )


if __name__ == "__main__":
    main()
