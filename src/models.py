"""Pydantic models for data validation. Replace with your own."""

from datetime import date

from pydantic import BaseModel, Field, field_validator

transaction_types = {"income", "expense"}
currencies = {"EUR", "UAH"}
payment_methods = {"cash", "card", "bank_transfer"}
categories = {
    "husband_salary",
    "pension",
    "transport_refund",
    "parents_support",
    "food",
    "nanny",
    "clothes_shoes",
    "medical_insurance",
    "rent",
    "bike_repair",
    "home_repair",
    "transport",
    "gifts",
    "health",
}


class BudgetTransaction(BaseModel):
    """Validated family budget transaction after cleaning."""

    transaction_id: str
    transaction_date: date
    transaction_type: str
    category: str
    amount: float = Field(gt=0)
    currency: str
    payment_method: str
    description: str | None = None

    @field_validator("transaction_type")
    @classmethod
    def validate_transaction_type(cls, value: str) -> str:
        """Validate that transaction_type is one of the allowed values."""
        if value not in transaction_types:
            raise ValueError(f"transaction_type must be one of {transaction_types}")
        return value

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        """Validate that category is one of the allowed values."""
        if value not in categories:
            raise ValueError(f"category must be one of {categories}")
        return value

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        """Validate that currency is one of the allowed values."""
        if value not in currencies:
            raise ValueError(f"currency must be one of {currencies}")
        return value

    @field_validator("payment_method")
    @classmethod
    def validate_payment_method(cls, value: str) -> str:
        """Validate that payment_method is one of the allowed values."""
        if value not in payment_methods:
            raise ValueError(f"payment_method must be one of {payment_methods}")
        return value
