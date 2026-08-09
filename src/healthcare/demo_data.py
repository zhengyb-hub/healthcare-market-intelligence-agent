"""Deterministic synthetic Healthcare Vendor and Evidence dataset."""

from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
from typing import Any

from .enums import SOURCE_AUTHORITY_GUIDANCE, SOURCE_TYPES
from .models import SolutionCategory
from .repositories import SolutionCategoryRepository
from .services import DataFoundationService, EvidenceService, VendorService


TITLE_THEMES = (
    "Integrated hospital platform overview",
    "Clinical workflow solution description",
    "Synthetic hospital deployment case",
    "Regional platform procurement notice",
    "Interoperability tender announcement",
    "Healthcare data market observation",
    "Company product portfolio update",
    "Digital hospital programme release",
    "Patient service implementation news",
    "Manual analyst observation",
    "Imported solution capability record",
    "Imported data governance record",
    "Healthcare cloud service description",
    "Analytics implementation case",
    "Evidence quality control sample",
)


def load_taxonomy(path: Path) -> list[SolutionCategory]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [SolutionCategory(**item) for item in payload["categories"]]


def load_vendor_seed(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("is_synthetic") is not True:
        raise ValueError("Demo vendor data must declare is_synthetic=true.")
    return list(payload["vendors"])


def seed_demo_dataset(
    foundation: DataFoundationService,
    category_repository: SolutionCategoryRepository,
    taxonomy_path: Path,
    vendor_seed_path: Path,
    reset: bool = False,
) -> dict[str, Any]:
    """Seed 12 vendors and 180 evidence records without internet access."""
    database = category_repository.database
    if reset:
        database.reset_data()

    categories = load_taxonomy(taxonomy_path)
    for category in categories:
        category_repository.upsert(category)

    vendor_service: VendorService = foundation.vendor_service
    evidence_service: EvidenceService = foundation.evidence_service
    vendor_seed = load_vendor_seed(vendor_seed_path)

    for vendor_values in vendor_seed:
        if vendor_service.get_vendor(vendor_values["vendor_id"]) is None:
            vendor_service.create_vendor({**vendor_values, "is_synthetic": True})

    if evidence_service.evidence_repository.count() > 0:
        return foundation.statistics()

    category_ids = [category.category_id for category in categories]
    start_date = date(2024, 1, 15)

    for vendor_index, vendor_values in enumerate(vendor_seed):
        vendor_id = vendor_values["vendor_id"]
        vendor_name = vendor_values["vendor_name"]
        previous_values: dict[str, Any] | None = None

        for evidence_index in range(15):
            source_type = SOURCE_TYPES[evidence_index % len(SOURCE_TYPES)]
            publication = start_date + timedelta(
                days=vendor_index * 31 + evidence_index * 19
            )
            category_one = category_ids[(vendor_index + evidence_index) % len(category_ids)]
            category_two = category_ids[
                (vendor_index + evidence_index + 5) % len(category_ids)
            ]
            title = f"{TITLE_THEMES[evidence_index]} — {vendor_name}"
            raw_text = (
                f"Synthetic demonstration evidence for {vendor_name}. "
                f"This {source_type.lower()} record describes a fictional "
                f"{category_one.replace('_', ' ')} capability and related implementation context. "
                "It exists only to test Healthcare IT data modelling, validation, filtering, "
                "persistence, and source handling; it is not a real market claim."
            )
            linkable = source_type not in {"Manual Entry", "CSV Import", "JSON Import"}
            source_url = (
                f"https://demo.invalid/evidence/{vendor_index + 1:02d}/{evidence_index + 1:02d}"
                if linkable
                else ""
            )
            values: dict[str, Any] = {
                "evidence_id": f"evidence_demo_{vendor_index + 1:02d}_{evidence_index + 1:02d}",
                "vendor_id": vendor_id,
                "source_type": source_type,
                "source_title": title,
                "source_url": source_url,
                "publication_date": publication.isoformat(),
                "collected_at": "2026-08-09",
                "raw_text": raw_text,
                "summary": (
                    f"Synthetic {source_type.lower()} signal for {vendor_name}; "
                    "demonstration use only."
                ),
                "solution_categories": [category_one, category_two],
                "hospital_name": (
                    f"Synthetic Hospital {vendor_index + 1:02d}"
                    if source_type == "Hospital Case Study"
                    else ""
                ),
                "procurement_entity": (
                    f"Synthetic Health Authority {vendor_index + 1:02d}"
                    if source_type in {"Public Procurement", "Tender Announcement"}
                    else ""
                ),
                "project_name": (
                    f"Synthetic Healthcare Project {vendor_index + 1:02d}-{evidence_index + 1:02d}"
                    if source_type in {
                        "Hospital Case Study",
                        "Public Procurement",
                        "Tender Announcement",
                    }
                    else ""
                ),
                "contract_value": (
                    str(800_000 + vendor_index * 25_000 + evidence_index * 5_000)
                    if source_type in {"Public Procurement", "Tender Announcement"}
                    else ""
                ),
                "currency": (
                    "CNY"
                    if source_type in {"Public Procurement", "Tender Announcement"}
                    else ""
                ),
                "source_authority": SOURCE_AUTHORITY_GUIDANCE[source_type],
                "is_synthetic": True,
            }

            if evidence_index == 14 and vendor_index < 6 and previous_values:
                # Six explicit duplicates are retained and marked, never silently removed.
                values.update(
                    {
                        "source_type": previous_values["source_type"],
                        "source_title": previous_values["source_title"],
                        "source_url": previous_values["source_url"],
                        "publication_date": previous_values["publication_date"],
                        "raw_text": previous_values["raw_text"],
                        "summary": previous_values["summary"],
                        "solution_categories": previous_values["solution_categories"],
                        "source_authority": previous_values["source_authority"],
                    }
                )
            elif evidence_index == 14 and 6 <= vendor_index < 9:
                # Three warning samples: normally linkable official source without a URL.
                values.update(
                    {
                        "source_type": "Vendor Website",
                        "source_url": "",
                        "source_authority": "High",
                    }
                )
            elif evidence_index == 14 and vendor_index >= 9:
                # Three invalid samples: invalid contract values retained as Rejected.
                values.update(
                    {
                        "source_type": "Public Procurement",
                        "contract_value": "not-a-number",
                        "currency": "CNY",
                        "source_authority": "High",
                    }
                )

            evidence_service.create_evidence(values)
            previous_values = values

    return foundation.statistics()
