# PulseIQ-ETL

**PulseIQ-ETL** is a Python-based ETL (Extract, Transform, Load) pipeline designed to process employee data, clean records, identify data quality issues, and generate summary reports.

## Features

- Extract employee data from CSV files.
- Clean and standardize data.
- Remove duplicate records.
- Handle missing values.
- Validate data quality.
- Separate rejected records.
- Generate summary reports and processing logs.
- Run automated unit tests.
- Build and run the application using Docker.
- Automate testing with GitHub Actions CI.

## Tech Stack

- **Language:** Python 3.12
- **Data Processing:** Pandas (if used in the implementation)
- **Input Format:** CSV
- **Containerization:** Docker and Docker Compose
- **Testing:** Python unittest
- **CI/CD:** GitHub Actions

## Project Structure

```text
pulseiq-etl/
├── .github/
│   └── workflows/
│       └── ci.yml
├── Data/
│   ├── Raw/
│   │   └── employees.csv
│   ├── Clean/
│   │   └── employees_cleaned.csv
│   └── Rejected/
│       └── employees_rejected.csv
├── Docs/
├── Logs/
├── Rejected/
├── Src/
│   ├── __init__.py
│   ├── data_quality.py
│   ├── etl.py
│   ├── pipeline.py
│   ├── report.py
│   └── test_etl.py
├── .env.example
├── compose.yaml
├── Dockerfile
├── Dockerfile.test
└── requirements.txt
```

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Prathap310/pulseiq-etl.git
cd pulseiq-etl
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Run the ETL pipeline

```bash
python -m Src.pipeline
```

### 4. Run unit tests

```bash
python -m unittest discover -s Src -p "test_etl.py" -v
```

### 5. Run with Docker Compose

```bash
docker compose up --build
```

## Continuous Integration

GitHub Actions automatically runs the ETL unit tests when changes are pushed to, or a pull request targets, the `main` or `master` branch.

The workflow uses Python 3.12 and installs the dependencies listed in `requirements.txt`.

## Expected Outputs

- Cleaned employee data.
- Rejected records requiring review.
- Data quality results.
- Summary reports and logs.

## Author

**Prathap Reddy**

GitHub: [Prathap310](https://github.com/Prathap310)
