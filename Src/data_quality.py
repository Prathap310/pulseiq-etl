
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "Data" / "Raw"
REPORT_DIR = PROJECT_DIR / "Docs"

TOLERANCE = 0.01

# Preserve the columns required by the existing tests.
SUMMARY_COLUMNS = [
    "file",
    "dataset_type",
    "total_rows",
    "total_columns",
    "missing_cells",
    "duplicate_rows",
    "invalid_salary_rows",
    "quality_status",
    "issues_detected",
]


def load_csv(filename):
    """Load a raw CSV, returning None if it is unavailable."""
    path = RAW_DIR / filename
    if not path.exists():
        return None
    return pd.read_csv(path, low_memory=False)


def as_date(series):
    return pd.to_datetime(series, errors="coerce")


def as_number(series):
    return pd.to_numeric(series, errors="coerce")


def profile_file(path):
    """General profiling; business rules are reported separately."""
    df = pd.read_csv(path, low_memory=False)

    missing = int(df.isna().sum().sum())
    duplicates = int(df.duplicated().sum())

    salary_column = next(
        (column for column in df.columns
         if column.lower() == "salary"),
        None,
    )

    invalid_salary = 0
    if salary_column:
        salary = as_number(df[salary_column])
        invalid_salary = int(
            (salary.isna() | (salary <= 0)).sum()
        )

    issues = []
    if missing:
        issues.append("Missing values")
    if duplicates:
        issues.append("Duplicate rows")
    if invalid_salary:
        issues.append("Invalid salary values")
    if df.columns.duplicated().any():
        issues.append("Duplicate column names")
    if any(not str(column).strip() for column in df.columns):
        issues.append("Empty column names")

    return {
        "file": path.name,
        "dataset_type": path.stem.split("_")[0],
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "missing_cells": missing,
        "duplicate_rows": duplicates,
        "invalid_salary_rows": invalid_salary,
        "quality_status": "CHECK" if issues else "PASS",
        "issues_detected": "; ".join(issues),
    }


def record_rule(results, findings, rule_id, rule_name,
                dataset, bad_rows, id_column, description):
    """Save a rule result and the individual affected record IDs."""
    if bad_rows is None:
        bad_rows = pd.DataFrame()

    record_ids = []
    if not bad_rows.empty and id_column in bad_rows.columns:
        record_ids = (
            bad_rows[id_column]
            .dropna()
            .astype(str)
            .drop_duplicates()
            .tolist()
        )

    count = len(bad_rows)

    results.append({
        "rule_id": rule_id,
        "rule_name": rule_name,
        "dataset": dataset,
        "status": "FAIL" if count else "PASS",
        "violation_count": count,
        "affected_ids": "; ".join(record_ids),
        "description": description,
    })

    for _, row in bad_rows.iterrows():
        details = description

        # Include reconciliation values when available.
        if "difference" in row.index:
            details += (
                f" Difference={row['difference']:.2f}"
            )

        findings.append({
            "rule_id": rule_id,
            "rule_name": rule_name,
            "dataset": dataset,
            "record_id": str(row.get(id_column, "")),
            "details": details,
        })


