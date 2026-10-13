
import os
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
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


def load_warehouse():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Cleaned CSV not found: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    required = {
        "employee_id", "employee_name", "department"
    }

    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing CSV columns: {sorted(missing)}")

    df = df.drop_duplicates(subset=["employee_id"])

    today = date.today()
    today_key = int(today.strftime("%Y%m%d"))

    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            # 1. Load today's date dimension record.
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
                    today_key, today, today.day,
                    today.month, today.strftime("%B"),
                    (today.month - 1) // 3 + 1,
                    today.year,
                ),
            )

            inserted = 0
            updated = 0
            unchanged = 0

            for row in df.to_dict("records"):
                employee_id = str(row["employee_id"]).strip()
                employee_name = str(row["employee_name"]).strip()
                department = str(row["department"]).strip()

                if not employee_id or not employee_name or not department:
                    raise ValueError(
                        f"Invalid employee record: {row}"
                    )

                # 2. Create the department if it doesn't exist.
                cur.execute(
                    """
                    INSERT INTO warehouse.dim_department (
                        department_name
                    )
                    VALUES (%s)
                    ON CONFLICT (department_name) DO NOTHING
                    """,
                    (department,),
                )

                cur.execute(
                    """
                    SELECT department_key
                    FROM warehouse.dim_department
                    WHERE department_name = %s
                    """,
                    (department,),
                )
                department_key = cur.fetchone()["department_key"]

                # 3. Find the employee's current version.
                cur.execute(
                    """
                    SELECT employee_key, employee_name,
                           department_key, valid_from
                    FROM warehouse.dim_employee
                    WHERE employee_id = %s
                      AND is_current = TRUE
                    FOR UPDATE
                    """,
                    (employee_id,),
                )
                existing = cur.fetchone()

                if existing is None:
                    cur.execute(
                        """
                        INSERT INTO warehouse.dim_employee (
                            employee_id, employee_name,
                            department_key, valid_from,
                            valid_to, is_current
                        )
                        VALUES (%s, %s, %s, %s, NULL, TRUE)
                        """,
                        (
                            employee_id, employee_name,
                            department_key, today,
                        ),
                    )
                    inserted += 1

                elif (
                    existing["employee_name"] != employee_name
                    or existing["department_key"] != department_key
                ):
                    # If a change occurs on the same day,
                    # update today's version instead of creating
                    # two versions with the same valid_from date.
                    if existing["valid_from"] == today:
                        cur.execute(
                            """
                            UPDATE warehouse.dim_employee
                            SET employee_name = %s,
                                department_key = %s
                            WHERE employee_key = %s
                            """,
                            (
                                employee_name, department_key,
                                existing["employee_key"],
                            ),
                        )
                    else:
                        cur.execute(
                            """
                            UPDATE warehouse.dim_employee
                            SET valid_to = %s,
                                is_current = FALSE
                            WHERE employee_key = %s
                            """,
                            (
                                today - timedelta(days=1),
                                existing["employee_key"],
                            ),
                        )

                        cur.execute(
                            """
                            INSERT INTO warehouse.dim_employee (
                                employee_id, employee_name,
                                department_key, valid_from,
                                valid_to, is_current
                            )
                            VALUES (%s, %s, %s, %s, NULL, TRUE)
                            """,
                            (
                                employee_id, employee_name,
                                department_key, today,
                            ),
                        )

                    updated += 1

                else:
                    unchanged += 1

    print("\nWAREHOUSE DIMENSION LOAD COMPLETE")
    print(f"Source rows processed: {len(df)}")
    print(f"New employees: {inserted}")
    print(f"Updated employee versions: {updated}")
    print(f"Unchanged employees: {unchanged}")


if __name__ == "__main__":
    load_warehouse()
