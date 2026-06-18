"""Storage functions for Postgres and Blob Storage."""

import logging
import os
from contextlib import closing
from datetime import date, datetime, timezone
from io import StringIO

import pandas as pd
from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient

import psycopg2

log = logging.getLogger(__name__)


def get_db_schema() -> str:
    """Return the personal database schema name."""
    return os.environ.get("DB_SCHEMA", "public")


def prepare_database_schema(cur, schema: str) -> None:
    """Create and select the personal database schema."""
    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")  # noqa: S608
    cur.execute(f"SET search_path TO {schema}")  # noqa: S608


def insert_budget_transactions(df: pd.DataFrame) -> None:
    """Insert a DataFrame of budget transactions into Postgres.

    Creates the table in your personal schema (DB_SCHEMA env var, e.g. dev_alice).
    All CREATE TABLE and INSERT statements run inside that schema so your tables
    never collide with other students on the shared server.
    """

    db_url = os.environ["POSTGRES_URL"]
    schema = os.environ.get("DB_SCHEMA", "public")

    with closing(psycopg2.connect(db_url)) as conn:
        with conn.cursor() as cur:
            prepare_database_schema(cur, schema)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS budget_transactions (
                    transaction_id TEXT PRIMARY KEY,
                    transaction_date DATE NOT NULL,
                    transaction_type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    amount NUMERIC NOT NULL,
                    currency TEXT NOT NULL,
                    payment_method TEXT NOT NULL,
                    description TEXT,
                    month TEXT NOT NULL,
                    exchange_rate_to_eur NUMERIC NOT NULL,
                    amount_eur NUMERIC NOT NULL,
                    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)

            for _, row in df.iterrows():
                transaction_date = row["transaction_date"]
                if isinstance(transaction_date, date):
                    transaction_date = transaction_date.date()

                cur.execute(
                    """
                    INSERT INTO budget_transactions (
                        transaction_id,
                        transaction_date,
                        transaction_type,
                        category,
                        amount,
                        currency,
                        payment_method,
                        description,
                        month,
                        exchange_rate_to_eur,
                        amount_eur
                        )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (transaction_id) DO UPDATE SET
                        transaction_date = EXCLUDED.transaction_date,
                        transaction_type = EXCLUDED.transaction_type,
                        category = EXCLUDED.category,
                        amount = EXCLUDED.amount,
                        currency = EXCLUDED.currency,
                        payment_method = EXCLUDED.payment_method,
                        description = EXCLUDED.description,
                        month = EXCLUDED.month,
                        exchange_rate_to_eur = EXCLUDED.exchange_rate_to_eur,
                        amount_eur = EXCLUDED.amount_eur,
                        inserted_at = NOW()
                    """,
                    (
                        row["transaction_id"],
                        transaction_date,
                        row["transaction_type"],
                        row["category"],
                        float(row["amount"]),
                        row["currency"],
                        row["payment_method"],
                        row["description"],
                        row["month"],
                        float(row["exchange_rate_to_eur"]),
                        float(row["amount_eur"]),
                    ),
                )

        conn.commit()

    log.info("Inserted %d rows into %s.budget_transactions", len(df), schema)


def insert_monthly_summary(summary_df: pd.DataFrame) -> None:
    """Insert monthly category summary into Azure Postgres."""
    db_url = os.environ["POSTGRES_URL"]
    schema = get_db_schema()

    with closing(psycopg2.connect(db_url)) as conn:
        with conn.cursor() as cur:
            prepare_database_schema(cur, schema)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS monthly_category_summary (
                    month TEXT NOT NULL,
                    category TEXT NOT NULL,
                    total_income_eur NUMERIC NOT NULL,
                    total_expense_eur NUMERIC NOT NULL,
                    net_eur NUMERIC NOT NULL,
                    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (month, category)
                )
            """)

            for _, row in summary_df.iterrows():
                cur.execute(
                    """
                    INSERT INTO monthly_category_summary (
                        month,
                        category,
                        total_income_eur,
                        total_expense_eur,
                        net_eur
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (month, category) DO UPDATE SET
                        total_income_eur = EXCLUDED.total_income_eur,
                        total_expense_eur = EXCLUDED.total_expense_eur,
                        net_eur = EXCLUDED.net_eur,
                        generated_at = NOW()
                    """,
                    (
                        row["month"],
                        row["category"],
                        float(row["total_income_eur"]),
                        float(row["total_expense_eur"]),
                        float(row["net_eur"]),
                    ),
                )

        conn.commit()

    log.info(
        "Inserted %d rows into %s.monthly_category_summary",
        len(summary_df),
        schema,
    )


def get_blob_container():
    """Return Azure Blob container client."""
    conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container_name = os.environ.get("AZURE_STORAGE_CONTAINER", "raw")

    client = BlobServiceClient.from_connection_string(conn_str)
    container = client.get_container_client(container_name)

    try:
        container.create_container()
    except ResourceExistsError:
        pass

    return container


def upload_dataframe_to_blob(df: pd.DataFrame, blob_name: str) -> None:
    """Upload a DataFrame to AzureBlob Storage as a CSV file."""
    container = get_blob_container()
    csv_text = df.to_csv(index=False)

    container.upload_blob(
        name=blob_name,
        data=csv_text.encode("utf-8"),
        overwrite=True,
    )

    log.info("Uploaded DataFrame to blob: %s", blob_name)


def download_csv_from_blob(blob_name: str) -> pd.DataFrame:
    """Download a CSV file from Azure Blob Storage and read it with pandas."""
    container = get_blob_container()

    blob_client = container.get_blob_client(blob_name)
    csv_bytes = blob_client.download_blob().readall()
    csv_text = csv_bytes.decode("utf-8")

    df = pd.read_csv(StringIO(csv_text))

    log.info("Downloaded %d rows from blob: %s", len(df), blob_name)
    return df


def make_timestamped_blob_name(prefix: str, filename: str) -> str:
    """Create a timestamped blob name."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    return f"{prefix}/{timestamp}_{filename}"