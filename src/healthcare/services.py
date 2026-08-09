"""Service layer for Vendor and Evidence business operations."""

from __future__ import annotations

import csv
from dataclasses import asdict
from datetime import date
import io
import json
import sqlite3
from typing import Any
from uuid import uuid4

from .deduplication import clean_text, content_fingerprint, find_near_duplicate_title
from .enums import SOURCE_AUTHORITY_GUIDANCE
from .models import Evidence, ImportResult, Vendor, utc_now
from .repositories import (
    EvidenceRepository,
    SolutionCategoryRepository,
    VendorRepository,
)
from .validation import is_valid_url, validate_evidence_input, validate_vendor_input


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _list_value(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    separator = ";" if ";" in text else "|" if "|" in text else ","
    return [item.strip() for item in text.split(separator) if item.strip()]


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}


class VendorService:
    def __init__(
        self,
        repository: VendorRepository,
    ) -> None:
        self.repository = repository
        self.event_handler: Any | None = None

    def create_vendor(self, values: dict[str, Any]) -> Vendor:
        now = utc_now()
        payload = {
            "vendor_id": str(values.get("vendor_id") or _new_id("vendor")),
            "vendor_name": str(values.get("vendor_name", "")).strip(),
            "vendor_type": str(values.get("vendor_type", "Healthcare IT Vendor")),
            "primary_market": str(values.get("primary_market", "")).strip(),
            "company_summary": clean_text(values.get("company_summary", ""), 4000),
            "headquarters": str(values.get("headquarters", "")).strip(),
            "website": str(values.get("website", "")).strip(),
            "target_customer_types": _list_value(
                values.get("target_customer_types", [])
            ),
            "evidence_count": 0,
            "last_updated": now,
            "created_at": str(values.get("created_at") or now),
            "updated_at": now,
            "status": str(values.get("status", "Active")),
            "is_synthetic": _bool_value(values.get("is_synthetic", False)),
        }
        result = validate_vendor_input(payload)
        if result.errors:
            raise ValueError("; ".join(result.errors))
        vendor = Vendor(solution_categories=[], **payload)
        try:
            created = self.repository.create(vendor)
            if self.event_handler is not None:
                self.event_handler.vendor_updated(created, "created")
            return created
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Vendor could not be created: {exc}") from exc

    def get_vendor(self, vendor_id: str) -> Vendor | None:
        return self.repository.get(vendor_id)

    def list_vendors(
        self,
        include_archived: bool = False,
        search: str = "",
    ) -> list[Vendor]:
        return self.repository.list_all(include_archived, search)

    def update_vendor(self, vendor_id: str, values: dict[str, Any]) -> Vendor:
        existing = self.repository.get(vendor_id)
        if existing is None:
            raise KeyError(f"Unknown vendor_id: {vendor_id}")
        payload = asdict(existing)
        payload.update(values)
        payload["vendor_id"] = vendor_id
        payload["target_customer_types"] = _list_value(
            payload.get("target_customer_types", [])
        )
        result = validate_vendor_input(payload)
        if result.errors:
            raise ValueError("; ".join(result.errors))
        updated = self.repository.update(vendor_id, payload)
        if self.event_handler is not None:
            self.event_handler.vendor_updated(updated, "updated")
        return updated

    def archive_vendor(self, vendor_id: str) -> Vendor:
        archived = self.repository.archive(vendor_id)
        if self.event_handler is not None:
            self.event_handler.vendor_updated(archived, "archived")
        return archived


