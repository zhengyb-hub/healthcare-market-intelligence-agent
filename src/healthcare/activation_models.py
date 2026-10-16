"""Marketing-activation entities derived from grounded competitor evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CompetitorChange:
    change_id: str
    vendor_id: str
    change_type: str
    significance: str
    headline: str
    before_text: str
    after_text: str
    evidence_ids: list[str]
    detected_at: str
    status: str
    is_synthetic: bool
    fingerprint: str


@dataclass(slots=True)
class MarketingActionBrief:
    action_brief_id: str
    title: str
    objective: str
    audience: str
    channels: list[str]
    vendor_ids: list[str]
    evidence_ids: list[str]
    change_ids: list[str]
    sections: dict[str, list[str]]
    status: str
    created_at: str
    is_synthetic: bool

@dataclass(slots=True)
class ContentOpportunity:
    content_opportunity_id: str
    action_brief_id: str
    title: str
    channel: str
    content_format: str
    audience: str
    hook: str
    angle: str
    cta: str
    evidence_ids: list[str]
    source_change_ids: list[str]
    status: str
    created_at: str
    is_synthetic: bool


@dataclass(slots=True)
class WeeklyDigest:
    digest_id: str
    period_start: str
    period_end: str
    title: str
    sections: dict[str, list[dict[str, Any] | str]]
    change_ids: list[str]
    evidence_ids: list[str]
    created_at: str
    is_synthetic: bool
