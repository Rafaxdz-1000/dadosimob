"""Helpers for normalizing Brazilian text, numbers and dates."""

from __future__ import annotations

import math
import re
import unicodedata
from datetime import date, datetime
from typing import Any

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_label(value: Any) -> str:
    """Lowercase, strip accents and collapse punctuation into single spaces.

    >>> normalize_label("Valor de Transação (declarado pelo contribuinte)")
    'valor de transacao declarado pelo contribuinte'
    """
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return _NON_ALNUM.sub(" ", text.lower()).strip()


def parse_br_number(value: Any) -> float | None:
    """Parse numbers written in Brazilian format.

    Accepts floats/ints untouched and strings like ``"R$ 1.234.567,89"``,
    ``"1234,5"``, ``"12,5%"`` or ``"1234.50"``. Returns ``None`` when the value
    cannot be interpreted.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        f = float(value)
        return None if math.isnan(f) else f
    text = str(value).strip().replace("R$", "").replace("%", "").replace(" ", "")
    text = text.replace(" ", "")
    if not text or text in {"-", "--"}:
        return None
    if "," in text:
        # Brazilian format: dots are thousand separators, comma is decimal.
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") > 1:
        # "1.234.567" with no decimals.
        text = text.replace(".", "")
    try:
        return float(text)
    except ValueError:
        return None


_DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y")


def parse_br_date(value: Any) -> date | None:
    """Parse a date from datetime objects, Excel serials or common BR strings."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if hasattr(value, "to_pydatetime"):  # pandas.Timestamp
        try:
            return value.to_pydatetime().date()
        except (ValueError, OverflowError):
            return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isnan(value):
            return None
        # Excel serial date (1900 system).
        if 20000 < value < 80000:
            from datetime import timedelta

            return (datetime(1899, 12, 30) + timedelta(days=float(value))).date()
        return None
    text = str(value).strip()[:10]
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None
