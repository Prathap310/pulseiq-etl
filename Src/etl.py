
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
OUTPUT_DIR = DATA_DIR / "Clean"
REJECTED_DIR = DATA_DIR / "Rejected"
LOG_DIR = PROJECT_DIR / os.getenv("LOG_DIR", "Logs")

for directory in (RAW_DIR, OUTPUT_DIR, REJECTED_DIR, LOG_DIR):
    directory.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. LOGGING CONFIGURATION
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
# 3. REQUIRED EMPLOYEE COLUMNS
# ============================================================

REQUIRED_COLUMNS = [
    "employee_id",
    "employee_name",
    "department",
    "salary",
    "city",
]


# ============================================================
# 4. PANDERA DATA VALIDATION SCHEMA
# ============================================================

employee_schema = pa.DataFrameSchema(
    {
        "employee_id": pa.Column(
            int,
            nullable=False,
            coerce=True,
            checks=pa.Check.ge(1),
        ),
        "employee_name": pa.Column(
            str,
            nullable=False,
            coerce=True,
            checks=pa.Check.str_length(min_value=1),
        ),
        "department": pa.Column(
            str,
            nullable=False,
            coerce=True,
            checks=pa.Check.str_length(min_value=1),
        ),
        "salary": pa.Column(
            float,
            nullable=False,
            coerce=True,
            checks=pa.Check.gt(0),
        ),
        "city": pa.Column(
            str,
            nullable=False,
            coerce=True,
            checks=pa.Check.str_length(min_value=1),
        ),
    },
    strict=False,
)


# ============================================================
# 5. STANDARDIZE COLUMN NAMES
# ============================================================

def standardize_columns(df):
    df = df.copy()

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

    return df


# ============================================================
# 6. TRANSFORM AND CLEAN DATA
# ============================================================

def transform_data(df):
    df = standardize_columns(df)

    # Remove exact duplicate records.
    df = df.drop_duplicates().copy()

    # Standardize text fields when present.
    text_columns = [
        "employee_name",
        "department",
        "city",
    ]

    for column in text_columns:
        if column in df.columns:
            df[column] = df[column].map(
                lambda value: value.strip()
                if isinstance(value, str)
                else value
            )

    # Remove missing values from required columns
    # that exist in the supplied DataFrame.
    existing_required = [
        column
        for column in REQUIRED_COLUMNS
        if column in df.columns
    ]

    if existing_required:
        df = df.dropna(subset=existing_required).copy()

    # Remove blank text values.
    for column in text_columns:
        if column in df.columns:
            df = df[
                df[column].map(
                    lambda value: (
                        not isinstance(value, str)
                        or bool(value.strip())
                    )
                )
            ].copy()

    # Validate employee IDs when available.
    if "employee_id" in df.columns:
        numeric_ids = pd.to_numeric(
            df["employee_id"], errors="coerce"
        )

        valid_ids = (
            numeric_ids.notna()
            & numeric_ids.ge(1)
            & numeric_ids.mod(1).eq(0)
        )

        df = df.loc[valid_ids].copy()
        df["employee_id"] = numeric_ids.loc[valid_ids].astype(int)

    # Convert salary to numeric and remove invalid salaries.
    if "salary" in df.columns:
        numeric_salary = pd.to_numeric(
            df["salary"], errors="coerce"
        )

        valid_salary = (
            numeric_salary.notna()
            & numeric_salary.gt(0)
        )

        df = df.loc[valid_salary].copy()
        df["salary"] = numeric_salary.loc[valid_salary]

    return df.reset_index(drop=True)


# ============================================================
# 7. IDENTIFY INVALID RECORDS
# ============================================================

