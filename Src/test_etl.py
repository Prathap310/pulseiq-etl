
import unittest
import pandas as pd

from etl import transform_data


class TestETL(unittest.TestCase):

    def test_column_names_are_cleaned(self):
        df = pd.DataFrame({
            " Employee Name ": ["Rahul"],
            " Department ": ["IT"]
        })

        result = transform_data(df)

        self.assertIn("employee_name", result.columns)
        self.assertIn("department", result.columns)

    def test_duplicate_rows_are_removed(self):
        df = pd.DataFrame({
            "employee_id": [101, 101],
            "employee_name": ["Rahul", "Rahul"],
            "department": ["IT", "IT"],
            "salary": [55000, 55000],
            "city": ["Bengaluru", "Bengaluru"]
        })

        result = transform_data(df)

        self.assertEqual(len(result), 1)

    def test_empty_values_are_removed(self):
        df = pd.DataFrame({
            "employee_id": [101, 102],
            "employee_name": ["Rahul", None],
            "department": ["IT", "HR"],
            "salary": [55000, 45000],
            "city": ["Bengaluru", "Hyderabad"]
        })

        result = transform_data(df)

        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
