"""Claim creation, support assessment, and basic Phase 3 review actions."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from .enums import CLAIM_REVIEW_STATUSES, CLAIM_TYPES
from .intelligence_models import Claim
from .intelligence_repositories import BriefRepository, ClaimRepository, EvidencePackRepository
from .models import utc_now
from .traceability_service import TraceabilityService


class ClaimService:
    def __init__(
        self,
        repository: ClaimRepository,
        brief_repository: BriefRepository,
        pack_repository: EvidencePackRepository,
        traceability_service: TraceabilityService,
    ) -> None:
        self.repository = repository
        self.brief_repository = brief_repository
        self.pack_repository = pack_repository
        self.traceability_service = traceability_service
        self.event_handler: Any | None = None

    def create_claim(self, values: dict[str, Any]) -> Claim:
        brief_id = str(values.get("brief_id", "")).strip()
        brief = self.brief_repository.get(brief_id)
        if brief is None:
            raise ValueError(f"Unknown brief_id: {brief_id}")
        pack = self.pack_repository.get(brief.evidence_pack_id)
        if pack is None:
            raise ValueError(f"Unknown Evidence Pack: {brief.evidence_pack_id}")
        claim_text = str(values.get("claim_text", "")).strip()
        if not claim_text:
            raise ValueError("claim_text is required")
        claim_type = str(values.get("claim_type", "")).strip().upper()
        if claim_type not in CLAIM_TYPES:
            raise ValueError("Invalid claim_type")
        evidence_ids = list(dict.fromkeys(values.get("evidence_ids", []) or []))
        vendor_id = str(values.get("vendor_id", "")).strip()
        if vendor_id and vendor_id not in pack.vendor_ids:
            raise ValueError("Claim Vendor must belong to the Evidence Pack")
        assessment = self.traceability_service.assess(claim_type, evidence_ids, pack)
        now = utc_now()
        claim = Claim(
            claim_id=str(values.get("claim_id") or f"claim_{uuid4().hex}"),
            brief_id=brief_id,
            vendor_id=vendor_id,
            claim_text=claim_text,
            claim_type=claim_type,
            evidence_ids=evidence_ids,
            traceable=assessment["traceable"],
            support_level=assessment["support_level"],
            review_status=(
                "UNSUPPORTED"
                if assessment["support_level"] == "UNSUPPORTED"
                else "PENDING"
            ),
            explanation=str(values.get("explanation", assessment["reason"])).strip(),
            created_at=now,
            updated_at=now,
        )
        created = self.repository.create(claim)
        if self.event_handler is not None:
            self.event_handler.claim_generated(created, brief.is_demo)
        return created

    def review_claim(
        self,
        claim_id: str,
        action: str,
        updates: dict[str, Any] | None = None,
    ) -> Claim:
        claim = self.repository.get(claim_id)
        if claim is None:
            raise KeyError(f"Unknown claim_id: {claim_id}")
        brief = self.brief_repository.get(claim.brief_id)
        if brief is None:
            raise KeyError(f"Unknown brief_id: {claim.brief_id}")
        pack = self.pack_repository.get(brief.evidence_pack_id)
        if pack is None:
            raise KeyError(f"Unknown Evidence Pack: {brief.evidence_pack_id}")

        values = updates or {}
        claim_text = str(values.get("claim_text", claim.claim_text)).strip()
        claim_type = str(values.get("claim_type", claim.claim_type)).upper()
        evidence_ids = list(
            dict.fromkeys(values.get("evidence_ids", claim.evidence_ids) or [])
        )
        if not claim_text:
            raise ValueError("claim_text is required")
        if claim_type not in CLAIM_TYPES:
            raise ValueError("Invalid claim_type")
        assessment = self.traceability_service.assess(claim_type, evidence_ids, pack)

        normalized_action = action.strip().casefold()
        review_status_map = {
            "approve": "APPROVED",
            "reject": "REJECTED",
            "edit": "EDITED",
            "mark unsupported": "UNSUPPORTED",
            "unsupported": "UNSUPPORTED",
        }
        review_status = review_status_map.get(normalized_action)
        if review_status not in CLAIM_REVIEW_STATUSES:
            raise ValueError("Unknown review action")
        if review_status == "APPROVED" and assessment["support_level"] == "UNSUPPORTED":
            raise ValueError("Unsupported Claim cannot be approved")
        if review_status == "UNSUPPORTED":
            assessment = {
                **assessment,
                "support_level": "UNSUPPORTED",
                "traceable": False,
            }

        now = utc_now()
        reviewed = self.repository.update(
            claim_id,
            {
                "claim_text": claim_text,
                "claim_type": claim_type,
                "evidence_ids": evidence_ids,
                "support_level": assessment["support_level"],
                "traceable": assessment["traceable"],
                "review_status": review_status,
                "explanation": str(values.get("explanation", claim.explanation)),
                "reviewed_at": now,
                "updated_at": now,
            },
        )
        if self.event_handler is not None:
            self.event_handler.claim_reviewed(
                reviewed,
                action,
                str(values.get("reviewer", "local-reviewer")),
                brief.is_demo,
            )
        return reviewed
