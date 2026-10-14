# PulseIQ Analytics Warehouse Schema

## 1. Overview

- Database: `pulseiq_wh`
- Schema: `dw`
- Database engine: PostgreSQL 16
- Warehouse model: dimensional/star-schema warehouse
- Dimensions: 11
- Fact tables: 12
- Total warehouse tables: 23

Source workbook:
`Data/Source/03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx`

Loader:
`Src/load_warehouse.py`

Migration:
`warehouse/migrations/002_full_warehouse.sql`

## 2. Dimension tables

| Dimension | Purpose |
|---|---|
| `dim_date` | Calendar dates and date attributes |
| `dim_employee` | Employee details and historical versions |
| `dim_department` | Department reference data and aggregate member |
| `dim_role` | Employee roles |
| `dim_location` | Work locations |
| `dim_leave_type` | Leave categories |
| `dim_account` | Financial account hierarchy |
| `dim_client` | Client reference data |
| `dim_vendor` | Vendor reference data |
| `dim_team` | Team reference data |
| `dim_sprint` | Sprint reference data |

### Special dimension members

The loader creates:
- An unknown employee member with `employee_key = -1`.
- An aggregate department member with `department_id = 'ALL'`.
- Additional calendar dates through `2027-03-31`.

These members support unknown employee references, aggregate reporting, and future calendar coverage.

## 3. Fact tables and grain

The table below documents the intended reporting grain and the primary key defined in `warehouse/migrations/002_full_warehouse.sql`. Primary keys establish record uniqueness; they do not necessarily enforce every business-grain rule.

| Fact table | Intended grain | Primary key |
|---|---|---|
| `fact_payroll` | One payroll item per payroll record | `payroll_item_id` |
| `fact_attendance_monthly` | One attendance record per source fact | `attendance_fact_id` |
| `fact_leave` | One leave request | `leave_request_id` |
| `fact_headcount_monthly` | One department per reporting date | `(date_key, department_id)` |
| `fact_ledger` | One ledger line | `line_id` |
| `fact_invoice` | One invoice | `invoice_id` |
| `fact_invoice_payment` | One invoice payment transaction | `payment_id` |
| `fact_expense` | One expense record | `expense_id` |
| `fact_task` | One task | `task_id` |
| `fact_anomaly` | One anomaly record | `result_id` |
| `fact_attrition_risk` | One prediction record | `prediction_id` |
| `fact_forecast` | One forecast record | `forecast_id` |

The dimension-table keys are defined in the migration. `dim_employee` uses `employee_key` as its primary key and enforces uniqueness on `(employee_id, valid_from)` to support historical employee versions.

**Follow-up validation:** Confirm source-level business grain and any additional uniqueness rules for attendance, payroll, anomaly, attrition-risk, and forecast records. Do not infer these rules from primary keys alone.

## 4. Slowly Changing Dimension (SCD)

`dim_employee` contains employee versioning fields:
- `employee_key`
- `employee_id`
- `valid_from`
- `valid_to`
- `is_current`
- `change_reason`

The employee business identifier can appear in multiple historical versions. Fact tables should use the appropriate employee surrogate key where available.

A known issue exists for employee `100000`'s history: the workbook documents an overlapping validity interval. This is retained for data-quality validation and should not be silently corrected during loading.

## 5. Data loading and repeatability

The loader processes all 23 warehouse tables and commits the load transaction.

The loader adds the unknown employee, aggregate department, and calendar extension described above. Loads use existing warehouse keys and upsert logic.

A second load completed successfully. The post-load row-count check matched the expected counts for all 23 tables.

**Idempotence validation:** 23/23 tables matched expected row counts after the repeated load. This confirms row-count stability; record-level equality should be checked separately if required.

## 6. Payroll reconciliation

The workbook's `reference_summary_dept_month` sheet contains 198 department-month records.

After excluding the four documented exception payroll items (`PI-X0001` through `PI-X0004`) in the reconciliation query:

- Department-month keys matched: 198/198
- Missing keys: 0
- Extra keys: 0
- Employer cost matched: 198/198
- Gross pay matched: 198/198
- Overtime pay matched: 198/198
- Employees paid matched: 198/198

**Result: PASS**

The exception records remain in the warehouse. The reconciliation query excludes them for comparison; it does not physically remove or quarantine them.

## 7. Known data-quality issues

The source workbook includes a `dq_known_issues` sheet. Documented examples include:
- Duplicate payroll rows and payroll records with missing employee references
- Attendance records after employee exit
- A payroll-to-ledger mismatch
- An invoice overpayment
- Invalid task and leave dates
- Stale attrition predictions
- An expense total mismatch
- An employee history overlap

These records should be reported and handled through explicit data-quality rules rather than silently deleted.

## 8. Validation status

| Validation | Result |
|---|---|
| Initial warehouse load | Passed |
| All 23 tables loaded | Passed |
| Payroll department-month reconciliation after excluding four known exceptions | Passed |
| Repeat-load row-count check | Passed, 23/23 tables |
| Known data-quality checks | Findings identified; review against source exceptions |

## 9. Follow-up work

- Confirm exact fact-table grain and unique keys against `warehouse/migrations/002_full_warehouse.sql`.
- Implement or document repeatable data-quality checks.
- Decide how downstream reporting should exclude or flag known exceptions.
- Run the project's unit tests and CI workflow.
