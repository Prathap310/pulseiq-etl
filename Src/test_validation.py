
import unittest
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "Data" / "Raw"
DOCS_DIR = PROJECT_DIR / "Docs"


class TestDatasetValidation(unittest.TestCase):

    def test_dataset_names_are_unique(self):
        self.assertTrue(
            RAW_DIR.exists(),
            f"Raw folder is missing: {RAW_DIR}",
        )

        files = list(RAW_DIR.glob("*.csv"))

        self.assertGreater(
            len(files),
            0,
            "No raw CSV datasets found.",
        )

        names = [file.stem.lower() for file in files]

        self.assertEqual(
            len(names),
            len(set(names)),
            "Duplicate dataset filenames found.",
        )

    def test_contract_report_exists(self):
        contract_file = DOCS_DIR / "data_contracts_full.csv"

        self.assertTrue(
            contract_file.exists(),
            "Contract report missing. Run: "
            "python Src/validate_contracts.py",
        )

    def test_quality_report_has_required_columns(self):
        report_file = DOCS_DIR / "raw_data_quality_report.csv"

        self.assertTrue(
            report_file.exists(),
            "Quality report missing. Run: "
            "python Src/validate_datasets.py",
        )

        report = pd.read_csv(report_file)
        columns = set(report.columns)

        # Accept common alternative names for dataset identifiers.
        self.assertTrue(
            {"dataset", "file"} & columns,
            "Missing dataset identifier. Actual columns: "
            f"{list(report.columns)}",
        )

        # Accept common alternative names for row counts.
        self.assertTrue(
            {"row_count", "total_rows", "rows"} & columns,
            "Missing row count. Actual columns: "
            f"{list(report.columns)}",
        )

        self.assertIn(
            "quality_status",
            columns,
            "Missing quality_status. Actual columns: "
            f"{list(report.columns)}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