class EvidenceService:
    def __init__(
        self,
        evidence_repository: EvidenceRepository,
        vendor_repository: VendorRepository,
        category_repository: SolutionCategoryRepository,
    ) -> None:
        self.evidence_repository = evidence_repository
        self.vendor_repository = vendor_repository
        self.category_repository = category_repository
        self.event_handler: Any | None = None

    def create_evidence(self, values: dict[str, Any]) -> Evidence:
        now = utc_now()
        raw_text = str(values.get("raw_text", ""))
        cleaned_text = clean_text(values.get("cleaned_text") or raw_text)
        source_type = str(values.get("source_type", "Manual Entry")).strip()
        source_url = str(values.get("source_url", "")).strip()
        payload: dict[str, Any] = {
            "evidence_id": str(values.get("evidence_id") or _new_id("evidence")),
            "vendor_id": str(values.get("vendor_id", "")).strip(),
            "source_type": source_type,
            "source_title": clean_text(values.get("source_title", ""), 500),
            "source_url": source_url,
            "publication_date": str(values.get("publication_date", "")).strip(),
            "collected_at": str(values.get("collected_at") or date.today().isoformat()),
            "raw_text": raw_text,
            "cleaned_text": cleaned_text,
            "summary": clean_text(values.get("summary") or cleaned_text[:500], 1000),
            "solution_categories": _list_value(
                values.get("solution_categories", [])
            ),
            "hospital_name": clean_text(values.get("hospital_name", ""), 300),
            "procurement_entity": clean_text(
                values.get("procurement_entity", ""),
                300,
            ),
            "project_name": clean_text(values.get("project_name", ""), 400),
            "contract_value": str(values.get("contract_value", "")).strip(),
            "currency": str(values.get("currency", "")).strip().upper(),
            "evidence_status": str(values.get("evidence_status", "New")),
            "validation_status": "Valid",
            "source_authority": str(
                values.get("source_authority")
                or SOURCE_AUTHORITY_GUIDANCE.get(source_type, "Low")
            ),
            "traceable": bool(source_url and is_valid_url(source_url)),
            "content_hash": content_fingerprint(cleaned_text),
            "created_at": str(values.get("created_at") or now),
            "updated_at": now,
            "is_synthetic": _bool_value(values.get("is_synthetic", False)),
            "duplicate_of_evidence_id": "",
            "duplicate_reasons": [],
            "validation_messages": [],
        }

        vendor_exists = self.vendor_repository.get(payload["vendor_id"]) is not None
        result = validate_evidence_input(
            payload,
            vendor_exists=lambda vendor_id: (
                vendor_exists and vendor_id == payload["vendor_id"]
            ),
            valid_solution_categories=self.category_repository.valid_ids(),
        )
        if any(message.startswith("Missing or invalid Vendor reference") for message in result.errors):
            raise ValueError("; ".join(result.errors))

        exact_duplicates = self.evidence_repository.find_exact_duplicates(
            payload["source_url"],
            payload["content_hash"],
        )
        if exact_duplicates:
            payload["duplicate_of_evidence_id"] = exact_duplicates[0][0]
            payload["duplicate_reasons"] = exact_duplicates[0][1]
            result.warnings.append(
                "Duplicate evidence detected: "
                + ", ".join(payload["duplicate_reasons"])
            )
        else:
            near_title = find_near_duplicate_title(
                payload["source_title"],
                self.evidence_repository.title_candidates(payload["vendor_id"]),
            )
            if near_title:
                payload["duplicate_of_evidence_id"] = near_title[0]
                payload["duplicate_reasons"] = [
                    f"Near-Duplicate Title ({near_title[1]:.2f})"
                ]
                result.warnings.append(
                    f"Near-duplicate title detected at similarity {near_title[1]:.2f}"
                )

        payload["validation_status"] = result.status
        payload["validation_messages"] = result.messages
        if payload["validation_status"] == "Invalid":
            payload["evidence_status"] = "Rejected"
        elif payload["validation_status"] == "Warning":
            payload["evidence_status"] = "Needs Review"
        elif payload["evidence_status"] == "New":
            payload["evidence_status"] = "Validated"

        evidence = Evidence(**payload)
        try:
            self.evidence_repository.create(evidence)
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Evidence could not be created: {exc}") from exc
        self.vendor_repository.refresh_metrics(evidence.vendor_id)
        if self.event_handler is not None:
            self.event_handler.evidence_added(evidence)
        return evidence

    def get_evidence(self, evidence_id: str) -> Evidence | None:
        return self.evidence_repository.get(evidence_id)

    def list_evidence(self, **filters: Any) -> list[Evidence]:
        return self.evidence_repository.list_all(**filters)

    def add_pasted_text(
        self,
        vendor_id: str,
        title: str,
        text: str,
        publication_date: str,
        solution_categories: list[str],
        is_synthetic: bool = False,
    ) -> Evidence:
        return self.create_evidence(
            {
                "vendor_id": vendor_id,
                "source_type": "Manual Entry",
                "source_title": title,
                "publication_date": publication_date,
                "raw_text": text,
                "solution_categories": solution_categories,
                "source_authority": "Low",
                "is_synthetic": is_synthetic,
            }
        )

    def import_csv(self, content: str | bytes) -> ImportResult:
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(content)))
        return self._import_rows(rows, default_source_type="CSV Import")

    def import_json(self, content: str | bytes) -> ImportResult:
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig")
        payload = json.loads(content)
        if isinstance(payload, dict):
            rows = payload.get("evidence", [])
        else:
            rows = payload
        if not isinstance(rows, list):
            raise ValueError("JSON import must be a list or an object with an evidence list.")
        return self._import_rows(rows, default_source_type="JSON Import")

    def _import_rows(
        self,
        rows: list[dict[str, Any]],
        default_source_type: str,
    ) -> ImportResult:
        result = ImportResult()
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                result.rejected.append(
                    {"row": index, "error": "Import row must be an object."}
                )
                continue
            values = dict(row)
            values["source_type"] = values.get("source_type") or default_source_type
            try:
                result.created.append(self.create_evidence(values))
            except (KeyError, TypeError, ValueError) as exc:
                result.rejected.append({"row": index, "error": str(exc)})
        return result


class DataFoundationService:
    def __init__(
        self,
        vendor_service: VendorService,
        evidence_service: EvidenceService,
        category_repository: SolutionCategoryRepository,
    ) -> None:
        self.vendor_service = vendor_service
        self.evidence_service = evidence_service
        self.category_repository = category_repository

    def statistics(self) -> dict[str, Any]:
        vendors = self.vendor_service.list_vendors(include_archived=True)
        evidence_repository = self.evidence_service.evidence_repository
        return {
            "vendor_count": len(vendors),
            "active_vendor_count": sum(v.status == "Active" for v in vendors),
            "evidence_count": evidence_repository.count(),
            "solution_category_count": len(self.category_repository.list_all()),
            "duplicate_count": evidence_repository.duplicate_count(),
            **evidence_repository.distributions(),
        }
