"""Phase 4 operational product-workflow entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import utc_now


@dataclass(slots=True)
class FeedEvent:
    feed_id: str
    event_type: str
    vendor_id: str
    evidence_id: str
    brief_id: str
    title: str
    summary: str
    source_type: str
    solution_categories: list[str]
    event_date: str
    created_at: str
    importance: str
    is_synthetic: bool
    dedupe_key: str


@dataclass(slots=True)
class WatchlistEntry:
    watchlist_id: str
    vendor_id: str
    watchlist_created_at: str
    last_viewed_at: str
    evidence_count_at_last_view: int
    is_synthetic: bool


@dataclass(slots=True)
class Opportunity:
    opportunity_id: str
    opportunity_type: str
    title: str
    evidence_ids: list[str]
    related_claim_ids: list[str]
    related_vendor_ids: list[str]
    evidence_statement: str
    inference: str
    recommendation: str
    confidence_basis: str
    review_status: str
    reviewer: str
    reviewer_note: str
    reviewed_at: str
    created_at: str
    is_synthetic: bool


@dataclass(slots=True)
class EvidenceAssessment:
    evidence_id: str
    quality_level: str
    quality_score: int
    quality_components: dict[str, int]
    quality_explanation: list[str]
    freshness_status: str
    age_days: int


@dataclass(slots=True)
class DuplicateGroup:
    duplicate_group_id: str
    primary_evidence_id: str
    member_evidence_ids: list[str]
    reasons: list[str]
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class BriefReview:
    brief_id: str
    reviewer: str
    review_started_at: str
    review_completed_at: str
    review_minutes: float
    review_notes: list[str]
    revision_count: int
    updated_at: str


@dataclass(slots=True)
class ReviewNote:
    note_id: str
    claim_id: str
    reviewer: str
    note: str
    created_at: str


@dataclass(slots=True)
class SavedComparison:
    comparison_id: str
    brief_id: str
    selected_vendors: list[str]
    claim_ids: list[str]
    summary: str
    created_at: str
    is_synthetic: bool


@dataclass(slots=True)
class ExecutiveBrief:
    executive_brief_id: str
    brief_id: str
    title: str
    sections: dict[str, list[str]]
    feed_ids: list[str]
    evidence_ids: list[str]
    created_at: str
    is_synthetic: bool


@dataclass(slots=True)
class SalesEnablementOutput:
    sales_output_id: str
    brief_id: str
    title: str
    sections: dict[str, list[dict[str, Any]]]
    source_claim_ids: list[str]
    evidence_ids: list[str]
    created_at: str
    is_synthetic: bool


@dataclass(slots=True)
class UsageEvent:
    usage_event_id: str
    event_type: str
    entity_type: str
    entity_id: str
    actor: str
    metadata: dict[str, Any]
    created_at: str
    is_synthetic: bool


@dataclass(slots=True)
class AuditEvent:
    audit_event_id: str
    event_type: str
    actor: str
    entity_type: str
    entity_id: str
    related_ids: dict[str, Any]
    details: dict[str, Any]
    created_at: str
    is_synthetic: bool
