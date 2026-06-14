"""Main pipeline: fetch, validate, store."""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from pydantic import ValidationError

from src.models import BudgetTransaction
from src.storage import (
    download_csv_from_blob,
    insert_budget_transactions,
    insert_monthly_summary,
    upload_dataframe_to_blob,
    make_timestamped_blob_name,
)

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
logging.getLogger("azure").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

CATEGORY = {
    # income categories
    "husband salary": "husband_salary",
    "husband's salary": "husband_salary",
    "salary": "husband_salary",
    "pension": "pension",
    "transport refund": "transport_refund",
    "parent support": "parents_support",
    "parents support": "parents_support",
    # food
    "groceries": "food",
    "products": "food",
    # nanny
    "childcare": "nanny",
    "babysitter": "nanny",
    # clothes and shoes
    "clothes": "clothes_shoes",
    "shoes": "clothes_shoes",
    "clothes/shoes": "clothes_shoes",
    # medical insurance
    "medical insurance": "medical_insurance",
    "health insurance": "medical_insurance",
    "insurance": "medical_insurance",
    # rent
    "house rent": "rent",
    # bike repair
    "bike": "bike_repair",
    "bike repair": "bike_repair",
    # home repair
    "home repair": "home_repair",
    # transport
    "public transport": "transport",
    "train": "transport",
    "bus": "transport",
    # gifts
    "gift": "gifts",
    # health
    "medical": "health",
    "healthcare": "health",
}

CURRENCY = {
    "eur": "EUR",
    "euro": "EUR",
    "€": "EUR",
    "uah": "UAH",
    "грн": "UAH",
}


PAYMENT_METHOD = {
    "card": "card",
    "cash": "cash",
    "bank transfer": "bank_transfer",
}


def env_flag(name: str, default: str = "false") -> bool:
    """Read true/false value from environment variable."""
    return os.getenv(name, default).lower() == "true"


def clean_text(value) -> str:
    """Convert value to lowercase text without extra spaces."""
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def clean_transaction_type(value) -> str:
    """Clean transaction type: Income, EXPENSE -> income, expense."""
    return clean_text(value)


def clean_category(value) -> str:
    """Convert messy category names to clean category names."""
    key = clean_text(value)
    return CATEGORY.get(key, key)


def clean_currency(value) -> str:
    """Clean currency values: eur, EURO, € -> EUR."""
    key = clean_text(value)
    return CURRENCY.get(key, key.upper())


def clean_payment_method(value) -> str:
    """Clean payment method: bank transfer -> bank_transfer."""
    key = clean_text(value)
    return PAYMENT_METHOD.get(key, key)


def clean_amount(value) -> float:
    """Convert messy amount values to float.

    Examples:
    €95,40 -> 95.40
    3000,00 -> 3000.00
    €83.90 -> 83.90
    """
    if pd.isna(value):
        raise ValueError("amount is missing")

    text = str(value).strip()

    if text == "":
        raise ValueError("amount is missing")

    text = text.replace("€", "")
    text = text.replace("₴", "")
    text = text.replace(" ", "")
    text = text.replace(",", ".")

    return float(text)


def clean_date(value):
    """Convert different date formats to a Python date."""
    if pd.isna(value):
        raise ValueError("date is missing")

    text = str(value).strip()

    date_formats = [
        "%Y-%m-%d",  # 2026-06-01
        "%d/%m/%Y",  # 01/06/2026
        "%Y/%m/%d",  # 2026/06/05
        "%B %d %Y",  # June 10 2026
        "%d-%m-%Y",  # 07-06-2026
    ]

    for date_format in date_formats:
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue

    raise ValueError(f"invalid date: {value}")


def fetch_data() -> list[dict]:
    """Read messy family budget data from a CSV file or Azure Blob.."""
    input_mode = os.getenv("INPUT_MODE", "local").lower()

    if input_mode == "blob":
        blob_name = os.environ["INPUT_BLOB_NAME"]
        return download_csv_from_blob(blob_name)

    if input_mode == "local":
        input_path = Path(
            os.getenv(
                "INPUT_CSV_PATH",
                "data/family_budget_messy_input_halyna.csv",
            )
        )

        if not input_path.exists():
            log.error("CSV file not found: %s", input_path)
            sys.exit(1)

        df = pd.read_csv(input_path)
        log.info("Loaded %d raw rows from %s", len(df), input_path)
        return df

    raise ValueError(f"Unsupported INPUT_MODE: {input_mode}")


def clean_record(row: pd.Series) -> dict:
    """Clean one CSV row before Pydantic validation."""
    description = row.get("description")

    if pd.isna(description):
        description = None
    else:
        description = str(description).strip()

    return {
        "transaction_id": str(row["transaction_id"]).strip(),
        "transaction_date": clean_date(row["date"]),
        "transaction_type": clean_transaction_type(row["type"]),
        "category": clean_category(row["category"]),
        "amount": clean_amount(row["amount"]),
        "currency": clean_currency(row["currency"]),
        "payment_method": clean_payment_method(row["payment_method"]),
        "description": description,
    }