def run_business_rules():
    results = []
    findings = []

    employees = load_csv("dim_employee.csv")
    attendance = load_csv("fact_attendance_monthly.csv")
    payroll = load_csv("fact_payroll.csv")
    ledger = load_csv("fact_ledger.csv")
    invoices = load_csv("fact_invoice.csv")
    tasks = load_csv("fact_task.csv")
    leave = load_csv("fact_leave.csv")
    expenses = load_csv("fact_expense.csv")
    attrition = load_csv("fact_attrition_risk.csv")

    # DQ-01: Attendance period must not be after the employee's
    # exit month. Use the current employee-dimension version.
    if attendance is not None and employees is not None:
        current = employees.copy()

        if "is_current" in current.columns:
            current = current[
                current["is_current"].astype(str).str.upper().eq("Y")
            ]

        current["exit_date_parsed"] = as_date(current["exit_date"])
        current = current.drop_duplicates("employee_id", keep="last")

        exit_map = current.set_index("employee_id")["exit_date_parsed"]

        a = attendance.copy()
        a["period_end_parsed"] = as_date(a["period_end_date"])
        a["employee_exit_date"] = a["employee_id"].map(exit_map)

        # Attendance in the same month as the exit is allowed by
        # the catalog; only a later month is a violation.
        exit_month_end = (
            a["employee_exit_date"] + pd.offsets.MonthEnd(0)
        )

        bad = a[
            a["employee_exit_date"].notna()
            & a["period_end_parsed"].notna()
            & (a["period_end_parsed"] > exit_month_end)
        ]

        record_rule(
            results, findings, "DQ-01",
            "Attendance after exit",
            "fact_attendance_monthly", bad, "attendance_fact_id",
            "Attendance period ends after the employee's exit month."
        )
    else:
        record_rule(
            results, findings, "DQ-01",
            "Attendance after exit",
            "fact_attendance_monthly", None, "attendance_fact_id",
            "Skipped: attendance or employee dimension is missing."
        )

    # DQ-02: One payroll row per employee per run.
    if payroll is not None:
        bad = payroll[
            payroll.duplicated(
                ["employee_id", "run_id"], keep=False
            )
        ]

        record_rule(
            results, findings, "DQ-02",
            "Duplicate payroll employee/run",
            "fact_payroll", bad, "payroll_item_id",
            "employee_id and run_id must be unique together."
        )
    else:
        record_rule(
            results, findings, "DQ-02",
            "Duplicate payroll employee/run",
            "fact_payroll", None, "payroll_item_id",
            "Skipped: payroll dataset is missing."
        )

    # DQ-03: Every payroll employee ID must exist in dim_employee.
    if payroll is not None and employees is not None:
        valid_ids = set(
            employees["employee_id"].dropna().astype(str)
        )

        bad = payroll[
            ~payroll["employee_id"].astype(str).isin(valid_ids)
        ]

        record_rule(
            results, findings, "DQ-03",
            "Payroll orphan employee",
            "fact_payroll", bad, "payroll_item_id",
            "Payroll employee_id does not exist in dim_employee."
        )
    else:
        record_rule(
            results, findings, "DQ-03",
            "Payroll orphan employee",
            "fact_payroll", None, "payroll_item_id",
            "Skipped: payroll or employee dimension is missing."
        )

    # DQ-04: Monthly payroll employer cost must equal the net
    # ledger expense for accounts 5001-5005, within INR 0.01.
    if payroll is not None and ledger is not None:
        p = payroll.copy()
        l = ledger.copy()

        p["month"] = (
            as_date(p["period_end_date"])
            .dt.to_period("M").astype(str)
        )
        p["employer_cost_num"] = as_number(p["employer_cost"])

        l["month"] = (
            as_date(l["entry_date"])
            .dt.to_period("M").astype(str)
        )
        l["account_code"] = l["account_code"].astype(str)
        l["debit_num"] = as_number(l["debit"]).fillna(0)
        l["credit_num"] = as_number(l["credit"]).fillna(0)

        salary_ledger = l[
            l["account_code"].isin(
                ["5001", "5002", "5003", "5004", "5005"]
            )
        ].copy()

        # Use net debits so credit reversals reduce the expense.
        salary_ledger["net_expense"] = (
            salary_ledger["debit_num"]
            - salary_ledger["credit_num"]
        )

        payroll_monthly = (
            p.groupby("month", as_index=False)["employer_cost_num"]
            .sum(min_count=1)
            .rename(columns={
                "employer_cost_num": "payroll_employer_cost"
            })
        )

        ledger_monthly = (
            salary_ledger.groupby("month", as_index=False)["net_expense"]
            .sum()
            .rename(columns={
                "net_expense": "ledger_salary_expense"
            })
        )

        comparison = payroll_monthly.merge(
            ledger_monthly, on="month", how="outer"
        )

        comparison["payroll_employer_cost"] = comparison[
            "payroll_employer_cost"
        ].fillna(0)

        comparison["ledger_salary_expense"] = comparison[
            "ledger_salary_expense"
        ].fillna(0)

        comparison["difference"] = (
            comparison["ledger_salary_expense"]
            - comparison["payroll_employer_cost"]
        )

        bad = comparison[
            comparison["difference"].abs() > TOLERANCE
        ].copy()

        bad["reconciliation_id"] = bad["month"]

        record_rule(
            results, findings, "DQ-04",
            "Payroll-ledger reconciliation",
            "fact_ledger + fact_payroll", bad, "reconciliation_id",
            "Monthly payroll employer_cost must equal net ledger "
            "expense for accounts 5001-5005 within INR 0.01."
        )
    else:
        record_rule(
            results, findings, "DQ-04",
            "Payroll-ledger reconciliation",
            "fact_ledger + fact_payroll", None, "entry_id",
            "Skipped: payroll or ledger dataset is missing."
        )

    # DQ-05: Invoice amount paid cannot exceed total, and
    # balance due cannot be negative.
    if invoices is not None:
        i = invoices.copy()
        total = as_number(i["total_amount"])
        paid = as_number(i["amount_paid"])
        balance = as_number(i["balance_due"])

        bad = i[
            (paid > total + TOLERANCE)
            | (balance < -TOLERANCE)
        ]

        record_rule(
            results, findings, "DQ-05",
            "Invoice overpayment",
            "fact_invoice", bad, "invoice_id",
            "amount_paid must not exceed total_amount and "
            "balance_due must not be negative."
        )
    else:
        record_rule(
            results, findings, "DQ-05", "Invoice overpayment",
            "fact_invoice", None, "invoice_id",
            "Skipped: invoice dataset is missing."
        )

    # DQ-06: Completion date cannot precede start date.
    if tasks is not None:
        t = tasks.copy()
        started = as_date(t["started_date"])
        completed = as_date(t["completed_date"])

        bad = t[
            started.notna()
            & completed.notna()
            & (completed < started)
        ]

        record_rule(
            results, findings, "DQ-06",
            "Task completed before start",
            "fact_task", bad, "task_id",
            "completed_date cannot precede started_date."
        )
    else:
        record_rule(
            results, findings, "DQ-06",
            "Task completed before start",
            "fact_task", None, "task_id",
            "Skipped: task dataset is missing."
        )

    # DQ-07: Done tasks must have a valid completion date.
    if tasks is not None:
        status = tasks["status"].astype(str).str.strip().str.lower()
        completed = as_date(tasks["completed_date"])

        bad = tasks[status.eq("done") & completed.isna()]

        record_rule(
            results, findings, "DQ-07",
            "Done task missing completion date",
            "fact_task", bad, "task_id",
            "A task marked Done must have completed_date."
        )
    else:
        record_rule(
            results, findings, "DQ-07",
            "Done task missing completion date",
            "fact_task", None, "task_id",
            "Skipped: task dataset is missing."
        )

    # DQ-08: Leave end date cannot precede start date.
    if leave is not None:
        lv = leave.copy()
        start = as_date(lv["start_date"])
        end = as_date(lv["end_date"])

        bad = lv[
            start.notna() & end.notna() & (end < start)
        ]

        record_rule(
            results, findings, "DQ-08",
            "Invalid leave date range",
            "fact_leave", bad, "leave_request_id",
            "end_date cannot precede start_date."
        )
    else:
        record_rule(
            results, findings, "DQ-08",
            "Invalid leave date range",
            "fact_leave", None, "leave_request_id",
            "Skipped: leave dataset is missing."
        )

    # DQ-09: Prediction as_of_date must be within seven days
    # of the latest as_of_date in the feed.
    if attrition is not None:
        ar = attrition.copy()
        ar["as_of_parsed"] = as_date(ar["as_of_date"])

        latest_date = ar["as_of_parsed"].max()

        if pd.isna(latest_date):
            bad = ar.copy()
        else:
            threshold = latest_date - pd.Timedelta(days=7)
            bad = ar[
                ar["as_of_parsed"].isna()
                | (ar["as_of_parsed"] < threshold)
            ].copy()

        record_rule(
            results, findings, "DQ-09",
            "Stale attrition predictions",
            "fact_attrition_risk", bad, "prediction_id",
            "as_of_date must be within seven days of the latest "
            "prediction date in the feed."
        )
    else:
        record_rule(
            results, findings, "DQ-09",
            "Stale attrition predictions",
            "fact_attrition_risk", None, "prediction_id",
            "Skipped: attrition risk dataset is missing."
        )

    # DQ-10: Expense total must equal amount excluding GST + GST.
    if expenses is not None:
        ex = expenses.copy()
        expected = (
            as_number(ex["amount_excl_gst"])
            + as_number(ex["gst_amount"])
        )
        actual = as_number(ex["total_amount"])

        bad = ex[
            expected.notna()
            & actual.notna()
            & ((actual - expected).abs() > TOLERANCE)
        ]

        record_rule(
            results, findings, "DQ-10",
            "Expense GST arithmetic",
            "fact_expense", bad, "expense_id",
            "total_amount must equal amount_excl_gst + gst_amount "
            "within INR 0.01."
        )
    else:
        record_rule(
            results, findings, "DQ-10",
            "Expense GST arithmetic",
            "fact_expense", None, "expense_id",
            "Skipped: expense dataset is missing."
        )

    # Additional catalog check: each journal entry must balance.
    if ledger is not None:
        l = ledger.copy()
        l["debit_num"] = as_number(l["debit"]).fillna(0)
        l["credit_num"] = as_number(l["credit"]).fillna(0)

        journal = (
            l.groupby("entry_id", as_index=False)
            .agg(
                total_debit=("debit_num", "sum"),
                total_credit=("credit_num", "sum"),
            )
        )

        journal["difference"] = (
            journal["total_debit"] - journal["total_credit"]
        )

        bad = journal[
            journal["difference"].abs() > 0.005
        ].copy()

        record_rule(
            results, findings, "DQ-C02",
            "Ledger journal balance",
            "fact_ledger", bad, "entry_id",
            "Total debits must equal total credits per journal entry "
            "within INR 0.005."
        )

    return results, findings


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # General profile report; preserve the existing test contract.
    profiles = []
    read_errors = []

    files = sorted(RAW_DIR.glob("*.csv")) if RAW_DIR.exists() else []

    for path in files:
        try:
            profiles.append(profile_file(path))
        except Exception as exc:
            read_errors.append({
                "file": path.name,
                "error": str(exc),
            })
            print(f"ERROR reading {path.name}: {exc}")

    profile_path = REPORT_DIR / "raw_data_quality_report.csv"
    pd.DataFrame(
        profiles, columns=SUMMARY_COLUMNS
    ).to_csv(profile_path, index=False)

    rules, findings = run_business_rules()
    rules_df = pd.DataFrame(rules)

    findings_df = pd.DataFrame(
        findings,
        columns=[
            "rule_id", "rule_name", "dataset",
            "record_id", "details",
        ],
    )

    rules_path = REPORT_DIR / "business_rule_report.csv"
    findings_path = REPORT_DIR / "business_rule_findings.csv"

    rules_df.to_csv(rules_path, index=False)
    findings_df.to_csv(findings_path, index=False)

    report = {
        "project": "PulseIQ-ETL",
        "generated_at": datetime.now().astimezone().isoformat(),
        "files_checked": len(profiles),
        "files_failed_to_read": len(read_errors),
        "read_errors": read_errors,
        "business_rules_total": len(rules),
        "business_rules_passed": int(
            rules_df["status"].eq("PASS").sum()
        ),
        "business_rules_failed": int(
            rules_df["status"].eq("FAIL").sum()
        ),
        "business_rule_results": rules,
        "note": (
            "Rule failures indicate data-quality findings, not "
            "necessarily a pipeline execution failure. DQ-04 uses "
            "the catalog's monthly employer-cost reconciliation "
            "against ledger accounts 5001-5005."
        ),
    }

    json_path = REPORT_DIR / "data_quality_report.json"
    with json_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, default=str)

    print(f"Profile report: {profile_path}")
    print(f"Business-rule report: {rules_path}")
    print(f"Business-rule findings: {findings_path}")
    print(f"JSON report: {json_path}")

    print("\nBUSINESS RULE RESULTS")
    print(
        rules_df[
            ["rule_id", "status", "violation_count"]
        ].to_string(index=False)
    )

    print(
        f"\nPassed: {report['business_rules_passed']} | "
        f"Failed: {report['business_rules_failed']}"
    )


if __name__ == "__main__":
    main()
