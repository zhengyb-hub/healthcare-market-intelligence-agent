"""Phase 3 market-intelligence entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import utc_now


@dataclass(slots=True)
class EvidencePack:
    evidence_pack_id: str
    vendor_ids: list[str]
    evidence_ids: list[str]
    selection_criteria: dict[str, Any]
    contains_synthetic_data: bool
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class Claim:
    claim_id: str
    brief_id: str
    vendor_id: str
    claim_text: str
    claim_type: str
    evidence_ids: list[str]
    traceable: bool
    support_level: str
    review_status: str
    explanation: str = ""
    reviewed_at: str = ""
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class CompetitorBrief:
    brief_id: str
    title: str
    vendor_ids: list[str]
    brief_type: str
    evidence_pack_id: str
    claims: list[Claim]
    executive_summary: str
    sections: dict[str, list[str]]
    generated_at: str
    status: str
    model: str
    prompt_version: str
    is_demo: bool


@dataclass(slots=True)
class VendorIntelligenceProfile:
    profile_id: str
    vendor_id: str
    brief_id: str
    company_overview: str
    sections: dict[str, list[str]]
    evidence_coverage: dict[str, Any]
    last_intelligence_update: str
    is_demo: bool


@dataclass(slots=True)
class GenerationLog:
    generation_id: str
    task_type: str
    vendor_ids: list[str]
    evidence_pack_id: str
    evidence_ids: list[str]
    model: str
    prompt_version: str
    generated_at: str
    success: bool
    error: str
    is_demo: bool
