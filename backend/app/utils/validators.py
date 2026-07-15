"""
IntelliDesk AI — Input Validators
Reusable validators for files, emails, passwords, and other inputs.
"""

import re

from flask import current_app

from app.utils.helpers import get_file_extension


def validate_email_format(email: str) -> bool:
    """Check if string is a valid email format."""
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Validate password strength.
    Returns (is_valid: bool, errors: list[str]).
    """
    errors = []
    if len(password) < 8:
        errors.append("Must be at least 8 characters.")
    if not re.search(r"[A-Z]", password):
        errors.append("Must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        errors.append("Must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        errors.append("Must contain at least one digit.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-]", password):
        errors.append("Must contain at least one special character.")
    return len(errors) == 0, errors


def validate_file_extension(filename: str, allowed_extensions: set | None = None) -> bool:
    """Check if file has an allowed extension."""
    if allowed_extensions is None:
        allowed_extensions = current_app.config.get(
            "ALLOWED_UPLOAD_EXTENSIONS",
            {"pdf", "docx", "txt", "md", "png", "jpg", "jpeg"},
        )
    ext = get_file_extension(filename)
    return ext in allowed_extensions


def validate_file_size(file_size_bytes: int) -> bool:
    """Check if file size is within configured limit."""
    max_bytes = current_app.config.get("MAX_UPLOAD_SIZE_MB", 25) * 1024 * 1024
    return file_size_bytes <= max_bytes


def validate_phone(phone: str) -> bool:
    """Loosely validate phone number format."""
    cleaned = re.sub(r"[\s\-\(\)\+]", "", phone)
    return cleaned.isdigit() and 7 <= len(cleaned) <= 15
