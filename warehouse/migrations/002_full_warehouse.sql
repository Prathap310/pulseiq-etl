

BEGIN;



CREATE SCHEMA IF NOT EXISTS dw;



-- WARNING: Recreates these warehouse tables.

-- Existing warehouse data in these tables will be removed.

DROP TABLE IF EXISTS

      dw.fact_forecast,

      dw.fact_attrition_risk,

      dw.fact_anomaly,

      dw.fact_task,

      dw.fact_expense,

      dw.fact_invoice_payment,

      dw.fact_invoice,

      dw.fact_ledger,

      dw.fact_headcount_monthly,

      dw.fact_leave,

      dw.fact_attendance_monthly,

      dw.fact_payroll,

      dw.dim_employee,

      dw.dim_sprint,

      dw.dim_team,

      dw.dim_vendor,

      dw.dim_client,

      dw.dim_account,

      dw.dim_leave_type,

      dw.dim_location,

      dw.dim_role,

      dw.dim_department,

      dw.dim_date

CASCADE;



-- ==========================================

-- DIMENSION TABLES (11)

-- ==========================================



CREATE TABLE dw.dim_date (

      date_key INTEGER PRIMARY KEY,

      date DATE UNIQUE NOT NULL,

      year INTEGER,

      quarter INTEGER,

      month_number INTEGER,

      month_name VARCHAR(20),

      year_month VARCHAR(10),

      week_of_year INTEGER,

      day_of_week VARCHAR(20),

      is_weekend VARCHAR(5),

      is_holiday VARCHAR(5),

      is_working_day VARCHAR(5),

      financial_year VARCHAR(10),

      fiscal_quarter VARCHAR(10),

      fiscal_month_number INTEGER,

      is_month_end VARCHAR(5),

      month_start_date DATE,

      month_end_date DATE

);



CREATE TABLE dw.dim_department (

      department_id VARCHAR(20) PRIMARY KEY,

      department_name VARCHAR(150),

      cost_center VARCHAR(50),

      description TEXT,

      is_leadership VARCHAR(5)

);



CREATE TABLE dw.dim_role (

      role_id VARCHAR(20) PRIMARY KEY,

      department_id VARCHAR(20),

      role_title VARCHAR(150),

      level INTEGER,

      grade VARCHAR(50),

      band_min_annual NUMERIC(14,2),

      band_mid_annual NUMERIC(14,2),

      band_max_annual NUMERIC(14,2),

      overtime_eligible VARCHAR(5),

      band_reference_year INTEGER

);



CREATE TABLE dw.dim_location (

      work_location VARCHAR(150) PRIMARY KEY,

      state VARCHAR(100),

      city_tier VARCHAR(50),

      tier_number INTEGER

);



CREATE TABLE dw.dim_leave_type (

      leave_type_code VARCHAR(50) PRIMARY KEY,

      leave_type_name VARCHAR(150),

      pay_type VARCHAR(50),

      annual_quota_days NUMERIC(8,2),

      prorated_for_joiners VARCHAR(5),

      carry_forward_allowed VARCHAR(5),

      max_carry_forward_days NUMERIC(8,2),

      policy_note TEXT

);



CREATE TABLE dw.dim_account (

      account_code VARCHAR(50) PRIMARY KEY,

      account_name VARCHAR(200),

      account_type VARCHAR(50),

      normal_balance VARCHAR(50),

      parent_code VARCHAR(50),

      is_group VARCHAR(5),

      statement VARCHAR(50),

      is_active VARCHAR(5)

);



CREATE TABLE dw.dim_client (

      client_id VARCHAR(50) PRIMARY KEY,

      client_name VARCHAR(200),

      industry VARCHAR(100),

      city VARCHAR(100),

      state_or_region VARCHAR(100),

      country VARCHAR(100),

      client_type VARCHAR(100),

      gst_registration VARCHAR(100),

      payment_terms_days INTEGER,

      payment_behaviour VARCHAR(100),

      primary_service_line VARCHAR(150),

      contact_email VARCHAR(254),

      onboarded_on DATE,

      is_active VARCHAR(5)

);



