"""Domain entities for Vendors, Evidence, and Solution Categories."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    """Return a timezone-aware UTC timestamp in a stable ISO representation."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class SolutionCategory:
    category_id: str
    name: str
    description: str
    parent_id: str | None = None
    status: str = "Active"
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class Vendor:
    vendor_id: str
    vendor_name: str
    vendor_type: str
    primary_market: str
    company_summary: str
    headquarters: str
    website: str
    solution_categories: list[str] = field(default_factory=list)
    target_customer_types: list[str] = field(default_factory=list)
    evidence_count: int = 0
    last_updated: str = field(default_factory=utc_now)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    status: str = "Active"
    is_synthetic: bool = False


@dataclass(slots=True)
class Evidence:
    evidence_id: str
    vendor_id: str
    source_type: str
    source_title: str
    source_url: str
    publication_date: str
    collected_at: str
    raw_text: str
    cleaned_text: str
    summary: str
    solution_categories: list[str]
    hospital_name: str = ""
    procurement_entity: str = ""
    project_name: str = ""
    contract_value: str = ""
    currency: str = ""
    evidence_status: str = "New"
    validation_status: str = "Valid"
    source_authority: str = "Low"
    traceable: bool = False
    content_hash: str = ""
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    is_synthetic: bool = False
    duplicate_of_evidence_id: str = ""
    duplicate_reasons: list[str] = field(default_factory=list)
    validation_messages: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.errors:
            return "Invalid"
        if self.warnings:
            return "Warning"
        return "Valid"

    @property
    def messages(self) -> list[str]:
        return [*(f"ERROR: {item}" for item in self.errors), *(f"WARNING: {item}" for item in self.warnings)]


@dataclass(slots=True)
class ImportResult:
    created: list[Evidence] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)

    @property
    def created_count(self) -> int:
        return len(self.created)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)
