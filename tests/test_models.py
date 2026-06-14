"""Example tests for Pydantic models. Replace with your own."""

from datetime import date
import pytest
from pydantic import ValidationError
from src.models import BudgetTransaction


def make_valid_transaction(**overrides):
    """Create a valid transaction and optionally override some fields."""
    data = {
        "transaction_id": "T001",
        "transaction_date": "2026-06-01",
        "transaction_type": "expense",
        "category": "food",
        "amount": 50.0,
        "currency": "EUR",
        "payment_method": "card",
        "description": "Groceries",
    }

    data.update(overrides)
    return BudgetTransaction(**data)


def test_valid_budget_transaction():
    """A valid budget transaction should be accepted."""
    transaction = make_valid_transaction()

    assert transaction.transaction_id == "T001"
    assert transaction.transaction_date == date(2026, 6, 1)
    assert transaction.transaction_type == "expense"
    assert transaction.category == "food"
    assert transaction.amount == 50.0
    assert transaction.currency == "EUR"
    assert transaction.payment_method == "card"


def test_negative_amount_is_rejected():
    """Amount must be greater than zero."""
    with pytest.raises(ValidationError):
        make_valid_transaction(amount=-25.0)


def test_invalid_transaction_type_is_rejected():
    """Transaction type must be income or expense."""
    with pytest.raises(ValidationError):
        make_valid_transaction(transaction_type="unknown")


def test_unknown_category_is_rejected():
    """Category must be one of the allowed budget categories."""
    with pytest.raises(ValidationError):
        make_valid_transaction(category="random_category")


def test_invalid_currency_is_rejected():
    """Currency must be EUR or UAH."""
    with pytest.raises(ValidationError):
        make_valid_transaction(currency="USD")


def test_invalid_payment_method_is_rejected():
    """Payment method must be card, cash or bank_transfer."""
    with pytest.raises(ValidationError):
        make_valid_transaction(payment_method="paypal")


def test_invalid_date_is_rejected():
    """Invalid date should be rejected."""
    with pytest.raises(ValidationError):
        make_valid_transaction(transaction_date="not-a-date")