CREATE TABLE dw.dim_vendor (

      vendor_id VARCHAR(50) PRIMARY KEY,

      vendor_name VARCHAR(200),

      primary_expense_account VARCHAR(50),

      payment_terms_days INTEGER,

      city VARCHAR(100),

      gst_registration VARCHAR(100),

      is_active VARCHAR(5)

);



CREATE TABLE dw.dim_team (

      team_id VARCHAR(50) PRIMARY KEY,

      team_name VARCHAR(150),

      department_id VARCHAR(20),

      team_lead_employee_id VARCHAR(50),

      active_members INTEGER,

      planning_cadence VARCHAR(100),

      board_tool VARCHAR(100)

);



CREATE TABLE dw.dim_sprint (

      sprint_id VARCHAR(50) PRIMARY KEY,

      sprint_name VARCHAR(150),

      start_date DATE,

      end_date DATE,

      working_days INTEGER,

      financial_year VARCHAR(10)

);



-- Historical employee dimension:

-- One row per employee version, identified by employee_key.

CREATE TABLE dw.dim_employee (

      employee_key INTEGER PRIMARY KEY,

      employee_id VARCHAR(50) NOT NULL,

      full_name VARCHAR(200),

      gender VARCHAR(30),

      date_of_birth DATE,

      hire_date DATE,

      exit_date DATE,

      employment_status VARCHAR(50),

      employment_type VARCHAR(50),

      department_id VARCHAR(20),

      role_id VARCHAR(20),

      role_title VARCHAR(150),

      job_level INTEGER,

      manager_id VARCHAR(50),

      work_location VARCHAR(150),

      work_mode VARCHAR(50),

      highest_education VARCHAR(100),

      valid_from DATE NOT NULL,

      valid_to DATE,

      is_current VARCHAR(5) NOT NULL DEFAULT TRUE,

      change_reason VARCHAR(200),

      UNIQUE (employee_id, valid_from),

      CHECK (valid_to IS NULL OR valid_to >= valid_from)

);



-- ==========================================

-- FACT TABLES (12)

-- ==========================================



-- Grain: one row per payroll item.

CREATE TABLE dw.fact_payroll (

      payroll_item_id VARCHAR(100) PRIMARY KEY,

      run_id VARCHAR(50),

      employee_id VARCHAR(50),

      date_key INTEGER,

      employee_key INTEGER,

      period_end_date DATE,

      department_id VARCHAR(20),

      role_id VARCHAR(20),

      payable_days NUMERIC(8,2),

      lop_days NUMERIC(8,2),

      overtime_hours_paid NUMERIC(8,2),

      variable_pay_type VARCHAR(100),

      monthly_fixed_gross NUMERIC(14,2),

      basic NUMERIC(14,2),

      hra NUMERIC(14,2),

      conveyance NUMERIC(14,2),

      medical NUMERIC(14,2),

      special_allowance NUMERIC(14,2),

      earned_fixed_pay NUMERIC(14,2),

      overtime_pay NUMERIC(14,2),

      variable_pay NUMERIC(14,2),

      gross_pay NUMERIC(14,2),

      pf_employee NUMERIC(14,2),

      esi_employee NUMERIC(14,2),

      professional_tax NUMERIC(14,2),

      tds NUMERIC(14,2),

      other_deductions NUMERIC(14,2),

      total_deductions NUMERIC(14,2),

      net_pay NUMERIC(14,2),

      pf_employer NUMERIC(14,2),

      esi_employer NUMERIC(14,2),

      employer_cost NUMERIC(14,2),

      headcount_flag INTEGER

);



-- Grain: one row per employee-month attendance record.

CREATE TABLE dw.fact_attendance_monthly (

      attendance_fact_id VARCHAR(100) PRIMARY KEY,

      employee_id VARCHAR(50),

      date_key INTEGER,

      employee_key INTEGER,

      department_id VARCHAR(20),

      scheduled_days NUMERIC(8,2),

      present_days NUMERIC(8,2),

      wfh_days NUMERIC(8,2),

      half_days_unpaid NUMERIC(8,2),

      paid_leave_days NUMERIC(8,2),

      unpaid_absence_days NUMERIC(8,2),

      late_arrivals INTEGER,

      avg_hours_worked NUMERIC(8,2),

      overtime_hours NUMERIC(8,2),

      attendance_rate NUMERIC(8,4),

      period_end_date DATE

);



