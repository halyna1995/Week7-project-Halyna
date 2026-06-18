# Week 7 Project: Family Budget Data Pipeline

## What it does

This project processes a messy fictional family budget CSV file containing income and expense records. The pipeline cleans the data, validates records with Pydantic, converts UAH amounts to EUR, creates monthly category summaries with pandas, and stores the results in Azure Postgres and Azure Blob Storage.

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
Azure Postgres
        ↓
Azure Blob Storage
        ↓
Docker image
        ↓
Azure Container App Job
```

## Data source

The input file is a messy CSV file:
data/family_budget_messy_input_halyna.csv

It contains fictional family budget transactions with:

- income records, such as salary, pension, transport refund, and parents support;
- expense records, such as food, nanny, clothes/shoes, medical insurance, rent, transport, gifts, health, bike repair, and home repair;
- different date formats;
- inconsistent category names;
- inconsistent amount formats;
- EUR and UAH currencies.

The same input CSV can also be uploaded to Azure Blob Storage:
Container: raw
Blob name: budget/input/family_budget_messy_input_halyna.csv

## Main transformations

The pipeline performs the following steps:

1. Reads the CSV file from local storage or Azure Blob Storage.
2. Cleans messy values with pandas and helper functions.
3. Normalizes categories, currencies, payment methods, dates, and amounts.
4. Validates cleaned records with the BudgetTransaction Pydantic model.
5. Converts UAH amounts to EUR using an exchange rate.
6. Creates a monthly category summary with pandas.
7. Saves cleaned transactions and summaries locally.
8. Writes cleaned transactions and summaries to Azure Postgres.
9. Uploads cleaned and summary CSV files to Azure Blob Storage.

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

```bash
cp .env.example .env
```

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

## Docker

Build the Docker image locally:
docker build -t family-budget-pipeline .

Run the container with environment variables from .env:
docker run --rm --env-file .env family-budget-pipeline

For Docker runs, the recommended input mode is Blob input:

INPUT_MODE=blob
INPUT_BLOB_NAME=budget/input/family_budget_messy_input_halyna.csv
SAVE_TO_AZURE=true

The Docker run was verified successfully. The container reads the input CSV from Azure Blob Storage, processes 44 valid records, writes data to Azure Postgres, and uploads output CSV files to Azure Blob Storage.

## Docker image for Azure

Build and tag the image for Azure Container Registry:

```bash
docker build --platform linux/amd64 \
  -t hyfregistry.azurecr.io/halyna-family-budget-pipeline:latest .
```

Push the image:

```bash
docker push hyfregistry.azurecr.io/halyna-family-budget-pipeline:latest
```

## Azure Container App Job

The pipeline is deployed as an Azure Container App Job.

Job name:
halyna-budget-pipeline-job

Resource group:
rg-hyf-data

Container Apps environment:
env-hyf-data

Image:
hyfregistry.azurecr.io/halyna-family-budget-pipeline:latest

Schedule:
`0 6 * * *`
This means the job is scheduled to run daily at 06:00 UTC.

## Create the job

Load credentials from your local .env file:

```bash
POSTGRES_URL=$(grep ^POSTGRES_URL= .env | cut -d= -f2-)
AZURE_STORAGE_CONNECTION_STRING=$(grep ^AZURE_STORAGE_CONNECTION_STRING= .env | cut -d= -f2-)
```

Create the job:

```bash
az containerapp job create \
  --name halyna-budget-pipeline-job \
  --resource-group rg-hyf-data \
  --environment env-hyf-data \
  --image hyfregistry.azurecr.io/halyna-family-budget-pipeline:latest \
  --registry-server hyfregistry.azurecr.io \
  --trigger-type Schedule \
  --cron-expression "0 6 * * *" \
  --replica-timeout 300 \
  --replica-retry-limit 0 \
  --env-vars \
    POSTGRES_URL="$POSTGRES_URL" \
    AZURE_STORAGE_CONNECTION_STRING="$AZURE_STORAGE_CONNECTION_STRING" \
    DB_SCHEMA=dev_halyna \
    AZURE_STORAGE_CONTAINER=raw \
    INPUT_MODE=blob \
    INPUT_BLOB_NAME=budget/input/family_budget_messy_input_halyna.csv \
    SAVE_TO_AZURE=true \
    LOG_LEVEL=INFO
```

## Start the job

```bash
az containerapp job start \
  --name halyna-budget-pipeline-job \
  --resource-group rg-hyf-data
```

## Verify job execution

```bash
az containerapp job execution list \
  --name halyna-budget-pipeline-job \
  --resource-group rg-hyf-data \
  --output table
```

A successful run should show status:
Succeeded

## Verify Postgres results

In DBeaver or another Postgres client, run:

```sql
SELECT COUNT(*) FROM dev_halyna.budget_transactions;
SELECT COUNT(*) FROM dev_halyna.monthly_category_summary;
```

Expected result after one successful run:
budget_transactions: 44 rows
monthly_category_summary: 20 rows

To inspect data:

```sql
SELECT * FROM dev_halyna.budget_transactions LIMIT 10;
SELECT * FROM dev_halyna.monthly_category_summary LIMIT 10;
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

The cleaned and summary files were verified in Azure Blob Storage after a successful Docker run.