"""
IntelliDesk AI — Utility Helpers
ID generation, slug creation, date formatting, and general utilities.
"""

import random
import string
from datetime import datetime, timezone


def generate_ticket_number() -> str:
    """
    Generate a unique ticket ID in format TKT-YYYYMMDD-XXXX.
    XXXX is a zero-padded random 4-digit number.
    Uniqueness enforced at the database level (UNIQUE constraint).
    """
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = "".join(random.choices(string.digits, k=4))
    return f"TKT-{date_str}-{suffix}"


def generate_incident_number() -> str:
    """Generate incident number: INC-YYYYMMDD-XXXX."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = "".join(random.choices(string.digits, k=4))
    return f"INC-{date_str}-{suffix}"


def generate_problem_number() -> str:
    """Generate problem number: PRB-YYYYMMDD-XXXX."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = "".join(random.choices(string.digits, k=4))
    return f"PRB-{date_str}-{suffix}"


def generate_article_slug(title: str) -> str:
    """
    Generate a URL-safe slug from an article title.
    Appends a short random suffix to prevent collisions.
    """
    from slugify import slugify
    base_slug = slugify(title, max_length=180)
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{base_slug}-{suffix}"


def format_bytes(size_in_bytes: int) -> str:
    """Convert bytes to human-readable string (e.g., '2.4 MB')."""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 ** 2:
        return f"{size_in_bytes / 1024:.1f} KB"
    elif size_in_bytes < 1024 ** 3:
        return f"{size_in_bytes / 1024 ** 2:.1f} MB"
    return f"{size_in_bytes / 1024 ** 3:.1f} GB"


def format_duration_hours(hours: float) -> str:
    """Convert hours to human-readable duration (e.g., '2h 30m')."""
    total_minutes = int(hours * 60)
    h, m = divmod(total_minutes, 60)
    if h == 0:
        return f"{m}m"
    if m == 0:
        return f"{h}h"
    return f"{h}h {m}m"


def time_until(dt: datetime) -> str:
    """Return human-readable time remaining until a datetime."""
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = dt - now
    if delta.total_seconds() <= 0:
        return "Overdue"
    total_minutes = int(delta.total_seconds() / 60)
    h, m = divmod(total_minutes, 60)
    if h == 0:
        return f"{m}m"
    if h < 24:
        return f"{h}h {m}m"
    days = h // 24
    return f"{days}d {h % 24}h"


def mask_email(email: str) -> str:
    """Partially mask email for safe display (e.g., 'j***@example.com')."""
    parts = email.split("@")
    if len(parts) != 2:
        return email
    local = parts[0]
    masked_local = local[0] + "***" if len(local) > 1 else "***"
    return f"{masked_local}@{parts[1]}"


def get_file_extension(filename: str) -> str:
    """Extract and lowercase file extension from filename."""
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def sanitize_filename(filename: str) -> str:
    """Remove unsafe characters from a filename."""
    keepchars = (" ", ".", "_", "-")
    return "".join(c for c in filename if c.isalnum() or c in keepchars).rstrip()