-- Grain: one row per leave request.

CREATE TABLE dw.fact_leave (

      leave_request_id VARCHAR(100) PRIMARY KEY,

      employee_id VARCHAR(50),

      employee_key INTEGER,

      leave_type_code VARCHAR(50),

      start_date_key INTEGER,

      end_date_key INTEGER,

      start_date DATE,

      end_date DATE,

      days NUMERIC(8,2),

      status VARCHAR(50),

      applied_on DATE,

      decided_on DATE,

      approver_id VARCHAR(50),

      reason TEXT

);



-- Grain: one row per department-month.

CREATE TABLE dw.fact_headcount_monthly (

      date_key INTEGER,

      month_start_date DATE,

      department_id VARCHAR(20),

      headcount_start INTEGER,

      hires INTEGER,

      exits INTEGER,

      voluntary_exits INTEGER,

      transfers_in INTEGER,

      transfers_out INTEGER,

      headcount_end INTEGER,

      attrition_rate_monthly_pct NUMERIC(10,4),

      PRIMARY KEY (date_key, department_id)

);



-- Grain: one row per ledger journal line.

CREATE TABLE dw.fact_ledger (

      line_id VARCHAR(100) PRIMARY KEY,

      entry_id VARCHAR(100),

      date_key INTEGER,

      entry_date DATE,

      posting_period VARCHAR(30),

      financial_year VARCHAR(20),

      account_code VARCHAR(50),

      debit NUMERIC(16,2),

      credit NUMERIC(16,2),

      signed_amount_debit_positive NUMERIC(16,2),

      cost_center_department_id VARCHAR(20),

      source_type VARCHAR(100),

      source_id VARCHAR(100)

);



-- Grain: one row per invoice.

CREATE TABLE dw.fact_invoice (

      invoice_id VARCHAR(100) PRIMARY KEY,

      invoice_number VARCHAR(100),

      client_id VARCHAR(50),

      invoice_date_key INTEGER,

      invoice_date DATE,

      due_date DATE,

      service_line_account VARCHAR(50),

      subtotal NUMERIC(16,2),

      gst_rate_percent NUMERIC(8,4),

      gst_amount NUMERIC(16,2),

      total_amount NUMERIC(16,2),

      amount_paid NUMERIC(16,2),

      balance_due NUMERIC(16,2),

      status VARCHAR(50),

      last_payment_date DATE,

      days_to_pay INTEGER,

      days_past_due_at_cutoff INTEGER,

      ageing_bucket_at_cutoff VARCHAR(50),

      carried_in_from_prior_period BOOLEAN,

      ledger_entry_id VARCHAR(100)

);



-- Grain: one row per invoice payment.

CREATE TABLE dw.fact_invoice_payment (

      payment_id VARCHAR(100) PRIMARY KEY,

      invoice_id VARCHAR(100),

      payment_date_key INTEGER,

      payment_date DATE,

      amount NUMERIC(16,2),

      payment_mode VARCHAR(100),

      reference_no VARCHAR(100),

      received_by VARCHAR(100),

      ledger_entry_id VARCHAR(100)

);



-- Grain: one row per expense.

CREATE TABLE dw.fact_expense (

      expense_id VARCHAR(100) PRIMARY KEY,

      expense_date DATE,

      expense_date_key INTEGER,

      category_account VARCHAR(50),

      vendor_id VARCHAR(50),

      bill_reference VARCHAR(100),

      description TEXT,

      department_id VARCHAR(20),

      amount_excl_gst NUMERIC(16,2),

      gst_rate_percent NUMERIC(8,4),

      gst_amount NUMERIC(16,2),

      total_amount NUMERIC(16,2),

      due_date DATE,

      paid_date DATE,

      status VARCHAR(50),

      payment_mode VARCHAR(100),

      submitted_by VARCHAR(100),

      approved_by VARCHAR(100),

      ledger_entry_id VARCHAR(100),

      payment_ledger_entry_id VARCHAR(100)

);