def get_rejection_reason(row):
    # Check missing or blank required fields.
    for column in REQUIRED_COLUMNS:
        if column not in row.index:
            return f"Missing required column: {column}"

        value = row[column]

        if pd.isna(value):
            return f"Missing {column.replace('_', ' ')}"

        if isinstance(value, str) and not value.strip():
            return f"Missing {column.replace('_', ' ')}"

    # Validate employee ID.
    try:
        employee_id = float(row["employee_id"])

        if (
            not pd.notna(employee_id)
            or employee_id < 1
            or not employee_id.is_integer()
        ):
            return "Invalid employee ID"

    except (ValueError, TypeError, OverflowError):
        return "Invalid employee ID"

    # Validate salary.
    try:
        salary = float(row["salary"])

        if not pd.notna(salary) or salary <= 0:
            return "Invalid salary"

    except (ValueError, TypeError, OverflowError):
        return "Invalid salary"

    return None


# ============================================================
# 8. PROCESS ONE CSV FILE
# ============================================================

def process_file(file_path):
    logger.info("Starting file: %s", file_path.name)

    # Read raw CSV data.
    df = pd.read_csv(file_path)

    # Standardize column names before checking required fields.
    df = standardize_columns(df)

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # Remove exact duplicates before validation.
    df = df.drop_duplicates().copy()

    # Split valid and rejected records.
    valid_records = []
    rejected_records = []

    for _, row in df.iterrows():
        reason = get_rejection_reason(row)

        if reason is None:
            valid_records.append(row.to_dict())
        else:
            rejected_row = row.to_dict()
            rejected_row["rejection_reason"] = reason
            rejected_records.append(rejected_row)

    valid_df = pd.DataFrame(
        valid_records,
        columns=REQUIRED_COLUMNS,
    )

    rejected_df = pd.DataFrame(
        rejected_records,
        columns=list(df.columns) + ["rejection_reason"],
    )

    # Apply transformations to valid records.
    cleaned_df = transform_data(valid_df)

    # Validate cleaned records using Pandera.
    if not cleaned_df.empty:
        cleaned_df = employee_schema.validate(
            cleaned_df,
            lazy=True,
        )

    # Write cleaned output.
    cleaned_path = OUTPUT_DIR / (
        f"{file_path.stem}_cleaned.csv"
    )

    cleaned_df.to_csv(cleaned_path, index=False)

    # Write rejected output.
    rejected_path = REJECTED_DIR / (
        f"{file_path.stem}_rejected.csv"
    )

    rejected_df.to_csv(rejected_path, index=False)

    # Log results.
    logger.info(
        "%s: %d valid, %d rejected",
        file_path.name,
        len(cleaned_df),
        len(rejected_df),
    )

    print(
        f"{file_path.name}: "
        f"{len(cleaned_df)} valid, "
        f"{len(rejected_df)} rejected"
    )

    print(f"Cleaned file: {cleaned_path}")
    print(f"Rejected file: {rejected_path}")

    return {
        "file": file_path.name,
        "valid": len(cleaned_df),
        "rejected": len(rejected_df),
        "cleaned_path": str(cleaned_path),
        "rejected_path": str(rejected_path),
    }


# ============================================================
# 9. RUN THE ETL PROCESS FOR ALL RAW CSV FILES
# ============================================================

def main():
    files = sorted(RAW_DIR.glob("*.csv"))

    if not files:
        print(f"No CSV files found in {RAW_DIR}")
        logger.warning("No raw CSV files found.")
        return

    total_valid = 0
    total_rejected = 0

    for file_path in files:
        try:
            result = process_file(file_path)

            total_valid += result["valid"]
            total_rejected += result["rejected"]

        except Exception:
            logger.exception(
                "Failed to process %s",
                file_path.name,
            )

            print(
                f"Failed to process {file_path.name}. "
                "Check Logs/etl.log"
            )

    print("\n" + "=" * 45)
    print("PULSEIQ-ETL PROCESSING SUMMARY")
    print("=" * 45)
    print(f"Valid records: {total_valid}")
    print(f"Rejected records: {total_rejected}")
    print("ETL processing finished.")
    print(f"Log file: {LOG_DIR / 'etl.log'}")


if __name__ == "__main__":
    main()
