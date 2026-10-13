# PulseIQ-ETL — Task 2: Analytics Warehouse Design

## 1. Objective

Design a reporting database separate from the operational database. The warehouse will use a star schema with fact tables and dimension tables.

## 2. Business Questions

1. What is the employee headcount by department and month?
2. What is the payroll cost by department and month?
3. What are the monthly attendance trends?
4. How many employees leave each month?
5. How do employee roles and departments change over time?

## 3. Dimension Tables

- **dim_employee:** Employee details and historical changes.
- **dim_department:** Department information.
- **dim_role:** Employee role or job title.
- **dim_date:** Calendar date, month, quarter, and year.
- **dim_leave_type:** Leave categories and descriptions.

## 4. Fact Tables and Grain

- **fact_attendance:** One row per employee per day.
- **fact_payroll:** One row per employee per month.
- **fact_leave:** One row per leave record or leave event.
- **fact_headcount_monthly:** One row per department per month.

## 5. Historical Employee Changes

The employee dimension should preserve historical department and role assignments using `valid_from` and `valid_to` dates. This allows historical payroll and headcount reports to use the correct department and role for each period.

## 6. Data Loading

The Task 1 ETL pipeline will provide cleaned employee data. Task 2 will extend the pipeline to load warehouse tables using repeat-safe upserts.

## 7. Database

PostgreSQL will be used as the analytics warehouse database, running as a service in Docker Compose.

## 8. Validation

Warehouse query results will be compared with the cleaned source data. Repeated ETL runs must not create duplicate warehouse records.