-- Grain: one row per task.

CREATE TABLE dw.fact_task (

      task_id VARCHAR(100) PRIMARY KEY,

      team_id VARCHAR(50),

      sprint_id VARCHAR(50),

      assignee_employee_id VARCHAR(50),

      task_type VARCHAR(100),

      priority VARCHAR(50),

      story_points NUMERIC(8,2),

      created_date DATE,

      started_date DATE,

      due_date DATE,

      completed_date DATE,

      status VARCHAR(50),

      reopened_count INTEGER,

      cycle_time_days NUMERIC(8,2),

      is_overdue_at_cutoff VARCHAR(5),

      completed_on_time VARCHAR(5)

);



-- Grain: one row per scored anomaly result.

CREATE TABLE dw.fact_anomaly (

      result_id VARCHAR(100) PRIMARY KEY,

      source_dataset VARCHAR(150),

      record_id VARCHAR(100),

      employee_id VARCHAR(50),

      period VARCHAR(50),

      anomaly_score NUMERIC(12,6),

      flagged VARCHAR(5),

      reason_code VARCHAR(100),

      reason_text TEXT,

      money_at_risk NUMERIC(16,2),

      model_version VARCHAR(100),

      scored_at TIMESTAMPTZ,

      period_key VARCHAR(50)

);



-- Grain: one row per employee attrition-risk prediction.

CREATE TABLE dw.fact_attrition_risk (

      prediction_id VARCHAR(100) PRIMARY KEY,

      employee_id VARCHAR(50),

      as_of_date_key INTEGER,

      department_id VARCHAR(20),

      as_of_date DATE,

      risk_score_12m NUMERIC(12,6),

      risk_band VARCHAR(50),

      top_reason_1 TEXT,

      top_reason_2 TEXT,

      top_reason_3 TEXT,

      model_version VARCHAR(100),

      model_note TEXT,

      employee_key INTEGER

);



-- Grain: one row per metric, department and forecast month.

CREATE TABLE dw.fact_forecast (

      forecast_id VARCHAR(100) PRIMARY KEY,

      metric VARCHAR(150),

      department_id VARCHAR(20),

      forecast_month DATE,

      forecast_value NUMERIC(16,2),

      lower_80 NUMERIC(16,2),

      upper_80 NUMERIC(16,2),

      method VARCHAR(100),

      trained_through DATE,

      model_version VARCHAR(100),

      forecast_month_key INTEGER

);



-- ==========================================

-- FOREIGN KEYS

-- ==========================================



ALTER TABLE dw.dim_role

      ADD CONSTRAINT fk_role_department

      FOREIGN KEY (department_id)

      REFERENCES dw.dim_department(department_id);



ALTER TABLE dw.dim_employee

      ADD CONSTRAINT fk_employee_department

      FOREIGN KEY (department_id)

      REFERENCES dw.dim_department(department_id);



ALTER TABLE dw.dim_employee

      ADD CONSTRAINT fk_employee_role

      FOREIGN KEY (role_id)

      REFERENCES dw.dim_role(role_id);



ALTER TABLE dw.dim_employee

      ADD CONSTRAINT fk_employee_location

      FOREIGN KEY (work_location)

      REFERENCES dw.dim_location(work_location);



ALTER TABLE dw.dim_team

      ADD CONSTRAINT fk_team_department

      FOREIGN KEY (department_id)

      REFERENCES dw.dim_department(department_id);



ALTER TABLE dw.dim_account

      ADD CONSTRAINT fk_account_parent

      FOREIGN KEY (parent_code)

      REFERENCES dw.dim_account(account_code);



ALTER TABLE dw.dim_vendor

      ADD CONSTRAINT fk_vendor_account

      FOREIGN KEY (primary_expense_account)

      REFERENCES dw.dim_account(account_code);



