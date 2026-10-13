
import os
from pathlib import Path
from datetime import date

import pandas as pd
import psycopg2
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

CSV_PATH = PROJECT_DIR / "Data" / "Clean" / "employees_cleaned.csv"

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "warehouse-db"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "pulseiq_warehouse"),
    "user": os.getenv("DB_USER", "pulseiq_user"),
    "password": os.getenv("DB_PASSWORD", "pulseiq_local_password"),
}


def load_payroll():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)

    required = {"employee_id", "salary"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    df["employee_id"] = df["employee_id"].astype(str).str.strip()
    df["salary"] = pd.to_numeric(df["salary"], errors="raise")

    if df["employee_id"].duplicated().any():
        raise ValueError("Duplicate employee IDs found in CSV.")

    if df["salary"].isna().any() or (df["salary"] < 0).any():
        raise ValueError("Salary must be a non-negative number.")

    # The CSV does not specify a payroll month.
    # Use the current month as a provisional reporting month.
    today = date.today()
    month_start = today.replace(day=1)
    month_key = int(month_start.strftime("%Y%m%d"))

    inserted = 0
    skipped = 0

    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            # Ensure the first day of the month exists in dim_date.
            cur.execute(
                """
                INSERT INTO warehouse.dim_date (
                    date_key, full_date, day_number,
                    month_number, month_name,
                    quarter_number, year_number
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (full_date) DO NOTHING
                """,
                (
                    month_key, month_start, month_start.day,
                    month_start.month, month_start.strftime("%B"),
                    (month_start.month - 1) // 3 + 1,
                    month_start.year,
                ),
            )

            for row in df.to_dict("records"):
                cur.execute(
                    """
                    SELECT employee_key
                    FROM warehouse.dim_employee
                    WHERE employee_id = %s
                      AND is_current = TRUE
                    """,
                    (row["employee_id"],),
                )
                employee = cur.fetchone()

                if employee is None:
                    raise ValueError(
                        f"Employee not found: {row['employee_id']}"
                    )

                employee_key = employee[0]
                gross_salary = float(row["salary"])

                cur.execute(
                    """
                    INSERT INTO warehouse.fact_payroll (
                        employee_key, month_date_key,
                        gross_salary, deductions, net_salary
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (employee_key, month_date_key)
                    DO NOTHING
                    RETURNING employee_key
                    """,
                    (
                        employee_key, month_key,
                        gross_salary, 0, gross_salary,
                    ),
                )

                if cur.fetchone():
                    inserted += 1
                else:
                    skipped += 1

    print("\nPAYROLL LOAD COMPLETE")
    print(f"Payroll month: {month_start:%B %Y}")
    print(f"Inserted payroll rows: {inserted}")
    print(f"Existing rows skipped: {skipped}")


if __name__ == "__main__":
    load_payroll()
