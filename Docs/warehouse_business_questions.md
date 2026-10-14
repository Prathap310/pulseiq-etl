# PulseIQ Analytics Warehouse — Business Questions

## Objective
Design a separate PostgreSQL analytics warehouse to support workforce, payroll, attendance, leave, and invoice reporting.

## Business Questions

1. **Payroll cost:** What is the monthly employer payroll cost by department and role?
2. **Headcount trend:** How does employee headcount change by month and department?
3. **Attendance:** What are the attendance trends by month and department?
4. **Leave analysis:** How many leave requests and leave days occur by leave type and month?
5. **Invoice analysis:** What are the invoiced and collected amounts by month?

## Design Principle
The warehouse will use a star schema, with fact tables storing measurable business events and dimension tables providing descriptive context for reporting.

## Scope
This document defines the reporting questions for Task 2. The warehouse schema and table definitions will be documented separately.