ALTER TABLE dw.fact_payroll

      ADD CONSTRAINT fk_payroll_date

      FOREIGN KEY (date_key) REFERENCES dw.dim_date(date_key),

      ADD CONSTRAINT fk_payroll_employee

      FOREIGN KEY (employee_key) REFERENCES dw.dim_employee(employee_key),

      ADD CONSTRAINT fk_payroll_department

      FOREIGN KEY (department_id) REFERENCES dw.dim_department(department_id),

      ADD CONSTRAINT fk_payroll_role

      FOREIGN KEY (role_id) REFERENCES dw.dim_role(role_id);



ALTER TABLE dw.fact_attendance_monthly

      ADD CONSTRAINT fk_attendance_date

      FOREIGN KEY (date_key) REFERENCES dw.dim_date(date_key),

      ADD CONSTRAINT fk_attendance_employee

      FOREIGN KEY (employee_key) REFERENCES dw.dim_employee(employee_key),

      ADD CONSTRAINT fk_attendance_department

      FOREIGN KEY (department_id) REFERENCES dw.dim_department(department_id);



ALTER TABLE dw.fact_leave

      ADD CONSTRAINT fk_leave_employee

      FOREIGN KEY (employee_key) REFERENCES dw.dim_employee(employee_key),

      ADD CONSTRAINT fk_leave_type

      FOREIGN KEY (leave_type_code) REFERENCES dw.dim_leave_type(leave_type_code),

      ADD CONSTRAINT fk_leave_start_date

      FOREIGN KEY (start_date_key) REFERENCES dw.dim_date(date_key),

      ADD CONSTRAINT fk_leave_end_date

      FOREIGN KEY (end_date_key) REFERENCES dw.dim_date(date_key);



ALTER TABLE dw.fact_headcount_monthly

      ADD CONSTRAINT fk_headcount_date

      FOREIGN KEY (date_key) REFERENCES dw.dim_date(date_key),

      ADD CONSTRAINT fk_headcount_department

      FOREIGN KEY (department_id) REFERENCES dw.dim_department(department_id);



ALTER TABLE dw.fact_ledger

      ADD CONSTRAINT fk_ledger_date

      FOREIGN KEY (date_key) REFERENCES dw.dim_date(date_key),

      ADD CONSTRAINT fk_ledger_account

      FOREIGN KEY (account_code) REFERENCES dw.dim_account(account_code),

      ADD CONSTRAINT fk_ledger_department

      FOREIGN KEY (cost_center_department_id)

      REFERENCES dw.dim_department(department_id);



ALTER TABLE dw.fact_invoice

      ADD CONSTRAINT fk_invoice_client

      FOREIGN KEY (client_id) REFERENCES dw.dim_client(client_id),

      ADD CONSTRAINT fk_invoice_date

      FOREIGN KEY (invoice_date_key) REFERENCES dw.dim_date(date_key),

      ADD CONSTRAINT fk_invoice_account

      FOREIGN KEY (service_line_account)

      REFERENCES dw.dim_account(account_code);



ALTER TABLE dw.fact_invoice_payment

      ADD CONSTRAINT fk_payment_invoice

      FOREIGN KEY (invoice_id) REFERENCES dw.fact_invoice(invoice_id),

      ADD CONSTRAINT fk_payment_date

      FOREIGN KEY (payment_date_key) REFERENCES dw.dim_date(date_key);



ALTER TABLE dw.fact_expense

      ADD CONSTRAINT fk_expense_date

      FOREIGN KEY (expense_date_key) REFERENCES dw.dim_date(date_key),

      ADD CONSTRAINT fk_expense_account

      FOREIGN KEY (category_account) REFERENCES dw.dim_account(account_code),

      ADD CONSTRAINT fk_expense_vendor

      FOREIGN KEY (vendor_id) REFERENCES dw.dim_vendor(vendor_id),

      ADD CONSTRAINT fk_expense_department

      FOREIGN KEY (department_id) REFERENCES dw.dim_department(department_id);



