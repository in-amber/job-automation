"""Timestamp utilities."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def now_iso() -> str:
    """Get current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def now_local(tz: str = "America/Los_Angeles") -> datetime:
    """Get current time in the specified timezone."""
    return datetime.now(ZoneInfo(tz))


def parse_iso(iso_string: str) -> datetime:
    """Parse an ISO 8601 timestamp string."""
    return datetime.fromisoformat(iso_string)


def format_date(dt: datetime, fmt: str = "%Y-%m-%d") -> str:
    """Format a datetime as a date string."""
    return dt.strftime(fmt)


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format a datetime as a datetime string."""
    return dt.strftime(fmt)


def timestamp_for_filename() -> str:
    """Generate a timestamp suitable for filenames."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
