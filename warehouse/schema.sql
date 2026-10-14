-- PulseIQ-ETL: Task 2 Analytics dw
-- PostgreSQL star schema

CREATE SCHEMA IF NOT EXISTS dw;

-- 1. Date dimension
CREATE TABLE IF NOT EXISTS dw.dim_date (
    date_key       INTEGER PRIMARY KEY,
    full_date      DATE NOT NULL UNIQUE,
    day_number     INTEGER NOT NULL,
    month_number   INTEGER NOT NULL,
    month_name     VARCHAR(20) NOT NULL,
    quarter_number INTEGER NOT NULL,
    year_number    INTEGER NOT NULL
);

-- 2. Department dimension
CREATE TABLE IF NOT EXISTS dw.dim_department (
    department_key SERIAL PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL UNIQUE
);

-- 3. Role dimension
CREATE TABLE IF NOT EXISTS dw.dim_role (
    role_key SERIAL PRIMARY KEY,
    role_name VARCHAR(100) NOT NULL UNIQUE
);

-- 4. Employee dimension with historical tracking
CREATE TABLE IF NOT EXISTS dw.dim_employee (
    employee_key SERIAL PRIMARY KEY,
    employee_id VARCHAR(50) NOT NULL,
    employee_name VARCHAR(150),
    department_key INTEGER REFERENCES dw.dim_department(department_key),
    role_key INTEGER REFERENCES dw.dim_role(role_key),
    valid_from DATE NOT NULL,
    valid_to DATE,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (employee_id, valid_from),
    CHECK (valid_to IS NULL OR valid_to >= valid_from)
);

-- 5. Leave type dimension
CREATE TABLE IF NOT EXISTS dw.dim_leave_type (
    leave_type_key SERIAL PRIMARY KEY,
    leave_type_name VARCHAR(100) NOT NULL UNIQUE
);

-- 6. Attendance fact: one row per employee per day
CREATE TABLE IF NOT EXISTS dw.fact_attendance (
    employee_key INTEGER NOT NULL
        REFERENCES dw.dim_employee(employee_key),
    date_key INTEGER NOT NULL
        REFERENCES dw.dim_date(date_key),
    attendance_status VARCHAR(30) NOT NULL,
    hours_worked NUMERIC(6,2),
    PRIMARY KEY (employee_key, date_key),
    CHECK (hours_worked IS NULL OR hours_worked >= 0)
);

-- 7. Payroll fact: one row per employee per month
CREATE TABLE IF NOT EXISTS dw.fact_payroll (
    employee_key INTEGER NOT NULL
        REFERENCES dw.dim_employee(employee_key),
    month_date_key INTEGER NOT NULL
        REFERENCES dw.dim_date(date_key),
    gross_salary NUMERIC(12,2) NOT NULL,
    deductions NUMERIC(12,2) DEFAULT 0,
    net_salary NUMERIC(12,2),
    PRIMARY KEY (employee_key, month_date_key),
    CHECK (gross_salary >= 0),
    CHECK (deductions >= 0)
);

-- 8. Leave fact: one row per leave event
CREATE TABLE IF NOT EXISTS dw.fact_leave (
    leave_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_leave_id VARCHAR(100) UNIQUE,
    employee_key INTEGER NOT NULL
        REFERENCES dw.dim_employee(employee_key),
    leave_type_key INTEGER NOT NULL
        REFERENCES dw.dim_leave_type(leave_type_key),
    start_date_key INTEGER NOT NULL
        REFERENCES dw.dim_date(date_key),
    end_date_key INTEGER NOT NULL
        REFERENCES dw.dim_date(date_key),
    leave_days NUMERIC(6,2) NOT NULL,
    CHECK (leave_days > 0)
);

-- 9. Monthly headcount fact:
-- one row per department per month
CREATE TABLE IF NOT EXISTS dw.fact_headcount_monthly (
    department_key INTEGER NOT NULL
        REFERENCES dw.dim_department(department_key),
    month_date_key INTEGER NOT NULL
        REFERENCES dw.dim_date(date_key),
    headcount INTEGER NOT NULL,
    PRIMARY KEY (department_key, month_date_key),
    CHECK (headcount >= 0)
);

-- Indexes for common reporting joins
CREATE INDEX IF NOT EXISTS idx_employee_department
    ON dw.dim_employee(department_key);

CREATE INDEX IF NOT EXISTS idx_employee_role
    ON dw.dim_employee(role_key);

CREATE INDEX IF NOT EXISTS idx_attendance_date
    ON dw.fact_attendance(date_key);

CREATE INDEX IF NOT EXISTS idx_payroll_month
    ON dw.fact_payroll(month_date_key);

CREATE INDEX IF NOT EXISTS idx_leave_employee
    ON dw.fact_leave(employee_key);

CREATE INDEX IF NOT EXISTS idx_headcount_month
    ON dw.fact_headcount_monthly(month_date_key);