ALTER TABLE dw.fact_task

      ADD CONSTRAINT fk_task_team

      FOREIGN KEY (team_id) REFERENCES dw.dim_team(team_id),

      ADD CONSTRAINT fk_task_sprint

      FOREIGN KEY (sprint_id) REFERENCES dw.dim_sprint(sprint_id);



ALTER TABLE dw.fact_attrition_risk

      ADD CONSTRAINT fk_attrition_date

      FOREIGN KEY (as_of_date_key) REFERENCES dw.dim_date(date_key),

      ADD CONSTRAINT fk_attrition_department

      FOREIGN KEY (department_id) REFERENCES dw.dim_department(department_id),

      ADD CONSTRAINT fk_attrition_employee

      FOREIGN KEY (employee_key) REFERENCES dw.dim_employee(employee_key);



ALTER TABLE dw.fact_forecast

      ADD CONSTRAINT fk_forecast_department

      FOREIGN KEY (department_id) REFERENCES dw.dim_department(department_id),

      ADD CONSTRAINT fk_forecast_month

      FOREIGN KEY (forecast_month_key) REFERENCES dw.dim_date(date_key);



-- ==========================================

-- INDEXES

-- ==========================================



CREATE INDEX IF NOT EXISTS idx_employee_department

      ON dw.dim_employee(department_id);

CREATE INDEX IF NOT EXISTS idx_employee_role

      ON dw.dim_employee(role_id);

CREATE INDEX IF NOT EXISTS idx_employee_location

      ON dw.dim_employee(work_location);

CREATE INDEX IF NOT EXISTS idx_role_department

      ON dw.dim_role(department_id);



CREATE INDEX IF NOT EXISTS idx_payroll_period

      ON dw.fact_payroll(run_id);

CREATE INDEX IF NOT EXISTS idx_payroll_date

      ON dw.fact_payroll(date_key);

CREATE INDEX IF NOT EXISTS idx_payroll_employee

      ON dw.fact_payroll(employee_key);

CREATE INDEX IF NOT EXISTS idx_payroll_department

      ON dw.fact_payroll(department_id);



CREATE INDEX IF NOT EXISTS idx_attendance_date

      ON dw.fact_attendance_monthly(date_key);

CREATE INDEX IF NOT EXISTS idx_attendance_department

      ON dw.fact_attendance_monthly(department_id);



CREATE INDEX IF NOT EXISTS idx_leave_employee

      ON dw.fact_leave(employee_key);

CREATE INDEX IF NOT EXISTS idx_leave_dates

      ON dw.fact_leave(start_date_key, end_date_key);



CREATE INDEX IF NOT EXISTS idx_headcount_department

      ON dw.fact_headcount_monthly(department_id);



CREATE INDEX IF NOT EXISTS idx_ledger_date

      ON dw.fact_ledger(date_key);

CREATE INDEX IF NOT EXISTS idx_ledger_account

      ON dw.fact_ledger(account_code);



CREATE INDEX IF NOT EXISTS idx_invoice_client

      ON dw.fact_invoice(client_id);

CREATE INDEX IF NOT EXISTS idx_invoice_date

      ON dw.fact_invoice(invoice_date_key);



CREATE INDEX IF NOT EXISTS idx_payment_invoice

      ON dw.fact_invoice_payment(invoice_id);

CREATE INDEX IF NOT EXISTS idx_expense_date

      ON dw.fact_expense(expense_date_key);

CREATE INDEX IF NOT EXISTS idx_expense_vendor

      ON dw.fact_expense(vendor_id);



CREATE INDEX IF NOT EXISTS idx_task_team

      ON dw.fact_task(team_id);

CREATE INDEX IF NOT EXISTS idx_task_sprint

      ON dw.fact_task(sprint_id);



CREATE INDEX IF NOT EXISTS idx_anomaly_employee

      ON dw.fact_anomaly(employee_id);

CREATE INDEX IF NOT EXISTS idx_attrition_employee

      ON dw.fact_attrition_risk(employee_key);

CREATE INDEX IF NOT EXISTS idx_forecast_month

      ON dw.fact_forecast(forecast_month_key);



COMMIT;
