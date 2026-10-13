import logging
import os
from pathlib import Path

import pandas as pd
import pandera.pandas as pa
from dotenv import load_dotenv


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

DATA_DIR = PROJECT_DIR / os.getenv("DATA_DIR", "Data")
RAW_DIR = DATA_DIR / "Raw"
CLEAN_DIR = DATA_DIR / "Clean"
REJECTED_DIR = DATA_DIR / "Rejected"
LOG_DIR = PROJECT_DIR / os.getenv("LOG_DIR", "Logs")

for folder in (RAW_DIR, CLEAN_DIR, REJECTED_DIR, LOG_DIR):
    folder.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "etl.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
    force=True,
)
logger = logging.getLogger(__name__)


# ============================================================
# 3. EMPLOYEE DATA RULES
# ============================================================

EMPLOYEE_REQUIRED = [
    "employee_id",
    "employee_name",
    "department",
    "salary",
    "city",
]

employee_schema = pa.DataFrameSchema(
    {
        "employee_id": pa.Column(
            int, nullable=False, coerce=True, checks=pa.Check.ge(1)
        ),
        "employee_name": pa.Column(
            str, nullable=False, coerce=True,
            checks=pa.Check.str_length(min_value=1),
        ),
        "department": pa.Column(
            str, nullable=False, coerce=True,
            checks=pa.Check.str_length(min_value=1),
        ),
        "salary": pa.Column(
            float, nullable=False, coerce=True, checks=pa.Check.gt(0)
        ),
        "city": pa.Column(
            str, nullable=False, coerce=True,
            checks=pa.Check.str_length(min_value=1),
        ),
    },
    strict=False,
)


# ============================================================
# 4. PAYROLL DATA RULES
# ============================================================

PAYROLL_REQUIRED = [
    "payroll_item_id", "run_id", "employee_id", "date_key",
    "employee_key", "period_end_date", "department_id", "role_id",
    "payable_days", "lop_days", "overtime_hours_paid",
    "monthly_fixed_gross", "basic", "hra", "conveyance", "medical",
    "special_allowance", "earned_fixed_pay", "overtime_pay",
    "variable_pay", "gross_pay", "pf_employee", "esi_employee",
    "professional_tax", "tds", "other_deductions", "total_deductions",
    "net_pay", "pf_employer", "esi_employer", "employer_cost",
    "headcount_flag",
]

PAYROLL_NUMERIC_COLUMNS = [
    "employee_key", "payable_days", "lop_days", "overtime_hours_paid",
    "monthly_fixed_gross", "basic", "hra", "conveyance", "medical",
    "special_allowance", "earned_fixed_pay", "overtime_pay",
    "variable_pay", "gross_pay", "pf_employee", "esi_employee",
    "professional_tax", "tds", "other_deductions", "total_deductions",
    "net_pay", "pf_employer", "esi_employer", "employer_cost",
    "headcount_flag",
]

PAYROLL_NONNEGATIVE_COLUMNS = [
    "payable_days", "lop_days", "overtime_hours_paid",
    "monthly_fixed_gross", "basic", "hra", "conveyance", "medical",
    "special_allowance", "earned_fixed_pay", "overtime_pay",
    "variable_pay", "gross_pay", "pf_employee", "esi_employee",
    "professional_tax", "tds", "other_deductions", "total_deductions",
    "net_pay", "pf_employer", "esi_employer", "employer_cost",
]


# ============================================================
# 5. ATTENDANCE DATA RULES (NEW)
# ============================================================

ATTENDANCE_REQUIRED = [
    "attendance_fact_id",
    "employee_id",
    "date_key",
    "employee_key",
    "department_id",
    "scheduled_days",
    "present_days",
    "wfh_days",
    "half_days_unpaid",
    "paid_leave_days",
    "unpaid_absence_days",
    "late_arrivals",
    "avg_hours_worked",
    "overtime_hours",
    "attendance_rate",
    "period_end_date",
]

ATTENDANCE_NUMERIC_COLUMNS = [
    "employee_key",
    "scheduled_days",
    "present_days",
    "wfh_days",
    "half_days_unpaid",
    "paid_leave_days",
    "unpaid_absence_days",
    "late_arrivals",
    "avg_hours_worked",
    "overtime_hours",
    "attendance_rate",
]

ATTENDANCE_NONNEGATIVE_COLUMNS = [
    "scheduled_days",
    "present_days",
    "wfh_days",
    "half_days_unpaid",
    "paid_leave_days",
    "unpaid_absence_days",
    "late_arrivals",
    "avg_hours_worked",
    "overtime_hours",
]