def validate(raw_df: pd.DataFrame) -> list[BudgetTransaction]:
    """Validate raw records using Pydantic models."""
    valid_transactions = []
    invalid_count = 0
    for _, row in raw_df.iterrows():
        transaction_id = row.get("transaction_id", "unknown")

        try:
            cleaned = clean_record(row)
            transaction = BudgetTransaction(**cleaned)
            valid_transactions.append(transaction)

        except (ValueError, ValidationError) as e:
            invalid_count += 1
            log.warning("Skipping invalid record %s: %s", transaction_id, e)

    log.info("Validated %d / %d records", len(valid_transactions), len(raw_df))
    log.info("Found %d invalid records", invalid_count)

    return valid_transactions


def get_exchange_rate_to_eur(currency: str) -> float:
    """Get exchange rate from currency to EUR."""
    if currency == "EUR":
        return 1.0

    fallback_key = f"EXCHANGE_RATE_{currency}_TO_EUR"
    fallback_rate = os.getenv(fallback_key)

    if fallback_rate:
        log.info("Using fallback exchange rate from %s", fallback_key)
        return float(fallback_rate)

    url = f"https://api.frankfurter.dev/v2/rate/{currency}/EUR"

    response = requests.get(url, timeout=20)
    response.raise_for_status()

    data = response.json()

    if "rate" in data:
        return float(data["rate"])

    if "rates" in data and "EUR" in data["rates"]:
        return float(data["rates"]["EUR"])

    raise ValueError(f"Could not find EUR exchange rate in API response: {data}")


def transform(transactions: list[BudgetTransaction]) -> pd.DataFrame:
    """Convert validated records to a DataFrame and apply transformations.

    This is where pandas earns its place. Replace the examples below with
    transformations that make sense for your data.
    """
    df = pd.DataFrame([transaction.model_dump() for transaction in transactions])

    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    df["month"] = df["transaction_date"].dt.to_period("M").astype(str)

    currencies = df["currency"].unique()
    rates = {}

    for currency in currencies:
        rates[currency] = get_exchange_rate_to_eur(currency)
        log.info("Exchange rate %s -> EUR = %s", currency, rates[currency])

    df["exchange_rate_to_eur"] = df["currency"].map(rates)
    df["amount_eur"] = df["amount"] * df["exchange_rate_to_eur"]
    df["amount_eur"] = df["amount_eur"].round(2)

    log.info("Transformed %d rows", len(df))
    return df


def create_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Create monthly summary by category."""
    df = df.copy()

    df["income_eur"] = df["amount_eur"].where(
        df["transaction_type"] == "income",
        0,
    )

    df["expense_eur"] = df["amount_eur"].where(
        df["transaction_type"] == "expense",
        0,
    )

    summary = df.groupby(["month", "category"], as_index=False).agg(
        total_income_eur=("income_eur", "sum"),
        total_expense_eur=("expense_eur", "sum"),
    )

    summary["net_eur"] = (
        summary["total_income_eur"] - summary["total_expense_eur"]
    ).round(2)

    log.info("Created %d summary rows", len(summary))
    return summary


def save_local_output(df: pd.DataFrame, summary: pd.DataFrame) -> None:
    """Save local output files before adding Azure/Postgres."""
    output_dir = Path("data/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_dir / "cleaned_budget_transactions.csv", index=False)
    summary.to_csv(output_dir / "monthly_category_summary.csv", index=False)

    log.info("Saved cleaned transactions to data/output/")
    log.info("Saved monthly summary to data/output/")


def save_to_azure(df: pd.DataFrame, summary: pd.DataFrame) -> None:
    """Save transformed data to Postgres and Azure Blob Storage."""
    insert_budget_transactions(df)
    insert_monthly_summary(summary)

    transactions_blob_name = make_timestamped_blob_name(
        "budget/cleaned",
        "cleaned_budget_transactions.csv",
    )
    summary_blob_name = make_timestamped_blob_name(
        "budget/summary",
        "monthly_category_summary.csv",
    )

    upload_dataframe_to_blob(df, transactions_blob_name)
    upload_dataframe_to_blob(summary, summary_blob_name)


def run():
    """Run the full pipeline: fetch -> validate -> transform -> store."""
    log.info("Pipeline starting")

    raw = fetch_data()
    transactions = validate(raw)

    if not transactions:
        log.error("No valid transactions to process")
        sys.exit(1)

    df = transform(transactions)
    summary = create_summary(df)

    save_local_output(df, summary)

    if env_flag("SAVE_TO_AZURE"):
        save_to_azure(df, summary)
        log.info("Azure storage step completed")
    else:
        log.info("SAVE_TO_AZURE=false, skipping Postgres and Blob Storage")

    log.info("Pipeline finished: %d records stored", len(df))


if __name__ == "__main__":
    # Fail fast if required env vars are missing
    for var in ["POSTGRES_URL", "AZURE_STORAGE_CONNECTION_STRING"]:
        if var not in os.environ:
            log.error("Missing required environment variable: %s", var)
            sys.exit(1)

    run()
