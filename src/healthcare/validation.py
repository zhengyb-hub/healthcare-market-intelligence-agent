"""Healthcare-specific structural validation rules."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable
from urllib.parse import urlparse

from .enums import (
    EVIDENCE_STATUSES,
    SOURCE_AUTHORITIES,
    SOURCE_TYPES,
    TARGET_CUSTOMER_TYPES,
    URL_OPTIONAL_SOURCE_TYPES,
    VALIDATION_STATUSES,
    VENDOR_STATUSES,
    VENDOR_TYPES,
)
from .models import ValidationResult


def is_valid_url(value: str) -> bool:
    if not value.strip():
        return False
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _valid_date(value: str, allow_datetime: bool = False) -> bool:
    if not value.strip():
        return False
    try:
        if allow_datetime:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            date.fromisoformat(value)
    except ValueError:
        return False
    return True


def validate_vendor_input(values: dict[str, Any]) -> ValidationResult:
    result = ValidationResult()
    for field_name in (
        "vendor_id",
        "vendor_name",
        "vendor_type",
        "primary_market",
        "company_summary",
        "headquarters",
        "website",
    ):
        if not str(values.get(field_name, "")).strip():
            result.errors.append(f"Missing required Vendor field: {field_name}")

    if str(values.get("vendor_type", "")) not in VENDOR_TYPES:
        result.errors.append("Invalid vendor_type")
    if str(values.get("status", "Active")) not in VENDOR_STATUSES:
        result.errors.append("Invalid Vendor status")
    website = str(values.get("website", ""))
    if website and not is_valid_url(website):
        result.errors.append("Invalid Vendor website URL")

    customer_types = values.get("target_customer_types", []) or []
    invalid_customers = sorted(set(customer_types) - set(TARGET_CUSTOMER_TYPES))
    if invalid_customers:
        result.errors.append(
            "Invalid target_customer_types: " + ", ".join(invalid_customers)
        )
    return result


def validate_evidence_input(
    values: dict[str, Any],
    vendor_exists: Callable[[str], bool],
    valid_solution_categories: set[str],
) -> ValidationResult:
    result = ValidationResult()
    required = (
        "evidence_id",
        "vendor_id",
        "source_type",
        "source_title",
        "publication_date",
        "collected_at",
        "raw_text",
        "evidence_status",
        "source_authority",
    )
    for field_name in required:
        if not str(values.get(field_name, "")).strip():
            result.errors.append(f"Missing required Evidence field: {field_name}")

    vendor_id = str(values.get("vendor_id", "")).strip()
    if vendor_id and not vendor_exists(vendor_id):
        result.errors.append(f"Missing or invalid Vendor reference: {vendor_id}")

    source_type = str(values.get("source_type", "")).strip()
    if source_type not in SOURCE_TYPES:
        result.errors.append("Invalid source_type")

    source_url = str(values.get("source_url", "")).strip()
    if source_url and not is_valid_url(source_url):
        result.errors.append("Invalid source URL format")
    elif not source_url and source_type not in URL_OPTIONAL_SOURCE_TYPES:
        result.warnings.append("Source URL is missing for a source that is normally linkable")

    publication_date = str(values.get("publication_date", "")).strip()
    if publication_date and not _valid_date(publication_date):
        result.errors.append("Invalid publication_date; expected YYYY-MM-DD")

    collected_at = str(values.get("collected_at", "")).strip()
    if collected_at and not (
        _valid_date(collected_at) or _valid_date(collected_at, allow_datetime=True)
    ):
        result.errors.append("Invalid collected_at date or timestamp")

    if not str(values.get("raw_text", "")).strip():
        result.errors.append("Empty raw_text")

    categories = values.get("solution_categories", []) or []
    if not categories:
        result.warnings.append("No solution category assigned")
    invalid_categories = sorted(set(categories) - valid_solution_categories)
    if invalid_categories:
        result.errors.append(
            "Invalid solution category: " + ", ".join(invalid_categories)
        )

    contract_value = str(values.get("contract_value", "")).strip()
    if contract_value:
        try:
            parsed_value = Decimal(contract_value.replace(",", ""))
            if parsed_value < 0:
                result.errors.append("Invalid contract_value: value cannot be negative")
        except InvalidOperation:
            result.errors.append("Invalid contract_value: expected a number")
        if not str(values.get("currency", "")).strip():
            result.errors.append("Currency is required when contract_value is provided")

    if str(values.get("evidence_status", "")) not in EVIDENCE_STATUSES:
        result.errors.append("Invalid Evidence status")
    if str(values.get("validation_status", "Valid")) not in VALIDATION_STATUSES:
        result.errors.append("Invalid Validation status")
    if str(values.get("source_authority", "")) not in SOURCE_AUTHORITIES:
        result.errors.append("Invalid source_authority")

    return result