# ============================================================
# 6. SHARED HELPERS
# ============================================================

def transform_data(df):
    """Compatibility transformation used by the unit tests.

    Standardizes column names, removes exact duplicate rows, and removes rows
    containing missing values. This helper is independent of the dataset-specific
    employee, payroll, and attendance processors below.
    """
    result = df.copy()
    result.columns = (
        result.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace(r"[^a-z0-9_]", "", regex=True)
    )
    result = result.drop_duplicates()
    result = result.dropna()
    return result


def standardize_columns(df):
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )
    return df


def missing_value(value):
    return pd.isna(value) or (
        isinstance(value, str) and not value.strip()
    )


def write_outputs(clean_df, rejected_df, source_path, input_count=None):
    clean_path = CLEAN_DIR / f"{source_path.stem}_cleaned.csv"
    rejected_path = REJECTED_DIR / f"{source_path.stem}_rejected.csv"

    clean_df.to_csv(clean_path, index=False)
    rejected_df.to_csv(rejected_path, index=False)

    if input_count is None:
        input_count = len(clean_df) + len(rejected_df)

    logger.info(
        "%s: input=%d, clean=%d, rejected=%d",
        source_path.name, input_count, len(clean_df), len(rejected_df),
    )

    print(
        f"{source_path.name}: input={input_count}, "
        f"{len(clean_df)} clean, {len(rejected_df)} rejected"
    )
    print(f"Clean output: {clean_path}")
    print(f"Rejected output: {rejected_path}")

    return {
        "file": source_path.name,
        "valid": len(clean_df),
        "rejected": len(rejected_df),
        "input": input_count,
    }


def empty_rejected(columns):
    return pd.DataFrame(columns=list(columns) + ["rejection_reason"])


# ============================================================
# 7. EMPLOYEE PROCESSOR
# ============================================================

