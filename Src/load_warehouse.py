"""Load the PulseIQ star-schema workbook into PostgreSQL schema dw.

Dimensions are loaded before facts. The loader:
- preserves source records and adds documented special dimension members
  needed by source foreign keys;
- extends the date dimension through 2027-03-31 for forecast month-end keys;
- loads the self-referencing account hierarchy parent-first;
- uses primary-key upserts inside one database transaction.

Run inside Docker from the project root:
    docker compose run --rm --entrypoint python etl Src/load_warehouse.py
"""
from __future__ import annotations

import os
from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_batch
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

WORKBOOK = (
    PROJECT_DIR
    / "Data"
    / "Source"
    / "03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx"
)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "pulseiq_wh"),
    "user": os.getenv("DB_USER", "wos"),
    "password": os.getenv("DB_PASSWORD", "wos"),
}

DIMENSION_ORDER = [
    "dim_date",
    "dim_department",
    "dim_location",
    "dim_leave_type",
    "dim_account",  # self-referencing hierarchy, ordered parent-first
    "dim_client",
    "dim_role",
    "dim_employee",
    "dim_vendor",
    "dim_team",
    "dim_sprint",
]

FACT_ORDER = [
    "fact_payroll",
    "fact_attendance_monthly",
    "fact_leave",
    "fact_headcount_monthly",
    "fact_ledger",
    "fact_invoice",
    "fact_invoice_payment",
    "fact_expense",
    "fact_task",
    "fact_anomaly",
    "fact_attrition_risk",
    "fact_forecast",
]

TABLE_ORDER = DIMENSION_ORDER + FACT_ORDER


def is_missing(value: Any) -> bool:
    """Safely identify scalar missing values from pandas/numpy."""
    if value is None:
        return True
    try:
        result = pd.isna(value)
        return bool(result) if not hasattr(result, "__len__") else False
    except (TypeError, ValueError):
        return False


def normalise_value(value: Any, pg_type: str) -> Any:
    """Convert pandas/numpy values to psycopg2-friendly Python values."""
    if is_missing(value):
        return None

    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    elif hasattr(value, "item") and callable(value.item):
        value = value.item()

    if pg_type == "boolean":
        if isinstance(value, bool):
            return value
        text = str(value).strip().upper()
        if text in {"Y", "YES", "TRUE", "T", "1"}:
            return True
        if text in {"N", "NO", "FALSE", "F", "0"}:
            return False
        raise ValueError(f"Cannot convert {value!r} to PostgreSQL boolean")

    if isinstance(value, str):
        value = value.strip()
        return value if value else None

    if isinstance(value, (datetime, date, Decimal, int, float, bool)):
        return value

    return value


def get_table_metadata(cur, table_name: str):
    cur.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'dw' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table_name,),
    )
    columns = cur.fetchall()
    if not columns:
        raise RuntimeError(f"Target table dw.{table_name} does not exist")

    cur.execute(
        """
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.constraint_schema = kcu.constraint_schema
         AND tc.table_name = kcu.table_name
        WHERE tc.table_schema = 'dw'
          AND tc.table_name = %s
          AND tc.constraint_type = 'PRIMARY KEY'
        ORDER BY kcu.ordinal_position
        """,
        (table_name,),
    )
    pk_columns = [row[0] for row in cur.fetchall()]
    if not pk_columns:
        raise RuntimeError(
            f"dw.{table_name} has no primary key; safe upsert is unavailable"
        )

    return columns, pk_columns


def normalise_account_code(value: Any) -> str | None:
    """Normalize Excel account codes and treat blank/NaN parents as None."""
    # Handle Python None, pandas NA, NumPy NaN, and Excel blank cells first.
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    text = str(value).strip()
    if not text or text.casefold() in {"nan", "none", "null", "<na>"}:
        return None

    # Excel may represent whole-number account codes as floats (e.g. 1000.0).
    try:
        numeric = float(text)
        if numeric.is_integer():
            return str(int(numeric))
    except (ValueError, OverflowError):
        pass

    return text


