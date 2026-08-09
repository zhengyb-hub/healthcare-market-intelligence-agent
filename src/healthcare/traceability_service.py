"""Rule-based Claim support and traceability validation."""

from __future__ import annotations

from typing import Any

from .enums import CLAIM_TYPES
from .intelligence_models import Claim, EvidencePack
from .intelligence_repositories import (
    BriefRepository,
    ClaimRepository,
    EvidencePackRepository,
)
from .repositories import EvidenceRepository


class TraceabilityService:
    def __init__(
        self,
        claim_repository: ClaimRepository,
        brief_repository: BriefRepository,
        pack_repository: EvidencePackRepository,
        evidence_repository: EvidenceRepository,
    ) -> None:
        self.claim_repository = claim_repository
        self.brief_repository = brief_repository
        self.pack_repository = pack_repository
        self.evidence_repository = evidence_repository

    def assess(
        self,
        claim_type: str,
        evidence_ids: list[str],
        pack: EvidencePack,
    ) -> dict[str, Any]:
        if claim_type not in CLAIM_TYPES:
            return {
                "support_level": "UNSUPPORTED",
                "traceable": False,
                "invalid_citations": list(evidence_ids),
                "reason": "Invalid claim type",
            }
        if not evidence_ids:
            return {
                "support_level": "UNSUPPORTED",
                "traceable": False,
                "invalid_citations": [],
                "reason": "Claim has no Evidence IDs",
            }

        pack_ids = set(pack.evidence_ids)
        invalid_citations: list[str] = []
        warning_evidence = False
        for evidence_id in evidence_ids:
            evidence = self.evidence_repository.get(evidence_id)
            if evidence is None or evidence_id not in pack_ids:
                invalid_citations.append(evidence_id)
                continue
            if evidence.validation_status not in {"Valid", "Warning"}:
                invalid_citations.append(evidence_id)
                continue
            if evidence.evidence_status not in {"Validated", "Needs Review"}:
                invalid_citations.append(evidence_id)
                continue
            if evidence.validation_status == "Warning":
                warning_evidence = True

        if invalid_citations:
            return {
                "support_level": "UNSUPPORTED",
                "traceable": False,
                "invalid_citations": sorted(set(invalid_citations)),
                "reason": "One or more citations are missing, invalid, or outside the Evidence Pack",
            }
        if claim_type == "FACT" and not warning_evidence:
            level = "SUPPORTED"
            reason = "FACT cites one or more Valid Evidence records in the Evidence Pack"
        else:
            level = "PARTIALLY_SUPPORTED"
            reason = (
                "Evidence provides a basis, but the Claim is analytical/recommendatory "
                "or includes Warning Evidence"
            )
        return {
            "support_level": level,
            "traceable": True,
            "invalid_citations": [],
            "reason": reason,
        }

    def validate_brief(self, brief_id: str, update_claims: bool = True) -> dict[str, Any]:
        brief = self.brief_repository.get(brief_id)
        if brief is None:
            raise KeyError(f"Unknown brief_id: {brief_id}")
        pack = self.pack_repository.get(brief.evidence_pack_id)
        if pack is None:
            raise KeyError(f"Unknown Evidence Pack: {brief.evidence_pack_id}")

        support_counts = {
            "SUPPORTED": 0,
            "PARTIALLY_SUPPORTED": 0,
            "UNSUPPORTED": 0,
        }
        invalid_citations: list[dict[str, str]] = []
        traceable_claims = 0
        unsupported_facts: list[str] = []
        claims = self.claim_repository.list_by_brief(brief_id)
        for claim in claims:
            assessment = self.assess(claim.claim_type, claim.evidence_ids, pack)
            if claim.review_status == "UNSUPPORTED":
                assessment = {
                    **assessment,
                    "support_level": "UNSUPPORTED",
                    "traceable": False,
                    "reason": "Human review explicitly marked this Claim unsupported",
                }
            support_counts[assessment["support_level"]] += 1
            if assessment["traceable"]:
                traceable_claims += 1
            if claim.claim_type == "FACT" and assessment["support_level"] == "UNSUPPORTED":
                unsupported_facts.append(claim.claim_id)
            for evidence_id in assessment["invalid_citations"]:
                invalid_citations.append(
                    {"claim_id": claim.claim_id, "evidence_id": evidence_id}
                )
            if update_claims and (
                claim.support_level != assessment["support_level"]
                or claim.traceable != assessment["traceable"]
            ):
                self.claim_repository.update(
                    claim.claim_id,
                    {
                        "support_level": assessment["support_level"],
                        "traceable": assessment["traceable"],
                    },
                )

        passed = not invalid_citations and not unsupported_facts
        return {
            "brief_id": brief_id,
            "result": "PASS" if passed else "FAIL",
            "total_claims": len(claims),
            "supported_claims": support_counts["SUPPORTED"],
            "partially_supported_claims": support_counts["PARTIALLY_SUPPORTED"],
            "unsupported_claims": support_counts["UNSUPPORTED"],
            "traceable_claims": traceable_claims,
            "invalid_citations_detected": len(invalid_citations),
            "invalid_citations": invalid_citations,
            "unsupported_fact_claim_ids": unsupported_facts,
        }
