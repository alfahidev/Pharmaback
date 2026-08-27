"""
Common Utility Functions: Date parsing, CSV processing, Ticket reference generation.
"""
import csv
import io
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from django.utils import timezone

def parse_flexible_date(date_str: str | None) -> date | None:
    """
    Parses various date string formats commonly found in French pharmacy CSVs.
    Supports: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, MM/YYYY, YYYY/MM/DD.
    """
    if not date_str:
        return None
    date_str = str(date_str).strip()
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
        "%m/%Y",
        "%m-%Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # If only month/year provided, default to last day or 1st day
            return dt.date()
        except ValueError:
            continue
    return None

def parse_decimal_safe(val: any, default=Decimal("0.00")) -> Decimal:
    """
    Parses a string or float into Decimal handling spaces, commas, currency symbols.
    Example: '1 500,50 FCFA' -> Decimal('1500.50')
    """
    if val is None or val == "":
        return default
    if isinstance(val, (int, float, Decimal)):
        return Decimal(str(val))
    val_str = str(val).replace(" ", "").replace("\xa0", "").replace("FCFA", "").replace("F", "").replace("€", "").replace("$", "")
    val_str = val_str.replace(",", ".")
    try:
        return Decimal(val_str)
    except InvalidOperation:
        return default

def generate_ticket_number(prefix: str = "VTE") -> str:
    """Generates unique formatted ticket code: VTE-YYYYMMDD-XXXXXX"""
    today_str = timezone.now().strftime("%Y%m%d")
    import random
    rand_seq = f"{random.randint(1000, 9999)}"
    return f"{prefix}-{today_str}-{rand_seq}"