def order_accounts_parent_first(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize account codes and order parent accounts before children."""
    required = {"account_code", "parent_code"}
    if not required.issubset(df.columns):
        raise ValueError("dim_account must contain account_code and parent_code")

    frame = df.copy()
    frame["account_code"] = frame["account_code"].map(normalise_account_code)
    frame["parent_code"] = frame["parent_code"].map(normalise_account_code)
    # Ensure normalized missing parents are actual None values, not NaN/NA.
    frame["parent_code"] = frame["parent_code"].where(
        frame["parent_code"].notna(), None
    ).astype(object)

    if frame["account_code"].isna().any():
        raise ValueError("dim_account contains a blank account_code")

    if frame["account_code"].duplicated().any():
        duplicates = frame.loc[
            frame["account_code"].duplicated(), "account_code"
        ].tolist()
        raise ValueError(f"Duplicate account_code values: {duplicates}")

    by_code = {
        row["account_code"]: row
        for row in frame.to_dict("records")
    }
    pending = dict(by_code)
    ordered = []
    loaded = set()

    while pending:
        ready = []
        for code, row in pending.items():
            parent = row["parent_code"]

            # DataFrame/record conversion can turn None back into float NaN.
            # Treat every pandas-style missing scalar as a root account parent.
            if is_missing(parent) or parent is None:
                row["parent_code"] = None
                ready.append(code)
            elif parent not in by_code:
                raise ValueError(
                    f"Account {code} references missing parent account {parent}"
                )
            elif parent in loaded:
                ready.append(code)

        if not ready:
            raise ValueError(
                "dim_account has a cyclic parent hierarchy involving: "
                + ", ".join(pending.keys())
            )

        for code in ready:
            ordered.append(pending.pop(code))
            loaded.add(code)

    return pd.DataFrame(ordered, columns=frame.columns)


def prepare_frame(
    workbook: pd.ExcelFile, table_name: str, target_columns: list[str]
) -> pd.DataFrame:
    if table_name not in workbook.sheet_names:
        raise ValueError(f"Workbook is missing required sheet: {table_name}")

    frame = pd.read_excel(workbook, sheet_name=table_name)
    source_columns = list(frame.columns)
    if set(source_columns) != set(target_columns):
        missing = sorted(set(target_columns) - set(source_columns))
        extra = sorted(set(source_columns) - set(target_columns))
        raise ValueError(
            f"Column mismatch for {table_name}; missing={missing}, extra={extra}"
        )

    return frame[target_columns].copy()


def extend_date_dimension(frame: pd.DataFrame) -> pd.DataFrame:
    """Extend the calendar through March 2027, preserving workbook dates.

    The workbook does not provide a future holiday calendar. For generated dates,
    is_holiday and weekday is_working_day are NULL rather than guessed.
    """
    existing_dates = set(pd.to_datetime(frame["date"]).dt.date)
    rows = []
    current = date(2027, 1, 1)
    end = date(2027, 3, 31)

    while current <= end:
        if current not in existing_dates:
            month_start = current.replace(day=1)
            month_end = current.replace(
                day=monthrange(current.year, current.month)[1]
            )
            fiscal_start = (
                current.year if current.month >= 4 else current.year - 1
            )
            fiscal_month = (current.month - 4) % 12 + 1
            weekend = current.weekday() >= 5

            rows.append(
                {
                    "date": current,
                    "date_key": int(current.strftime("%Y%m%d")),
                    "year": current.year,
                    "quarter": (current.month - 1) // 3 + 1,
                    "month_number": current.month,
                    "month_name": current.strftime("%B"),
                    "year_month": current.strftime("%Y-%m"),
                    "week_of_year": current.isocalendar().week,
                    "day_of_week": current.strftime("%A"),
                    "is_weekend": "Y" if weekend else "N",
                    "is_holiday": None,
                    "is_working_day": "N" if weekend else None,
                    "financial_year": (
                        f"FY{fiscal_start}-{str(fiscal_start + 1)[-2:]}"
                    ),
                    "fiscal_quarter": f"Q{(fiscal_month - 1) // 3 + 1}",
                    "fiscal_month_number": fiscal_month,
                    "is_month_end": "Y" if current == month_end else "N",
                    "month_start_date": month_start,
                    "month_end_date": month_end,
                }
            )
        current += timedelta(days=1)

    if rows:
        frame = pd.concat(
            [frame, pd.DataFrame(rows, columns=frame.columns)],
            ignore_index=True,
        )

    if frame["date_key"].duplicated().any():
        duplicates = frame.loc[
            frame["date_key"].duplicated(), "date_key"
        ].tolist()
        raise ValueError(f"Duplicate date_key values after extension: {duplicates}")

    return frame


def add_special_dimension_rows(
    frame: pd.DataFrame, table_name: str
) -> pd.DataFrame:
    """Add explicit special members required by source fact foreign keys."""
    if table_name == "dim_department":
        if "ALL" not in set(frame["department_id"].astype(str)):
            row = {
                "department_id": "ALL",
                "department_name": "All Departments",
                "cost_center": None,
                "description": (
                    "Organization-wide forecast aggregate; "
                    "not a cost-center department"
                ),
                "is_leadership": "N",
            }
            frame = pd.concat(
                [frame, pd.DataFrame([row], columns=frame.columns)],
                ignore_index=True,
            )

    elif table_name == "dim_employee":
        if -1 not in set(pd.to_numeric(frame["employee_key"], errors="coerce")):
            row = {
                "employee_key": -1,
                "employee_id": "__UNKNOWN__",
                "full_name": "Unknown Employee",
                "gender": None,
                "date_of_birth": None,
                "hire_date": None,
                "exit_date": None,
                "employment_status": "Unknown",
                "employment_type": None,
                "department_id": "D01",
                "role_id": "R006",
                "role_title": "Unknown Employee",
                "job_level": None,
                "manager_id": None,
                "work_location": "Bengaluru",
                "work_mode": None,
                "highest_education": None,
                "valid_from": date(1900, 1, 1),
                "valid_to": None,
                "is_current": False,
                "change_reason": (
                    "Unknown employee key for unresolved source payroll records"
                ),
            }
            frame = pd.concat(
                [frame, pd.DataFrame([row], columns=frame.columns)],
                ignore_index=True,
            )

    return frame


def validate_special_references(workbook: pd.ExcelFile) -> None:
    """Fail early if source references required by the special members are absent."""
    departments = pd.read_excel(workbook, sheet_name="dim_department")
    roles = pd.read_excel(workbook, sheet_name="dim_role")
    locations = pd.read_excel(workbook, sheet_name="dim_location")

    if not {"D01", "D09"}.issubset(set(departments["department_id"].astype(str))):
        raise ValueError("Required departments D01 and D09 are missing.")
    if not {"R006", "R053"}.issubset(set(roles["role_id"].astype(str))):
        raise ValueError("Required roles R006 and R053 are missing.")
    if "Bengaluru" not in set(locations["work_location"].astype(str)):
        raise ValueError("Required location Bengaluru is missing.")

    payroll = pd.read_excel(workbook, sheet_name="fact_payroll")
    if "employee_key" not in payroll.columns:
        raise ValueError("fact_payroll is missing employee_key.")
    if not (pd.to_numeric(payroll["employee_key"], errors="coerce") == -1).any():
        print("Note: no payroll rows currently require the unknown employee member.")

    forecast = pd.read_excel(workbook, sheet_name="fact_forecast")
    required_dates = {20270131, 20270228, 20270331}
    found_dates = set(
        pd.to_numeric(forecast["forecast_month_key"], errors="coerce")
        .dropna()
        .astype(int)
    )
    if not required_dates.issubset(found_dates):
        raise ValueError(
            "Expected 2027 forecast month-end keys are missing from fact_forecast."
        )


def insert_table(
    cur, workbook: pd.ExcelFile, table_name: str
) -> tuple[int, int]:
    metadata, pk_columns = get_table_metadata(cur, table_name)
    target_columns = [row[0] for row in metadata]
    pg_types = {row[0]: row[1] for row in metadata}

    frame = prepare_frame(workbook, table_name, target_columns)
    source_count = len(frame)

    if table_name == "dim_date":
        frame = extend_date_dimension(frame)

    if table_name in {"dim_department", "dim_employee"}:
        frame = add_special_dimension_rows(frame, table_name)

    if table_name == "dim_account":
        frame = order_accounts_parent_first(frame)

    # The workbook stores fact_forecast.trained_through as a month label
    # such as "2026-09", while PostgreSQL expects a DATE. Represent the
    # training cutoff as the final calendar day of that month.
    if table_name == "fact_forecast" and "trained_through" in frame.columns:
        training_months = pd.to_datetime(
            frame["trained_through"].astype("string").str.strip(),
            format="%Y-%m",
            errors="coerce",
        )
        invalid_training_months = frame["trained_through"].notna() & training_months.isna()
        if invalid_training_months.any():
            invalid_values = frame.loc[invalid_training_months, "trained_through"].astype(str).unique().tolist()
            raise ValueError(
                "Invalid fact_forecast.trained_through month values: "
                + ", ".join(invalid_values)
            )
        frame["trained_through"] = (
            training_months.dt.to_period("M").dt.to_timestamp("M").dt.date
        )

    if frame.empty:
        return source_count, 0

    columns_sql = sql.SQL(", ").join(map(sql.Identifier, target_columns))
    table_sql = sql.SQL("{}.{}").format(
        sql.Identifier("dw"), sql.Identifier(table_name)
    )
    pk_sql = sql.SQL(", ").join(map(sql.Identifier, pk_columns))
    non_pk = [column for column in target_columns if column not in pk_columns]

    if non_pk:
        update_sql = sql.SQL(", ").join(
            sql.SQL("{} = EXCLUDED.{}").format(
                sql.Identifier(column), sql.Identifier(column)
            )
            for column in non_pk
        )
        conflict_sql = sql.SQL("ON CONFLICT ({}) DO UPDATE SET {}").format(
            pk_sql, update_sql
        )
    else:
        conflict_sql = sql.SQL("ON CONFLICT ({}) DO NOTHING").format(pk_sql)

    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}) {}").format(
        table_sql,
        columns_sql,
        sql.SQL(", ").join(sql.Placeholder() for _ in target_columns),
        conflict_sql,
    )

    rows = [
        tuple(normalise_value(row[column], pg_types[column]) for column in target_columns)
        for row in frame.to_dict("records")
    ]

    execute_batch(
        cur, statement.as_string(cur.connection), rows, page_size=500
    )
    return source_count, len(rows)


def main() -> None:
    if not WORKBOOK.exists():
        raise FileNotFoundError(f"Workbook not found: {WORKBOOK}")

    workbook = pd.ExcelFile(WORKBOOK)
    validate_special_references(workbook)

    print(f"Workbook: {WORKBOOK}")
    print(f"Loading {len(TABLE_ORDER)} warehouse tables into dw ...")
    print("Special members: unknown employee (-1), aggregate department (ALL)")
    print("Date dimension will be extended through 2027-03-31.")

    results = []
    # Any error rolls back all inserts/upserts in this transaction.
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            for table_name in TABLE_ORDER:
                source_count, processed_count = insert_table(
                    cur, workbook, table_name
                )
                results.append((table_name, source_count, processed_count))
                print(
                    f"dw.{table_name}: source={source_count:,}, "
                    f"processed={processed_count:,}"
                )

    print("\nWAREHOUSE LOAD COMMITTED")
    print(f"Tables processed: {len(results)}")
    print(f"Total workbook source rows: {sum(row[1] for row in results):,}")
    print(
        "Note: processed counts include 1 unknown employee, "
        "1 aggregate department, and 90 generated calendar dates."
    )
    print("Run post-load row counts and reconciliation queries next.")


if __name__ == "__main__":
    main()
