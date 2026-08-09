"""Transparent Evidence selection and reproducible Evidence Packs."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any
from uuid import uuid4

from .intelligence_models import EvidencePack
from .intelligence_repositories import EvidencePackRepository
from .models import Evidence
from .repositories import EvidenceRepository, VendorRepository


AUTHORITY_RANK = {"High": 3, "Medium": 2, "Low": 1}


class EvidencePackService:
    def __init__(
        self,
        repository: EvidencePackRepository,
        evidence_repository: EvidenceRepository,
        vendor_repository: VendorRepository,
    ) -> None:
        self.repository = repository
        self.evidence_repository = evidence_repository
        self.vendor_repository = vendor_repository

    def create_pack(
        self,
        vendor_ids: list[str],
        solution_categories: list[str] | None = None,
        source_types: list[str] | None = None,
        include_warning: bool = False,
        minimum_authority: str = "Low",
        published_since: str = "",
        max_evidence_per_vendor: int = 20,
    ) -> EvidencePack:
        unique_vendor_ids = list(dict.fromkeys(vendor_ids))
        if not unique_vendor_ids:
            raise ValueError("Evidence Pack requires at least one Vendor.")
        missing_vendors = [
            vendor_id
            for vendor_id in unique_vendor_ids
            if self.vendor_repository.get(vendor_id) is None
        ]
        if missing_vendors:
            raise ValueError("Unknown Vendor IDs: " + ", ".join(missing_vendors))

        categories = set(solution_categories or [])
        source_filter = set(source_types or [])
        minimum_rank = AUTHORITY_RANK.get(minimum_authority, 1)
        selected_by_vendor: dict[str, list[Evidence]] = defaultdict(list)

        for evidence in self.evidence_repository.list_all(include_archived=False):
            if evidence.vendor_id not in unique_vendor_ids:
                continue
            if evidence.duplicate_of_evidence_id:
                continue
            is_valid = (
                evidence.validation_status == "Valid"
                and evidence.evidence_status == "Validated"
            )
            is_allowed_warning = (
                include_warning
                and evidence.validation_status == "Warning"
                and evidence.evidence_status == "Needs Review"
            )
            if not (is_valid or is_allowed_warning):
                continue
            if categories and not categories.intersection(evidence.solution_categories):
                continue
            if source_filter and evidence.source_type not in source_filter:
                continue
            if AUTHORITY_RANK.get(evidence.source_authority, 0) < minimum_rank:
                continue
            if published_since and evidence.publication_date < published_since:
                continue
            selected_by_vendor[evidence.vendor_id].append(evidence)

        selected: list[Evidence] = []
        for vendor_id in unique_vendor_ids:
            ranked = sorted(
                selected_by_vendor[vendor_id],
                key=lambda item: (
                    -AUTHORITY_RANK.get(item.source_authority, 0),
                    -date.fromisoformat(item.publication_date).toordinal(),
                    item.source_type,
                    item.evidence_id,
                ),
            )
            selected.extend(ranked[: max(1, int(max_evidence_per_vendor))])

        pack = EvidencePack(
            evidence_pack_id=f"pack_{uuid4().hex}",
            vendor_ids=unique_vendor_ids,
            evidence_ids=[item.evidence_id for item in selected],
            selection_criteria={
                "validation_rule": (
                    "Validated Evidence only; Warning/Needs Review included"
                    if include_warning
                    else "Validated Evidence only"
                ),
                "duplicate_rule": "Exclude records with duplicate_of_evidence_id",
                "ranking_rule": (
                    "Within each Vendor: source authority High→Medium→Low, "
                    "then publication date newest→oldest, then source type and Evidence ID"
                ),
                "solution_categories": sorted(categories),
                "source_types": sorted(source_filter),
                "minimum_authority": minimum_authority,
                "published_since": published_since,
                "max_evidence_per_vendor": max(1, int(max_evidence_per_vendor)),
                "warning_evidence_included": include_warning,
            },
            contains_synthetic_data=any(item.is_synthetic for item in selected),
        )
        return self.repository.create(pack)

    def get_pack(self, evidence_pack_id: str) -> EvidencePack | None:
        return self.repository.get(evidence_pack_id)

    def evidence_for_pack(self, pack: EvidencePack) -> list[Evidence]:
        evidence: list[Evidence] = []
        for evidence_id in pack.evidence_ids:
            item = self.evidence_repository.get(evidence_id)
            if item is not None:
                evidence.append(item)
        return evidence

    def build_llm_payload(self, pack: EvidencePack) -> list[dict[str, Any]]:
        """Build the Phase 3 identity-preserving LLM Evidence payload."""
        return [
            {
                "evidence_id": item.evidence_id,
                "vendor_id": item.vendor_id,
                "source_type": item.source_type,
                "source_title": item.source_title,
                "source_url": item.source_url,
                "publication_date": item.publication_date,
                "solution_categories": item.solution_categories,
                "cleaned_text": item.cleaned_text,
                "summary": item.summary,
                "source_authority": item.source_authority,
                "validation_status": item.validation_status,
                "is_synthetic": item.is_synthetic,
            }
            for item in self.evidence_for_pack(pack)
        ]
