from __future__ import annotations

from datetime import datetime


def generate_customer_code(sequence: int) -> str:
    return f"CUST-{datetime.utcnow():%Y%m%d}-{sequence:04d}"


def generate_bill_number(sequence: int) -> str:
    return f"BILL-{datetime.utcnow():%Y%m%d}-{sequence:04d}"
