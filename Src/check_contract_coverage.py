from pathlib import Path
import re

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "Data" / "Raw"
DOCS_DIR = PROJECT_DIR / "Docs"
CONTRACT_FILE = DOCS_DIR / "data_contracts_full.csv"


def normalize(value):
    value = str(value).strip().lower()
    return re.sub(r"[^a-z0-9]+", "", value)


def extract_dataset_names(feed):
    """Extract dataset names from feeds like 'AI anomaly results (fact_anomaly)'."""
    names = set()

    for name in re.findall(r"\(([^()]*)\)", str(feed)):
        if name.strip():
            names.add(normalize(name))

    if not names:
        names.add(normalize(feed))

    return names


def main():
    if not CONTRACT_FILE.exists():
        raise FileNotFoundError(
            f"Contract file not found: {CONTRACT_FILE}. "
            "Run python Src/validate_contracts.py first."
        )

    contracts = pd.read_csv(CONTRACT_FILE, dtype=str).fillna("")

    required_columns = {"feed", "column_name"}
    missing_columns = required_columns - set(contracts.columns)
    if missing_columns:
        raise ValueError(
            "Contract file is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    if not RAW_DIR.exists():
        raise FileNotFoundError(f"Raw data directory not found: {RAW_DIR}")

    contract_names = set()
    feed_column_counts = {}

    for feed, group in contracts.groupby("feed", dropna=False):
        names = extract_dataset_names(feed)
        contract_names.update(names)

        for name in names:
            feed_column_counts[name] = (
                feed_column_counts.get(name, 0)
                + group["column_name"].str.strip().replace("", pd.NA).dropna().nunique()
            )

    datasets = sorted(RAW_DIR.glob("*.csv"))
    results = []

    for dataset in datasets:
        dataset_name = dataset.stem
        normalized_name = normalize(dataset_name)
        is_contracted = normalized_name in contract_names

        results.append({
            "dataset": dataset_name,
            "contract_defined": is_contracted,
            "contracted_columns": feed_column_counts.get(normalized_name, 0),
            "validation_status": (
                "CONTRACT_DEFINED_REQUIRES_SCHEMA_VALIDATION"
                if is_contracted
                else "NO_CONTRACT_DEFINITION_FOUND"
            ),
        })

    report = pd.DataFrame(results)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    output = DOCS_DIR / "contract_coverage.csv"
    report.to_csv(output, index=False)

    print("Raw datasets checked:", len(results))
    print("Datasets with contract definitions:", int(report["contract_defined"].sum()))
    print("Datasets without contract definitions:", int((~report["contract_defined"]).sum()))
    print("Report saved to:", output)
    print(
        "Note: this report identifies contract coverage only. "
        "It does not validate data types, nullability, or business rules."
    )


if __name__ == "__main__":
    main()
