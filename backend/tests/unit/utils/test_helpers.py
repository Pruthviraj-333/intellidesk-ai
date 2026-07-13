"""
IntelliDesk AI — Helper Utility Unit Tests
Tests for ID generation, formatting, and file utilities.
"""

import pytest
import re
from app.utils.helpers import (
    generate_ticket_number,
    generate_incident_number,
    generate_problem_number,
    format_bytes,
    format_duration_hours,
    mask_email,
    get_file_extension,
    sanitize_filename,
)


class TestIDGeneration:
    def test_ticket_number_format(self):
        ticket_id = generate_ticket_number()
        assert re.match(r"TKT-\d{8}-\d{4}", ticket_id), f"Invalid format: {ticket_id}"

    def test_incident_number_format(self):
        inc_id = generate_incident_number()
        assert re.match(r"INC-\d{8}-\d{4}", inc_id), f"Invalid format: {inc_id}"

    def test_problem_number_format(self):
        prb_id = generate_problem_number()
        assert re.match(r"PRB-\d{8}-\d{4}", prb_id), f"Invalid format: {prb_id}"

    def test_generated_ids_are_unique(self):
        ids = {generate_ticket_number() for _ in range(100)}
        assert len(ids) > 90  # High uniqueness (random suffix)


class TestFormatBytes:
    def test_bytes(self):
        assert format_bytes(512) == "512 B"

    def test_kilobytes(self):
        assert format_bytes(1536) == "1.5 KB"

    def test_megabytes(self):
        assert format_bytes(2 * 1024 * 1024) == "2.0 MB"

    def test_gigabytes(self):
        assert "GB" in format_bytes(2 * 1024 * 1024 * 1024)


class TestFormatDuration:
    def test_minutes_only(self):
        assert format_duration_hours(0.5) == "30m"

    def test_hours_only(self):
        assert format_duration_hours(2.0) == "2h"

    def test_hours_and_minutes(self):
        assert format_duration_hours(2.5) == "2h 30m"


class TestMaskEmail:
    def test_masks_local_part(self):
        masked = mask_email("john@example.com")
        assert masked.startswith("j***@")
        assert "example.com" in masked

    def test_handles_invalid_email(self):
        assert mask_email("notanemail") == "notanemail"


class TestFileUtilities:
    def test_get_extension_normal(self):
        assert get_file_extension("document.pdf") == "pdf"

    def test_get_extension_uppercase(self):
        assert get_file_extension("PHOTO.JPG") == "jpg"

    def test_get_extension_no_extension(self):
        assert get_file_extension("README") == ""

    def test_sanitize_filename_removes_special_chars(self):
        result = sanitize_filename("my file (2026).pdf")
        assert "<" not in result
        assert ">" not in result
        assert ";" not in result
