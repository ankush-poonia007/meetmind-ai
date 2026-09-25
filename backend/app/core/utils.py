"""
MeetMind AI — Core Utilities.

Provides shared normalization and helper utilities for deadlines and date-range filters,
enforcing canonical frozen deadline semantics.
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional, Tuple


def normalize_deadline(value: Any) -> Optional[datetime]:
    """
    Normalizes a task deadline to a UTC timezone-aware datetime adhering to
    MeetMind AI frozen deadline semantics:
    - Date-only input (date object or 'YYYY-MM-DD' string) -> end of that calendar date in UTC (23:59:59.999999).
    - Explicit timestamp (ISO string or datetime) -> exact instant preserved, normalized to UTC.
    - Naive datetime -> assigned UTC timezone.
    - NULL / None / empty string -> None.
    """
    if value is None or value == "":
        return None

    if isinstance(value, str):
        val_str = value.strip()
        if not val_str:
            return None
        # Check if date-only: no 'T' or space separator
        if "T" not in val_str and " " not in val_str:
            try:
                d = date.fromisoformat(val_str)
                return datetime.combine(d, time.max, tzinfo=timezone.utc)
            except ValueError:
                pass
        try:
            dt = datetime.fromisoformat(val_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass

    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime.combine(value, time.max, tzinfo=timezone.utc)

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    return value


def parse_filter_bound(val: Any, is_upper: bool) -> Tuple[str, datetime]:
    """
    Parses a deadline filter boundary (upper or lower) into an SQL operator
    and a UTC timezone-aware datetime.

    Upper bound (deadline_before):
    - Date-only input -> '<' midnight UTC at the start of the following day (half-open interval).
      This ensures tasks due at the beginning, middle, or end of the requested date are included,
      while tasks due on the following date are excluded.
    - Explicit timestamp -> '<=' exact UTC instant.

    Lower bound (deadline_after):
    - Date-only input -> '>=' midnight UTC at the start of the requested calendar day.
      This ensures tasks due anywhere on that calendar day or later are included.
    - Explicit timestamp -> '>=' exact UTC instant.
    """
    if isinstance(val, str):
        val_str = val.strip()
        if "T" not in val_str and " " not in val_str:
            try:
                val = date.fromisoformat(val_str)
            except ValueError:
                pass
        else:
            try:
                val = datetime.fromisoformat(val_str.replace("Z", "+00:00"))
            except ValueError:
                pass

    if isinstance(val, date) and not isinstance(val, datetime):
        if is_upper:
            next_day_midnight = datetime.combine(val + timedelta(days=1), time.min, tzinfo=timezone.utc)
            return ("<", next_day_midnight)
        else:
            start_day_midnight = datetime.combine(val, time.min, tzinfo=timezone.utc)
            return (">=", start_day_midnight)

    if isinstance(val, datetime):
        dt = val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val.astimezone(timezone.utc)
        return ("<=" if is_upper else ">=", dt)

    raise ValueError(f"Invalid deadline filter boundary value: {val!r}")
