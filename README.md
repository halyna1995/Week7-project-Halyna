# Week 7 Project: Family Budget Data Pipeline

## What it does

Processes messy fictional family budget CSV file containing income and expense
records. The pipeline cleans the data, validates records with Pydantic, converts UAH
amounts to EUR, creates monthly category summaries with pandas, and stores the results
in Azure Postgres and Azure Blob Storage.

## Architecture

```text
Local CSV or Azure Blob CSV
 ↓
pipeline.py
 ↓
pandas cleaning
 ↓
Pydantic validation
 ↓
exchange-rate enrichment
 ↓
Azure Postgres + Azure Blob Storage
```

## Data source

The input file is a messy CSV file:
data/family_budget_messy_input_halyna.csv

It contains fictional family budget transactions with:

- income records, such as salary, pension, transport refund, and parents support;
- expense records, such as food, nanny, clothes/shoes, medical insurance, rent,
  transport, gifts, health, bike repair, and home repair;
- different date formats;
- inconsistent category names;
- inconsistent amount formats;
- EUR and UAH currencies.

## Main transformations

The pipeline performs the following steps:

1. Reads the CSV file from local storage or Azure Blob Storage.
2. Cleans messy values with pandas and helper functions.
3. Normalizes categories, currencies, payment methods, dates, and amounts.
4. Validates cleaned records with the BudgetTransaction Pydantic model.
5. Converts UAH amounts to EUR using an exchange rate.
6. Creates a monthly category summary.
7. Saves cleaned transactions and summaries locally.
8. Optionally writes results to Azure Postgres and Azure Blob Storage.

### Outputs

## Local output

When the pipeline runs, it creates:
data/output/cleaned_budget_transactions.csv
data/output/monthly_category_summary.csv

These files are generated output and are not committed to Git.

## Azure Postgres output

The pipeline writes to two tables in the personal schema:
dev_halyna.budget_transactions
dev_halyna.monthly_category_summary

## Azure Blob Storage output

The pipeline uploads CSV outputs to Blob Storage:
budget/cleaned/
budget/summary/

The input CSV can also be uploaded to:
budget/input/family_budget_messy_input_halyna.csv

## Environment variables

Create a local .env file from .env.example:

Copy-Item .env.example .env

Then fill in the real values in .env.

Example .env.example:

INPUT_MODE=local
INPUT_CSV_PATH=data/family_budget_messy_input_halyna.csv
INPUT_BLOB_NAME=budget/input/family_budget_messy_input_halyna.csv

SAVE_TO_AZURE=false
LOG_LEVEL=INFO

POSTGRES_URL=
DB_SCHEMA=dev_halyna

AZURE_STORAGE_CONNECTION_STRING=
AZURE_STORAGE_CONTAINER=raw

EXCHANGE_RATE_UAH_TO_EUR=0.0215

Important:

- .env.example is committed to GitHub.
- .env is local only and must not be committed.
- Do not commit real connection strings, passwords, or Azure secrets.

## Run locally without Azure writes

Use this mode to test cleaning, validation, transformation, and local output files.

In .env set:

INPUT_MODE=local
SAVE_TO_AZURE=false

Run:

python -m src.pipeline

Expected result:

Loaded 50 raw rows
Validated 44 / 50 records
Found 6 invalid records
Transformed 44 rows
Created 20 summary rows
Saved cleaned transactions to data/output/
Saved monthly summary to data/output/
Pipeline finished

## Run locally with Azure Postgres and Blob Storage

Use this mode after filling in real Azure values in .env.

In .env set:

INPUT_MODE=local
SAVE_TO_AZURE=true

Run:

python -m src.pipeline

Expected result:

Inserted 44 rows into dev_halyna.budget_transactions
Inserted 20 rows into dev_halyna.monthly_category_summary
Uploaded DataFrame to blob: budget/cleaned/...
Uploaded DataFrame to blob: budget/summary/...
Azure storage step completed
Pipeline finished

## Run with input CSV from Azure Blob Storage

First upload the input CSV to Blob Storage:

Container: raw
Blob name: budget/input/family_budget_messy_input_halyna.csv

Then set in .env:

INPUT_MODE=blob
SAVE_TO_AZURE=true
INPUT_BLOB_NAME=budget/input/family_budget_messy_input_halyna.csv

Run:

python -m src.pipeline

The pipeline should download the CSV from Blob Storage, process it,
write rows to Postgres, and upload output files back to Blob Storage.

## Run tests

python -m pytest tests/ -v

The tests check that the Pydantic model:

- accepts a valid budget transaction;
- rejects negative amounts;
- rejects invalid transaction types;
- rejects unknown categories;
- rejects unsupported currencies;
- rejects invalid payment methods;
- rejects invalid dates.

## Format and lint

python -m ruff format src/ tests/
python -m ruff check src/ tests/

If uv is available, the same commands can be run as:
uv run pytest tests/ -v
uv run ruff format src/ tests/
uv run ruff check src/ tests/
uv run python -m src.pipeline

## Verify Postgres results

In DBeaver or another Postgres client, run:

```sql
SELECT COUNT(_) FROM dev_halyna.budget_transactions;
SELECT COUNT(_) FROM dev_halyna.monthly_category_summary;
```

Expected result after one successful run:
budget_transactions: 44 rows
monthly_category_summary: 20 rows

To inspect data:

```sql
SELECT _ FROM dev_halyna.budget_transactions LIMIT 10;
SELECT _ FROM dev_halyna.monthly_category_summary LIMIT 10;
```

## Verify Blob Storage results

In Azure Portal:

Storage Account
→ Containers
→ raw
→ budget

Expected folders:
budget/input/
budget/cleaned/
budget/summary/

The output files should look like:
budget/cleaned/YYYY-MM-DD_HHMMSS_cleaned_budget_transactions.csv
budget/summary/YYYY-MM-DD_HHMMSS_monthly_category_summary.csv

## Current project status

Implemented:

- messy family budget CSV input;
- pandas cleaning;
- Pydantic validation;
- UAH to EUR conversion;
- monthly category summary;
- local CSV output;
- Postgres storage;
- Blob Storage upload;
- optional Blob input mode;
- pytest model tests.

Next step:

- Docker build;
- push image to Azure Container Registry;
- create Azure Container App Job;
- configure scheduled run.
