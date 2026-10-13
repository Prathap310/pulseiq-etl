
import unittest
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "Data" / "Raw"
DOCS_DIR = PROJECT_DIR / "Docs"


class TestDatasetValidation(unittest.TestCase):

    def test_dataset_names_are_unique_when_raw_data_exists(self):
        files = list(RAW_DIR.glob("*.csv")) if RAW_DIR.exists() else []

        if not files:
            self.skipTest(
                "Raw CSV files are not included in this environment."
            )

        names = [file.stem.lower() for file in files]
        self.assertEqual(len(names), len(set(names)))

    def test_contract_report_has_valid_structure_when_available(self):
        contract_file = DOCS_DIR / "data_contracts_full.csv"

        if not contract_file.exists():
            self.skipTest(
                "Contract report is generated from the local workbook."
            )

        report = pd.read_csv(contract_file)
        self.assertGreater(len(report.columns), 0)

    def test_quality_report_has_required_columns_when_available(self):
        report_file = DOCS_DIR / "raw_data_quality_report.csv"

        if not report_file.exists():
            self.skipTest(
                "Run the data-quality script to generate this report."
            )

        report = pd.read_csv(report_file)
        columns = set(report.columns)

        self.assertTrue(
            {"dataset", "file"} & columns,
            f"Missing dataset identifier. Actual columns: {list(columns)}",
        )
        self.assertTrue(
            {"row_count", "total_rows", "rows"} & columns,
            f"Missing row count. Actual columns: {list(columns)}",
        )
        self.assertIn("quality_status", columns)


if __name__ == "__main__":
    unittest.main(verbosity=2)