def process_employees(source_path):
    df = standardize_columns(pd.read_csv(source_path, low_memory=False))
    input_count = len(df)

    missing = [c for c in EMPLOYEE_REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing employee columns: {missing}")

    # Remove exact duplicate records and log the reduction.
    df = df.drop_duplicates().copy()
    rejected = []
    rejected_indexes = set()

    for index, row in df.iterrows():
        reasons = []
        for column in EMPLOYEE_REQUIRED:
            if missing_value(row[column]):
                reasons.append(f"Missing {column}")

        employee_id = pd.to_numeric(
            pd.Series([row["employee_id"]]), errors="coerce"
        ).iloc[0]
        salary = pd.to_numeric(
            pd.Series([row["salary"]]), errors="coerce"
        ).iloc[0]

        if pd.isna(employee_id) or employee_id < 1 or float(employee_id) % 1 != 0:
            reasons.append("Invalid employee ID")
        if pd.isna(salary) or salary <= 0:
            reasons.append("Invalid salary")

        if reasons:
            record = row.to_dict()
            record["rejection_reason"] = "; ".join(dict.fromkeys(reasons))
            rejected.append(record)
            rejected_indexes.add(index)

    clean_df = df.loc[~df.index.isin(rejected_indexes)].copy()
    rejected_df = pd.DataFrame(rejected) if rejected else empty_rejected(df.columns)

    if not clean_df.empty:
        clean_df["employee_id"] = pd.to_numeric(
            clean_df["employee_id"], errors="raise"
        ).astype(int)
        clean_df["salary"] = pd.to_numeric(
            clean_df["salary"], errors="raise"
        ).astype(float)
        for column in ["employee_name", "department", "city"]:
            clean_df[column] = clean_df[column].astype(str).str.strip()
        clean_df = employee_schema.validate(clean_df, lazy=True)

    return write_outputs(clean_df, rejected_df, source_path, input_count)


# ============================================================
# 8. PAYROLL PROCESSOR
# ============================================================

def process_payroll(source_path):
    df = standardize_columns(pd.read_csv(source_path, low_memory=False))
    input_count = len(df)

    missing = [c for c in PAYROLL_REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing payroll columns: {missing}")

    df = df.drop_duplicates().copy()
    for column in [
        "payroll_item_id", "run_id", "employee_id", "department_id", "role_id"
    ]:
        df[column] = df[column].astype("string").str.strip()

    df["period_end_date"] = pd.to_datetime(
        df["period_end_date"], errors="coerce"
    )
    for column in PAYROLL_NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    duplicate_id = df["payroll_item_id"].duplicated(keep=False)
    # DQ rule: an employee should have at most one row per payroll run.
    duplicate_employee_run = df.duplicated(
        subset=["employee_id", "run_id"], keep=False
    )

    rejected = []
    rejected_indexes = set()

    for index, row in df.iterrows():
        reasons = []
        for column in [
            "payroll_item_id", "run_id", "employee_id", "date_key",
            "period_end_date", "department_id", "role_id",
        ]:
            if missing_value(row[column]):
                reasons.append(f"Missing or invalid {column}")

        for column in PAYROLL_NUMERIC_COLUMNS:
            if pd.isna(row[column]):
                reasons.append(f"Missing or invalid {column}")

        if bool(duplicate_id.loc[index]):
            reasons.append("Duplicate payroll_item_id")
        if bool(duplicate_employee_run.loc[index]):
            reasons.append("Duplicate employee_id/run_id combination")

        for column in PAYROLL_NONNEGATIVE_COLUMNS:
            if pd.notna(row[column]) and row[column] < 0:
                reasons.append(f"Negative value in {column}")

        if pd.notna(row["payable_days"]) and row["payable_days"] > 31:
            reasons.append("payable_days exceeds 31")
        if pd.notna(row["lop_days"]) and row["lop_days"] > 31:
            reasons.append("lop_days exceeds 31")
        if pd.notna(row["headcount_flag"]) and row["headcount_flag"] not in (0, 1):
            reasons.append("headcount_flag must be 0 or 1")

        if all(pd.notna(row[c]) for c in ["gross_pay", "total_deductions", "net_pay"]):
            expected_net = row["gross_pay"] - row["total_deductions"]
            if abs(expected_net - row["net_pay"]) >= 0.02:
                reasons.append("Net pay calculation mismatch")

        if reasons:
            record = row.to_dict()
            record["rejection_reason"] = "; ".join(dict.fromkeys(reasons))
            rejected.append(record)
            rejected_indexes.add(index)

    clean_df = df.loc[~df.index.isin(rejected_indexes)].copy()
    rejected_df = pd.DataFrame(rejected) if rejected else empty_rejected(df.columns)

    if "variable_pay_type" in clean_df.columns:
        clean_df["variable_pay_type"] = (
            clean_df["variable_pay_type"].fillna("").astype(str).str.strip()
        )

    return write_outputs(clean_df, rejected_df, source_path, input_count)


# ============================================================
# 9. ATTENDANCE PROCESSOR (NEW)
# ============================================================

def process_attendance(source_path):
    df = standardize_columns(pd.read_csv(source_path, low_memory=False))
    input_count = len(df)

    missing = [c for c in ATTENDANCE_REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing attendance columns: {missing}")

    df = df.drop_duplicates().copy()

    # Keep IDs as text to preserve identifiers such as EMP-0002.
    for column in ["attendance_fact_id", "employee_id", "department_id"]:
        df[column] = df[column].astype("string").str.strip()

    df["period_end_date"] = pd.to_datetime(
        df["period_end_date"], errors="coerce"
    )

    for column in ATTENDANCE_NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    duplicate_fact_id = df["attendance_fact_id"].duplicated(keep=False)
    rejected = []
    rejected_indexes = set()

    for index, row in df.iterrows():
        reasons = []

        for column in [
            "attendance_fact_id", "employee_id", "date_key",
            "employee_key", "department_id", "period_end_date",
        ]:
            if missing_value(row[column]):
                reasons.append(f"Missing or invalid {column}")

        for column in ATTENDANCE_NUMERIC_COLUMNS:
            if pd.isna(row[column]):
                reasons.append(f"Missing or invalid {column}")

        if bool(duplicate_fact_id.loc[index]):
            reasons.append("Duplicate attendance_fact_id")

        for column in ATTENDANCE_NONNEGATIVE_COLUMNS:
            if pd.notna(row[column]) and row[column] < 0:
                reasons.append(f"Negative value in {column}")

        # Attendance counts should not exceed the scheduled workdays.
        if pd.notna(row["scheduled_days"]) and row["scheduled_days"] > 31:
            reasons.append("scheduled_days exceeds 31")

        if (
            pd.notna(row["scheduled_days"])
            and pd.notna(row["present_days"])
            and row["present_days"] > row["scheduled_days"]
        ):
            reasons.append("present_days exceeds scheduled_days")

        if (
            pd.notna(row["scheduled_days"])
            and pd.notna(row["wfh_days"])
            and row["wfh_days"] > row["scheduled_days"]
        ):
            reasons.append("wfh_days exceeds scheduled_days")

        if (
            pd.notna(row["attendance_rate"])
            and not 0 <= row["attendance_rate"] <= 1
        ):
            reasons.append("attendance_rate must be between 0 and 1")

        if (
            pd.notna(row["avg_hours_worked"])
            and row["avg_hours_worked"] > 24
        ):
            reasons.append("avg_hours_worked exceeds 24")

        if (
            pd.notna(row["date_key"])
            and pd.notna(row["period_end_date"])
            and str(int(row["date_key"])) != row["period_end_date"].strftime("%Y%m%d")
        ):
            reasons.append("date_key does not match period_end_date")

        if reasons:
            record = row.to_dict()
            record["rejection_reason"] = "; ".join(dict.fromkeys(reasons))
            rejected.append(record)
            rejected_indexes.add(index)

    clean_df = df.loc[~df.index.isin(rejected_indexes)].copy()
    rejected_df = pd.DataFrame(rejected) if rejected else empty_rejected(df.columns)

    # Normalize output date and numeric types.
    if not clean_df.empty:
        clean_df["period_end_date"] = clean_df["period_end_date"].dt.strftime("%Y-%m-%d")
        clean_df["date_key"] = pd.to_numeric(clean_df["date_key"]).astype("int64")
        clean_df["employee_key"] = pd.to_numeric(
            clean_df["employee_key"]
        ).astype("int64")
        for column in ATTENDANCE_NUMERIC_COLUMNS:
            if column not in ("employee_key",):
                clean_df[column] = pd.to_numeric(clean_df[column])

    return write_outputs(clean_df, rejected_df, source_path, input_count)


# ============================================================
# 10. GENERAL DATASET PROCESSOR + DATA-QUALITY RULES
# ============================================================

def process_general_dataset(source_path):
    """Process datasets without a dedicated schema-specific processor.

    Keeps optional blanks, removes column-name formatting differences, and
    sends duplicate copies and known business-rule violations to Rejected.
    """
    df = standardize_columns(pd.read_csv(source_path, low_memory=False))
    input_count = len(df)

    # Empty files still produce consistent clean/rejected outputs.
    if len(df.columns) == 0:
        raise ValueError(f"No columns found in {source_path.name}")

    # Preserve one copy of exact duplicate records and reject subsequent copies.
    duplicate_rows = df.duplicated(keep="first")
    reasons_by_index = {idx: ["Exact duplicate row"] for idx in df.index[duplicate_rows]}

    def reject_where(mask, reason):
        for idx in df.index[mask.fillna(False)]:
            reasons_by_index.setdefault(idx, []).append(reason)

    # Convert only the columns needed by each rule; optional blanks remain valid.
    name = source_path.name.lower()
    if name == "fact_leave.csv":
        start = pd.to_datetime(df.get("start_date"), errors="coerce")
        end = pd.to_datetime(df.get("end_date"), errors="coerce")
        reject_where(start.notna() & end.notna() & (end < start),
                     "end_date is before start_date (DQ-C10)")
        days = pd.to_numeric(df.get("days"), errors="coerce")
        reject_where(days.notna() & (days < 0), "days cannot be negative")
    elif name == "fact_invoice.csv":
        paid = pd.to_numeric(df.get("amount_paid"), errors="coerce")
        total = pd.to_numeric(df.get("total_amount"), errors="coerce")
        balance = pd.to_numeric(df.get("balance_due"), errors="coerce")
        reject_where(paid.notna() & total.notna() & (paid > total + 0.01),
                     "amount_paid exceeds total_amount (DQ-C07)")
        reject_where(balance.notna() & (balance < -0.01),
                     "balance_due is negative (DQ-C07)")
    elif name == "fact_expense.csv":
        excl = pd.to_numeric(df.get("amount_excl_gst"), errors="coerce")
        gst = pd.to_numeric(df.get("gst_amount"), errors="coerce")
        total = pd.to_numeric(df.get("total_amount"), errors="coerce")
        reject_where(excl.notna() & gst.notna() & total.notna() &
                     ((total - excl - gst).abs() > 0.01),
                     "total_amount differs from amount_excl_gst + gst_amount (DQ-C08)")
    elif name == "fact_task.csv":
        started = pd.to_datetime(df.get("started_date"), errors="coerce")
        completed = pd.to_datetime(df.get("completed_date"), errors="coerce")
        status = df.get("status", pd.Series("", index=df.index)).astype("string").str.strip().str.lower()
        reject_where(started.notna() & completed.notna() & (completed < started),
                     "completed_date is before started_date (DQ-C09)")
        reject_where(status.eq("done") & completed.isna(),
                     "Done task has no completed_date (DQ-C09)")
    elif name == "fact_ledger.csv":
        if {"entry_id", "debit", "credit"}.issubset(df.columns):
            debit = pd.to_numeric(df["debit"], errors="coerce")
            credit = pd.to_numeric(df["credit"], errors="coerce")
            ledger = pd.DataFrame({"entry_id": df["entry_id"], "debit": debit, "credit": credit})
            ledger["difference"] = ledger["debit"].fillna(0) - ledger["credit"].fillna(0)
            entry_difference = ledger.groupby("entry_id", dropna=False)["difference"].transform("sum").abs()
            reject_where(entry_difference > 0.005, "entry_id is not balanced (DQ-C02)")
    elif name == "fact_attrition_risk.csv":
        score = pd.to_numeric(df.get("risk_score_12m"), errors="coerce")
        reject_where(score.notna() & ((score < 0) | (score > 1)),
                     "risk_score_12m must be between 0 and 1")
    elif name == "fact_anomaly.csv":
        score = pd.to_numeric(df.get("anomaly_score"), errors="coerce")
        reject_where(score.notna() & ((score < 0) | (score > 1)),
                     "anomaly_score must be between 0 and 1")
    elif name == "fact_headcount_monthly.csv":
        for column in ["headcount_start", "hires", "exits", "voluntary_exits",
                       "transfers_in", "transfers_out", "headcount_end"]:
            if column in df.columns:
                values = pd.to_numeric(df[column], errors="coerce")
                reject_where(values.notna() & (values < 0), f"{column} cannot be negative")

    rejected_indexes = set(reasons_by_index)
    clean_df = df.loc[~df.index.isin(rejected_indexes)].copy()
    if reasons_by_index:
        rejected_df = df.loc[df.index.isin(rejected_indexes)].copy()
        rejected_df["rejection_reason"] = [
            "; ".join(dict.fromkeys(reasons_by_index[idx]))
            for idx in rejected_df.index
        ]
    else:
        rejected_df = empty_rejected(df.columns)

    # Normalize common date columns where they exist; retain original values if
    # a date cannot be parsed, since the data dictionary may define them as text.
    date_columns = [c for c in df.columns if c.endswith("_date") or c in {"date", "month", "forecast_month", "trained_through", "as_of_date"}]
    for column in date_columns:
        parsed = pd.to_datetime(clean_df[column], errors="coerce")
        valid = clean_df[column].notna() & parsed.notna()
        if valid.any():
            clean_df.loc[valid, column] = parsed.loc[valid].dt.strftime("%Y-%m-%d")

    return write_outputs(clean_df, rejected_df, source_path, input_count)


# ============================================================
# 11. DATASET ROUTING
# ============================================================

def main():
    files = sorted(RAW_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {RAW_DIR}")

    total_valid = 0
    total_rejected = 0
    processed = []
    skipped = []
    failed = []

    for source_path in files:
        try:
            header = standardize_columns(pd.read_csv(source_path, nrows=0))
            columns = set(header.columns)

            if set(EMPLOYEE_REQUIRED).issubset(columns):
                result = process_employees(source_path)
            elif set(PAYROLL_REQUIRED).issubset(columns):
                result = process_payroll(source_path)
            elif set(ATTENDANCE_REQUIRED).issubset(columns):
                result = process_attendance(source_path)
            else:
                # All remaining source CSVs receive generic processing plus
                # filename-specific rules where the project defines them.
                result = process_general_dataset(source_path)

            processed.append(result["file"])
            total_valid += result["valid"]
            total_rejected += result["rejected"]

        except Exception:
            failed.append(source_path.name)
            logger.exception("Failed to process %s", source_path.name)
            print(f"FAILED: {source_path.name}. Check Logs/etl.log")

    print("\n" + "=" * 48)
    print("PULSEIQ-ETL SUMMARY")
    print("=" * 48)
    print(f"Raw CSV files discovered: {len(files)}")
    print(f"Datasets processed: {len(processed)}")
    print(f"Datasets not implemented yet: {len(skipped)}")
    print(f"Clean records: {total_valid}")
    print(f"Rejected records: {total_rejected}")
    print(f"Failed datasets: {len(failed)}")
    print(f"Log file: {LOG_DIR / 'etl.log'}")

    if skipped:
        logger.warning("Datasets not implemented yet: %s", ", ".join(skipped))
    if failed:
        raise RuntimeError("ETL failed for: " + ", ".join(failed))


if __name__ == "__main__":
    main()
