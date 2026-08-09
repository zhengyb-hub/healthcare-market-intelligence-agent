"""Phase 4 market-intelligence product workflow services."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from .claim_service import ClaimService
from .enums import (
    AUDIT_EVENT_TYPES,
    BRIEF_STATUSES,
    FEED_EVENT_TYPES,
    OPPORTUNITY_REVIEW_STATUSES,
    OPPORTUNITY_TYPES,
    USAGE_EVENT_TYPES,
)
from .intelligence_models import Claim, CompetitorBrief
from .intelligence_repositories import (
    BriefRepository,
    ClaimRepository,
    VendorProfileRepository,
)
from .models import Evidence, utc_now
from .repositories import EvidenceRepository, SolutionCategoryRepository, VendorRepository
from .traceability_service import TraceabilityService
from .workflow_models import (
    AuditEvent,
    BriefReview,
    DuplicateGroup,
    EvidenceAssessment,
    ExecutiveBrief,
    FeedEvent,
    Opportunity,
    ReviewNote,
    SalesEnablementOutput,
    SavedComparison,
    UsageEvent,
    WatchlistEntry,
)
from .workflow_repositories import (
    AuditRepository,
    DuplicateGroupRepository,
    ExecutiveBriefRepository,
    FeedRepository,
    OpportunityRepository,
    ReviewRepository,
    SalesEnablementRepository,
    SavedComparisonRepository,
    UsageRepository,
    WatchlistRepository,
)


FRESH_MAX_DAYS = 90
AGING_MAX_DAYS = 180
QUALITY_HIGH_MIN = 8
QUALITY_MEDIUM_MIN = 5


class UsageService:
    def __init__(self, repository: UsageRepository) -> None:
        self.repository = repository

    def record(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        actor: str = "local-user",
        metadata: dict[str, Any] | None = None,
        is_synthetic: bool = False,
    ) -> UsageEvent:
        if event_type not in USAGE_EVENT_TYPES:
            raise ValueError(f"Unsupported Usage event type: {event_type}")
        return self.repository.create(
            UsageEvent(
                usage_event_id=f"usage_{uuid4().hex}",
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                actor=actor.strip() or "local-user",
                metadata=metadata or {},
                created_at=utc_now(),
                is_synthetic=is_synthetic,
            )
        )


class AuditService:
    def __init__(self, repository: AuditRepository) -> None:
        self.repository = repository

    def record(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        actor: str = "system",
        related_ids: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
        is_synthetic: bool = False,
    ) -> AuditEvent:
        if event_type not in AUDIT_EVENT_TYPES:
            raise ValueError(f"Unsupported Audit event type: {event_type}")
        return self.repository.create(
            AuditEvent(
                audit_event_id=f"audit_{uuid4().hex}",
                event_type=event_type,
                actor=actor.strip() or "system",
                entity_type=entity_type,
                entity_id=entity_id,
                related_ids=related_ids or {},
                details=details or {},
                created_at=utc_now(),
                is_synthetic=is_synthetic,
            )
        )


class WorkflowEventService:
    """Translate real domain changes into Feed and Audit records."""

    def __init__(
        self,
        feed_repository: FeedRepository,
        audit_service: AuditService,
        usage_service: UsageService,
        vendor_repository: VendorRepository,
    ) -> None:
        self.feed_repository = feed_repository
        self.audit_service = audit_service
        self.usage_service = usage_service
        self.vendor_repository = vendor_repository

    def emit_feed(
        self,
        event_type: str,
        title: str,
        summary: str,
        vendor_id: str = "",
        evidence_id: str = "",
        brief_id: str = "",
        source_type: str = "",
        solution_categories: list[str] | None = None,
        event_date: str = "",
        importance: str = "MEDIUM",
        is_synthetic: bool = False,
        dedupe_key: str = "",
    ) -> FeedEvent:
        if event_type not in FEED_EVENT_TYPES:
            raise ValueError(f"Unsupported Feed event type: {event_type}")
        now = utc_now()
        return self.feed_repository.create(
            FeedEvent(
                feed_id=f"feed_{uuid4().hex}",
                event_type=event_type,
                vendor_id=vendor_id,
                evidence_id=evidence_id,
                brief_id=brief_id,
                title=title,
                summary=summary,
                source_type=source_type,
                solution_categories=solution_categories or [],
                event_date=event_date or now,
                created_at=now,
                importance=importance,
                is_synthetic=is_synthetic,
                dedupe_key=dedupe_key or f"{event_type}:{uuid4().hex}",
            )
        )

    def vendor_updated(self, vendor: Any, action: str = "updated") -> None:
        self.emit_feed(
            "VENDOR_UPDATED",
            f"Vendor {action}: {vendor.vendor_name}",
            vendor.company_summary,
            vendor_id=vendor.vendor_id,
            event_date=vendor.updated_at,
            importance="MEDIUM",
            is_synthetic=vendor.is_synthetic,
            dedupe_key=f"VENDOR_UPDATED:{vendor.vendor_id}:{vendor.updated_at}",
        )

    def evidence_added(self, evidence: Evidence, record_audit: bool = True) -> None:
        vendor = self.vendor_repository.get(evidence.vendor_id)
        vendor_name = vendor.vendor_name if vendor else evidence.vendor_id
        base = {
            "vendor_id": evidence.vendor_id,
            "evidence_id": evidence.evidence_id,
            "source_type": evidence.source_type,
            "solution_categories": evidence.solution_categories,
            "event_date": evidence.publication_date,
            "is_synthetic": evidence.is_synthetic,
        }
        self.emit_feed(
            "NEW_EVIDENCE",
            f"New Evidence: {vendor_name}",
            evidence.summary,
            importance="MEDIUM" if evidence.source_authority == "High" else "LOW",
            dedupe_key=f"NEW_EVIDENCE:{evidence.evidence_id}",
            **base,
        )
        if evidence.source_type == "Hospital Case Study":
            self.emit_feed(
                "NEW_CASE_STUDY",
                f"New case-study signal: {vendor_name}",
                evidence.summary,
                importance="HIGH",
                dedupe_key=f"NEW_CASE_STUDY:{evidence.evidence_id}",
                **base,
            )
        if evidence.source_type in {"Public Procurement", "Tender Announcement"}:
            self.emit_feed(
                "NEW_PROCUREMENT_SIGNAL",
                f"New procurement signal: {vendor_name}",
                evidence.summary,
                importance="HIGH",
                dedupe_key=f"NEW_PROCUREMENT_SIGNAL:{evidence.evidence_id}",
                **base,
            )
        if evidence.solution_categories:
            self.emit_feed(
                "NEW_SOLUTION_SIGNAL",
                f"Solution signal: {vendor_name}",
                "Observed categories: " + ", ".join(evidence.solution_categories),
                importance="MEDIUM",
                dedupe_key=f"NEW_SOLUTION_SIGNAL:{evidence.evidence_id}",
                **base,
            )
        if record_audit:
            self.audit_service.record(
                "EVIDENCE_ADDED",
                "Evidence",
                evidence.evidence_id,
                related_ids={"vendor_id": evidence.vendor_id},
                details={"validation_status": evidence.validation_status},
                is_synthetic=evidence.is_synthetic,
            )
            self.audit_service.record(
                "EVIDENCE_VALIDATED",
                "Evidence",
                evidence.evidence_id,
                related_ids={"vendor_id": evidence.vendor_id},
                details={
                    "validation_status": evidence.validation_status,
                    "evidence_status": evidence.evidence_status,
                },
                is_synthetic=evidence.is_synthetic,
            )

    def brief_generated(self, brief: CompetitorBrief, record_audit: bool = True) -> None:
        self.emit_feed(
            "BRIEF_GENERATED",
            f"Brief generated: {brief.title}",
            brief.executive_summary,
            vendor_id=brief.vendor_ids[0] if len(brief.vendor_ids) == 1 else "",
            brief_id=brief.brief_id,
            event_date=brief.generated_at,
            importance="HIGH",
            is_synthetic=brief.is_demo,
            dedupe_key=f"BRIEF_GENERATED:{brief.brief_id}",
        )
        if record_audit:
            self.audit_service.record(
                "COMPARISON_GENERATED" if brief.brief_type == "COMPARISON" else "BRIEF_GENERATED",
                "CompetitorBrief",
                brief.brief_id,
                related_ids={"vendor_ids": brief.vendor_ids, "evidence_pack_id": brief.evidence_pack_id},
                details={"brief_type": brief.brief_type, "prompt_version": brief.prompt_version},
                is_synthetic=brief.is_demo,
            )
            self.usage_service.record(
                "comparison_run" if brief.brief_type == "COMPARISON" else "brief_generated",
                "CompetitorBrief",
                brief.brief_id,
                metadata={"vendor_ids": brief.vendor_ids},
                is_synthetic=brief.is_demo,
            )

    def claim_generated(self, claim: Claim, is_synthetic: bool = False) -> None:
        self.audit_service.record(
            "CLAIM_GENERATED",
            "Claim",
            claim.claim_id,
            related_ids={"brief_id": claim.brief_id, "evidence_ids": claim.evidence_ids},
            details={"claim_type": claim.claim_type, "support_level": claim.support_level},
            is_synthetic=is_synthetic,
        )

    def claim_reviewed(
        self,
        claim: Claim,
        action: str,
        reviewer: str = "local-reviewer",
        is_synthetic: bool = False,
    ) -> None:
        self.emit_feed(
            "CLAIM_REVIEWED",
            f"Claim reviewed: {claim.claim_type}",
            claim.claim_text,
            vendor_id=claim.vendor_id,
            brief_id=claim.brief_id,
            event_date=claim.reviewed_at or utc_now(),
            importance="MEDIUM",
            is_synthetic=is_synthetic,
            dedupe_key=f"CLAIM_REVIEWED:{claim.claim_id}:{claim.reviewed_at}",
        )
        self.audit_service.record(
            "CLAIM_EDITED" if action.strip().casefold() == "edit" else "CLAIM_REVIEWED",
            "Claim",
            claim.claim_id,
            actor=reviewer,
            related_ids={"brief_id": claim.brief_id, "evidence_ids": claim.evidence_ids},
            details={"review_status": claim.review_status, "support_level": claim.support_level},
            is_synthetic=is_synthetic,
        )

    def opportunity_generated(self, opportunity: Opportunity) -> None:
        self.emit_feed(
            "IMPORTANT_INTELLIGENCE",
            opportunity.title,
            opportunity.inference,
            vendor_id=(opportunity.related_vendor_ids[0] if len(opportunity.related_vendor_ids) == 1 else ""),
            event_date=opportunity.created_at,
            importance="HIGH",
            is_synthetic=opportunity.is_synthetic,
            dedupe_key=f"IMPORTANT_INTELLIGENCE:{opportunity.opportunity_id}",
        )
        self.audit_service.record(
            "OPPORTUNITY_GENERATED",
            "Opportunity",
            opportunity.opportunity_id,
            related_ids={
                "vendor_ids": opportunity.related_vendor_ids,
                "claim_ids": opportunity.related_claim_ids,
                "evidence_ids": opportunity.evidence_ids,
            },
            details={"opportunity_type": opportunity.opportunity_type},
            is_synthetic=opportunity.is_synthetic,
        )


class EvidenceQualityService:
    """Transparent rule-based Evidence quality and freshness assessment."""

    def __init__(self, evidence_repository: EvidenceRepository) -> None:
        self.evidence_repository = evidence_repository

    @staticmethod
    def freshness(publication_date: str, as_of: date | None = None) -> tuple[str, int]:
        current = as_of or date.today()
        age_days = max(0, (current - date.fromisoformat(publication_date)).days)
        if age_days <= FRESH_MAX_DAYS:
            return "FRESH", age_days
        if age_days <= AGING_MAX_DAYS:
            return "AGING", age_days
        return "OUTDATED", age_days

    def assess(self, evidence: Evidence, as_of: date | None = None) -> EvidenceAssessment:
        freshness_status, age_days = self.freshness(evidence.publication_date, as_of)
        authority = {"High": 3, "Medium": 2, "Low": 1}.get(evidence.source_authority, 0)
        recency = {"FRESH": 3, "AGING": 2, "OUTDATED": 0}[freshness_status]
        completeness_fields = [
            evidence.source_title,
            evidence.publication_date,
            evidence.source_type,
            evidence.cleaned_text or evidence.raw_text,
            evidence.vendor_id,
            evidence.solution_categories,
        ]
        complete_count = sum(bool(value) for value in completeness_fields)
        completeness = 2 if complete_count == 6 else 1 if complete_count >= 4 else 0
        traceability = 1 if evidence.traceable else 0
        relevance = 1 if evidence.solution_categories else 0
        components = {
            "source_authority": authority,
            "recency": recency,
            "completeness": completeness,
            "traceability": traceability,
            "relevance": relevance,
        }
        score = sum(components.values())
        level = "HIGH" if score >= QUALITY_HIGH_MIN else "MEDIUM" if score >= QUALITY_MEDIUM_MIN else "LOW"
        return EvidenceAssessment(
            evidence_id=evidence.evidence_id,
            quality_level=level,
            quality_score=score,
            quality_components=components,
            quality_explanation=[
                f"Source authority {evidence.source_authority}: {authority}/3",
                f"Freshness {freshness_status} ({age_days} days): {recency}/3",
                f"Completeness {complete_count}/6 fields: {completeness}/2",
                f"Traceable source URL: {traceability}/1",
                f"Solution relevance metadata: {relevance}/1",
                f"Total {score}/10; HIGH >= {QUALITY_HIGH_MIN}, MEDIUM >= {QUALITY_MEDIUM_MIN}",
            ],
            freshness_status=freshness_status,
            age_days=age_days,
        )

    def distribution(self, as_of: date | None = None) -> dict[str, dict[str, int]]:
        assessments = [self.assess(item, as_of) for item in self.evidence_repository.list_all(include_archived=True)]
        return {
            "quality": dict(Counter(item.quality_level for item in assessments)),
            "freshness": dict(Counter(item.freshness_status for item in assessments)),
        }

    def vendor_freshness(self, vendor_id: str, as_of: date | None = None) -> dict[str, Any]:
        evidence = self.evidence_repository.list_all(vendor_id=vendor_id)
        assessments = [self.assess(item, as_of) for item in evidence]
        counts = Counter(item.freshness_status for item in assessments)
        latest = max((item.publication_date for item in evidence), default="")
        return {
            "latest_evidence_date": latest,
            "fresh_evidence_count": counts.get("FRESH", 0),
            "aging_evidence_count": counts.get("AGING", 0),
            "outdated_evidence_count": counts.get("OUTDATED", 0),
            "needs_intelligence_refresh": not assessments or counts.get("FRESH", 0) == 0,
        }


class WatchlistService:
    def __init__(
        self,
        repository: WatchlistRepository,
        vendor_repository: VendorRepository,
        evidence_repository: EvidenceRepository,
        brief_repository: BriefRepository,
        profile_repository: VendorProfileRepository,
        feed_repository: FeedRepository,
        quality_service: EvidenceQualityService,
        usage_service: UsageService,
    ) -> None:
        self.repository = repository
        self.vendor_repository = vendor_repository
        self.evidence_repository = evidence_repository
        self.brief_repository = brief_repository
        self.profile_repository = profile_repository
        self.feed_repository = feed_repository
        self.quality_service = quality_service
        self.usage_service = usage_service

    def follow(self, vendor_id: str, actor: str = "local-user") -> WatchlistEntry:
        existing = self.repository.get_by_vendor(vendor_id)
        if existing:
            return existing
        vendor = self.vendor_repository.get(vendor_id)
        if vendor is None:
            raise ValueError(f"Unknown vendor_id: {vendor_id}")
        now = utc_now()
        count = len(self.evidence_repository.list_all(vendor_id=vendor_id))
        entry = self.repository.create(
            WatchlistEntry(
                watchlist_id=f"watchlist_{uuid4().hex}",
                vendor_id=vendor_id,
                watchlist_created_at=now,
                last_viewed_at=now,
                evidence_count_at_last_view=count,
                is_synthetic=vendor.is_synthetic,
            )
        )
        self.usage_service.record(
            "watchlist_add", "Vendor", vendor_id, actor=actor, is_synthetic=vendor.is_synthetic
        )
        return entry

    def unfollow(self, vendor_id: str) -> bool:
        return self.repository.delete(vendor_id)

    def mark_viewed(self, vendor_id: str) -> WatchlistEntry:
        count = len(self.evidence_repository.list_all(vendor_id=vendor_id))
        return self.repository.update_view(vendor_id, utc_now(), count)

    def details(self, vendor_id: str) -> dict[str, Any]:
        entry = self.repository.get_by_vendor(vendor_id)
        vendor = self.vendor_repository.get(vendor_id)
        if entry is None or vendor is None:
            raise KeyError(f"Vendor is not followed: {vendor_id}")
        evidence = self.evidence_repository.list_all(vendor_id=vendor_id)
        procurements = [
            item for item in evidence
            if item.source_type in {"Public Procurement", "Tender Announcement"}
        ]
        briefs = [item for item in self.brief_repository.list_all() if vendor_id in item.vendor_ids]
        profiles = self.profile_repository.list_all(vendor_id)
        freshness = self.quality_service.vendor_freshness(vendor_id)
        new_count = max(0, len(evidence) - entry.evidence_count_at_last_view)
        recent_events = [
            event for event in self.feed_repository.list_all(vendor_id=vendor_id, limit=None)
            if event.created_at >= entry.last_viewed_at
        ]
        alerts: list[str] = []
        if new_count:
            alerts.append(f"{new_count} new evidence record(s)")
        if any(event.event_type == "NEW_PROCUREMENT_SIGNAL" for event in recent_events):
            alerts.append("New procurement activity")
        if any(event.event_type == "NEW_SOLUTION_SIGNAL" for event in recent_events):
            alerts.append("New solution category observed")
        if any(event.event_type == "BRIEF_GENERATED" for event in recent_events):
            alerts.append("Vendor profile or Brief updated")
        return {
            "entry": entry,
            "vendor": vendor,
            "primary_solution_areas": vendor.solution_categories,
            "evidence_count": len(evidence),
            "new_evidence_since_last_view": new_count,
            "latest_procurement_signal": procurements[0] if procurements else None,
            "latest_brief": briefs[0] if briefs else None,
            "latest_intelligence_update": (
                profiles[0].last_intelligence_update if profiles else ""
            ),
            "freshness": freshness,
            "alerts": alerts,
        }

    def list_details(self) -> list[dict[str, Any]]:
        return [self.details(entry.vendor_id) for entry in self.repository.list_all()]


class MarketMapService:
    def __init__(
        self,
        vendor_repository: VendorRepository,
        evidence_repository: EvidenceRepository,
        category_repository: SolutionCategoryRepository,
    ) -> None:
        self.vendor_repository = vendor_repository
        self.evidence_repository = evidence_repository
        self.category_repository = category_repository

    def build(
        self,
        vendor_ids: list[str] | None = None,
        category_ids: list[str] | None = None,
        minimum_evidence_count: int = 1,
    ) -> dict[str, Any]:
        vendors = self.vendor_repository.list_all()
        selected_vendors = set(vendor_ids or [vendor.vendor_id for vendor in vendors])
        categories = self.category_repository.list_all()
        selected_categories = set(category_ids or [item.category_id for item in categories])
        grouped: dict[tuple[str, str], list[Evidence]] = defaultdict(list)
        for evidence in self.evidence_repository.list_all():
            if evidence.vendor_id not in selected_vendors:
                continue
            if evidence.validation_status != "Valid" or evidence.evidence_status != "Validated":
                continue
            if evidence.duplicate_of_evidence_id:
                continue
            for category_id in evidence.solution_categories:
                if category_id in selected_categories:
                    grouped[(evidence.vendor_id, category_id)].append(evidence)
        cells: list[dict[str, Any]] = []
        threshold = max(1, int(minimum_evidence_count))
        for (vendor_id, category_id), evidence in sorted(grouped.items()):
            if len(evidence) < threshold:
                continue
            has_high = any(item.source_authority == "High" for item in evidence)
            support_status = (
                "SUPPORTED" if has_high or len(evidence) >= 2 else "PARTIALLY_SUPPORTED"
            )
            cells.append(
                {
                    "vendor_id": vendor_id,
                    "category_id": category_id,
                    "evidence_count": len(evidence),
                    "support_status": support_status,
                    "evidence_ids": [item.evidence_id for item in evidence],
                    "contains_synthetic_data": any(item.is_synthetic for item in evidence),
                }
            )
        density = Counter(cell["category_id"] for cell in cells)
        return {
            "vendor_ids": sorted(selected_vendors),
            "category_ids": sorted(selected_categories),
            "cells": cells,
            "competitive_density": dict(density),
            "support_rule": (
                "SUPPORTED when a cell has High-authority Evidence or at least two Validated records; "
                "otherwise PARTIALLY_SUPPORTED"
            ),
        }


class DuplicateGroupService:
    def __init__(
        self,
        repository: DuplicateGroupRepository,
        evidence_repository: EvidenceRepository,
    ) -> None:
        self.repository = repository
        self.evidence_repository = evidence_repository

    def rebuild(self) -> list[DuplicateGroup]:
        evidence = self.evidence_repository.list_all(include_archived=True)
        by_id = {item.evidence_id: item for item in evidence}
        parent = {item.evidence_id: item.evidence_id for item in evidence}

        def find(item_id: str) -> str:
            while parent[item_id] != item_id:
                parent[item_id] = parent[parent[item_id]]
                item_id = parent[item_id]
            return item_id

        def union(left: str, right: str) -> None:
            root_left, root_right = find(left), find(right)
            if root_left != root_right:
                parent[root_right] = root_left

        hashes: dict[str, str] = {}
        urls: dict[str, str] = {}
        for item in evidence:
            if item.duplicate_of_evidence_id in by_id:
                union(item.evidence_id, item.duplicate_of_evidence_id)
            if item.content_hash:
                if item.content_hash in hashes:
                    union(item.evidence_id, hashes[item.content_hash])
                else:
                    hashes[item.content_hash] = item.evidence_id
            if item.source_url:
                if item.source_url in urls:
                    union(item.evidence_id, urls[item.source_url])
                else:
                    urls[item.source_url] = item.evidence_id

        clusters: dict[str, list[Evidence]] = defaultdict(list)
        for item in evidence:
            clusters[find(item.evidence_id)].append(item)
        groups: list[DuplicateGroup] = []
        authority = {"High": 3, "Medium": 2, "Low": 1}
        for members in clusters.values():
            if len(members) < 2:
                continue
            primary = sorted(
                members,
                key=lambda item: (
                    -(item.validation_status == "Valid"),
                    -authority.get(item.source_authority, 0),
                    -int(item.traceable),
                    item.created_at,
                    item.evidence_id,
                ),
            )[0]
            reasons = sorted({reason for item in members for reason in item.duplicate_reasons})
            groups.append(
                DuplicateGroup(
                    duplicate_group_id=f"dupgroup_{primary.evidence_id}",
                    primary_evidence_id=primary.evidence_id,
                    member_evidence_ids=sorted(item.evidence_id for item in members),
                    reasons=reasons or ["Shared URL or Content Hash"],
                )
            )
        self.repository.replace_all(groups)
        return self.repository.list_all()


class OpportunityService:
    def __init__(
        self,
        repository: OpportunityRepository,
        market_map_service: MarketMapService,
        evidence_repository: EvidenceRepository,
        claim_repository: ClaimRepository,
        brief_repository: BriefRepository,
        category_repository: SolutionCategoryRepository,
        watchlist_repository: WatchlistRepository,
        event_service: WorkflowEventService,
    ) -> None:
        self.repository = repository
        self.market_map_service = market_map_service
        self.evidence_repository = evidence_repository
        self.claim_repository = claim_repository
        self.brief_repository = brief_repository
        self.category_repository = category_repository
        self.watchlist_repository = watchlist_repository
        self.event_service = event_service

    def _create(
        self,
        opportunity_type: str,
        title: str,
        evidence_ids: list[str],
        claim_ids: list[str],
        vendor_ids: list[str],
        evidence_statement: str,
        inference: str,
        recommendation: str,
        confidence_basis: str,
    ) -> Opportunity:
        if opportunity_type not in OPPORTUNITY_TYPES:
            raise ValueError("Invalid opportunity_type")
        unique_evidence = list(dict.fromkeys(evidence_ids))
        missing = [item for item in unique_evidence if self.evidence_repository.get(item) is None]
        if missing:
            raise ValueError("Opportunity cites unknown Evidence: " + ", ".join(missing))
        if not unique_evidence:
            raise ValueError("Opportunity requires an Evidence basis")
        evidence = [self.evidence_repository.get(item) for item in unique_evidence]
        item = self.repository.create(
            Opportunity(
                opportunity_id=f"opportunity_{uuid4().hex}",
                opportunity_type=opportunity_type,
                title=title,
                evidence_ids=unique_evidence,
                related_claim_ids=list(dict.fromkeys(claim_ids)),
                related_vendor_ids=list(dict.fromkeys(vendor_ids)),
                evidence_statement=evidence_statement,
                inference=inference,
                recommendation=recommendation,
                confidence_basis=confidence_basis,
                review_status="PENDING",
                reviewer="",
                reviewer_note="",
                reviewed_at="",
                created_at=utc_now(),
                is_synthetic=any(record and record.is_synthetic for record in evidence),
            )
        )
        self.event_service.opportunity_generated(item)
        return item

    def generate(self, vendor_ids: list[str] | None = None) -> list[Opportunity]:
        followed = [item.vendor_id for item in self.watchlist_repository.list_all()]
        selected_vendors = list(dict.fromkeys(vendor_ids or followed))
        if len(selected_vendors) < 2:
            selected_vendors = self.market_map_service.build()["vendor_ids"][:5]
        market_map = self.market_map_service.build(vendor_ids=selected_vendors)
        cells = market_map["cells"]
        if not cells:
            return []
        category_names = {
            item.category_id: item.name for item in self.category_repository.list_all()
        }
        by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for cell in cells:
            by_category[cell["category_id"]].append(cell)
        low_density_category, low_cells = sorted(
            by_category.items(), key=lambda pair: (len(pair[1]), pair[0])
        )[0]
        basis_ids = [eid for cell in low_cells for eid in cell["evidence_ids"]][:8]
        covered_vendors = {cell["vendor_id"] for cell in low_cells}
        missing_vendors = [item for item in selected_vendors if item not in covered_vendors]
        category_name = category_names.get(low_density_category, low_density_category)
        has_solution_white_space = len(covered_vendors) < len(selected_vendors)
        result = [
            self._create(
                "SOLUTION_WHITE_SPACE",
                (
                    f"Monitored-set solution white space: {category_name}"
                    if has_solution_white_space
                    else "No solution white space detected in the monitored set"
                ),
                basis_ids,
                [],
                selected_vendors,
                f"{len(covered_vendors)} of {len(selected_vendors)} monitored Vendors have Validated Evidence in {category_name}.",
                (
                    f"{category_name} is less densely evidenced within this monitored Vendor set; this is not a whole-market conclusion."
                    if has_solution_white_space
                    else "Every monitored Vendor has at least one qualifying cell in every currently mapped category, so the current dataset does not support a solution white-space claim."
                ),
                (
                    f"Investigate whether {category_name} merits additional positioning research and primary-source collection."
                    if has_solution_white_space
                    else "Expand the monitored Vendor/source set before asserting solution white space."
                ),
                "Deterministic Vendor-by-category counts from Validated, non-duplicate Evidence.",
            ),
            self._create(
                "EVIDENCE_GAP",
                (
                    f"Evidence gap for {category_name}"
                    if missing_vendors
                    else f"Evidence depth check for {category_name}"
                ),
                basis_ids,
                [],
                missing_vendors or selected_vendors,
                (
                    f"Peer Evidence exists for {category_name}, while {len(missing_vendors)} monitored Vendor(s) have no qualifying cell."
                    if missing_vendors
                    else f"All monitored Vendors have a qualifying {category_name} cell, but Evidence depth and freshness still vary."
                ),
                (
                    "The absence may reflect a collection gap or a real coverage difference; current data cannot distinguish the two."
                    if missing_vendors
                    else "No binary coverage gap is detected; a quality/freshness gap may still exist and requires record-level assessment."
                ),
                (
                    "Collect or validate primary Evidence for the uncovered Vendors before making a competitive claim."
                    if missing_vendors
                    else "Prioritize refreshed primary Evidence for the thinnest or oldest cells before deeper comparison."
                ),
                (
                    "Gap is defined as zero qualifying Market Map cells while peer cells cite the listed Evidence."
                    if missing_vendors
                    else "No zero-cell gap exists; the item is explicitly downgraded to an Evidence depth/freshness check."
                ),
            ),
        ]

        claims = [
            claim for brief in self.brief_repository.list_all()
            if any(vendor_id in selected_vendors for vendor_id in brief.vendor_ids)
            for claim in brief.claims
            if claim.evidence_ids
        ]
        analytical = [claim for claim in claims if claim.claim_type == "INFERENCE"]
        recommendations = [claim for claim in claims if claim.claim_type == "RECOMMENDATION"]
        message_basis = analytical[:3] or claims[:3]
        if message_basis:
            result.append(
                self._create(
                    "MESSAGING_WHITE_SPACE",
                    "Messaging white-space hypothesis",
                    [eid for claim in message_basis for eid in claim.evidence_ids][:10],
                    [claim.claim_id for claim in message_basis],
                    selected_vendors,
                    f"{len(message_basis)} Evidence-linked analytical messaging Claim(s) were reused from current Briefs.",
                    "Current messaging themes may leave room for a more explicitly evidence-led differentiation narrative.",
                    "Test an evidence-led message with Marketing; do not present the hypothesis as a measured market preference.",
                    "Based on existing INFERENCE Claims and their stored Evidence links, not a new LLM score.",
                )
            )
            result.append(
                self._create(
                    "COMPETITOR_WEAKNESS",
                    "Competitor weakness research hypothesis",
                    [eid for claim in message_basis for eid in claim.evidence_ids][:10],
                    [claim.claim_id for claim in message_basis],
                    selected_vendors,
                    "Current Briefs contain partially supported competitive-risk or positioning interpretations.",
                    "The interpretations may indicate a differentiable weakness, but require reviewer confirmation and more direct Evidence.",
                    "Use the cited Claims as discovery prompts and collect direct customer or procurement Evidence before external use.",
                    "Rule selects Evidence-linked INFERENCE Claims; it does not label a Vendor weakness as fact.",
                )
            )
        sales_basis = recommendations[:3] or claims[:3]
        if sales_basis:
            result.append(
                self._create(
                    "SALES_ENABLEMENT",
                    "Evidence-backed sales enablement opportunity",
                    [eid for claim in sales_basis for eid in claim.evidence_ids][:10],
                    [claim.claim_id for claim in sales_basis],
                    selected_vendors,
                    f"{len(sales_basis)} existing Evidence-linked recommendation Claim(s) can be translated into discovery questions and talking points.",
                    "The current intelligence can support a more consistent evidence-aware sales conversation.",
                    "Create talking points that preserve FACT/INFERENCE/RECOMMENDATION labels and cite the underlying Evidence.",
                    "Reuses stored recommendation Claims and their validated citations.",
                )
            )
        return result

    def review(self, opportunity_id: str, status: str, reviewer: str, note: str = "") -> Opportunity:
        normalized = status.strip().upper()
        if normalized not in OPPORTUNITY_REVIEW_STATUSES:
            raise ValueError("Invalid Opportunity review status")
        if not reviewer.strip():
            raise ValueError("Reviewer name is required")
        return self.repository.update_review(
            opportunity_id, normalized, reviewer.strip(), note.strip(), utc_now()
        )


class BriefWorkflowService:
    def __init__(
        self,
        brief_repository: BriefRepository,
        claim_repository: ClaimRepository,
        claim_service: ClaimService,
        review_repository: ReviewRepository,
        evidence_repository: EvidenceRepository,
        traceability_service: TraceabilityService,
        event_service: WorkflowEventService,
        audit_service: AuditService,
        usage_service: UsageService,
    ) -> None:
        self.brief_repository = brief_repository
        self.claim_repository = claim_repository
        self.claim_service = claim_service
        self.review_repository = review_repository
        self.evidence_repository = evidence_repository
        self.traceability_service = traceability_service
        self.event_service = event_service
        self.audit_service = audit_service
        self.usage_service = usage_service

    def _metadata(self, brief_id: str) -> BriefReview:
        existing = self.review_repository.get(brief_id)
        return existing or BriefReview(
            brief_id=brief_id,
            reviewer="",
            review_started_at="",
            review_completed_at="",
            review_minutes=0,
            review_notes=[],
            revision_count=0,
            updated_at=utc_now(),
        )

    def start_review(self, brief_id: str, reviewer: str, note: str = "") -> CompetitorBrief:
        brief = self.brief_repository.get(brief_id)
        if brief is None:
            raise KeyError(f"Unknown brief_id: {brief_id}")
        if brief.status not in {"DRAFT", "NEEDS_REVISION", "IN_REVIEW"}:
            raise ValueError(f"Cannot start review from {brief.status}")
        if not reviewer.strip():
            raise ValueError("Reviewer name is required")
        now = utc_now()
        meta = self._metadata(brief_id)
        meta.reviewer = reviewer.strip()
        meta.review_started_at = meta.review_started_at or now
        meta.review_completed_at = ""
        if note.strip():
            meta.review_notes.append(note.strip())
        meta.updated_at = now
        self.review_repository.upsert(meta)
        return self.brief_repository.update_status(brief_id, "IN_REVIEW")

    def review_claim(
        self,
        claim_id: str,
        action: str,
        reviewer: str,
        updates: dict[str, Any] | None = None,
        note: str = "",
    ) -> Claim:
        if not reviewer.strip():
            raise ValueError("Reviewer name is required")
        values = dict(updates or {})
        values["reviewer"] = reviewer.strip()
        claim = self.claim_service.review_claim(claim_id, action, values)
        if note.strip():
            self.review_repository.add_claim_note(
                ReviewNote(
                    note_id=f"reviewnote_{uuid4().hex}",
                    claim_id=claim_id,
                    reviewer=reviewer.strip(),
                    note=note.strip(),
                    created_at=utc_now(),
                )
            )
        return claim

    def return_for_revision(self, brief_id: str, reviewer: str, note: str) -> CompetitorBrief:
        brief = self.brief_repository.get(brief_id)
        if brief is None or brief.status != "IN_REVIEW":
            raise ValueError("Brief must be IN_REVIEW")
        if not note.strip():
            raise ValueError("Revision note is required")
        meta = self._metadata(brief_id)
        meta.reviewer = reviewer.strip() or meta.reviewer
        meta.review_notes.append(note.strip())
        meta.revision_count += 1
        meta.updated_at = utc_now()
        self.review_repository.upsert(meta)
        return self.brief_repository.update_status(brief_id, "NEEDS_REVISION")

    def approve(self, brief_id: str, reviewer: str, note: str = "") -> CompetitorBrief:
        brief = self.brief_repository.get(brief_id)
        if brief is None or brief.status != "IN_REVIEW":
            raise ValueError("Brief must be IN_REVIEW")
        if not reviewer.strip():
            raise ValueError("Reviewer name is required")
        report = self.traceability_service.validate_brief(brief_id)
        if report["result"] != "PASS":
            raise ValueError("Brief cannot be approved while traceability fails")
        pending = [claim for claim in self.claim_repository.list_by_brief(brief_id) if claim.review_status == "PENDING"]
        if pending:
            raise ValueError("All supported and partially supported Claims must be reviewed")
        now = utc_now()
        meta = self._metadata(brief_id)
        meta.reviewer = reviewer.strip()
        if note.strip():
            meta.review_notes.append(note.strip())
        meta.review_completed_at = now
        if meta.review_started_at:
            started = datetime.fromisoformat(meta.review_started_at)
            completed = datetime.fromisoformat(now)
            meta.review_minutes = max(0, (completed - started).total_seconds() / 60)
        meta.updated_at = now
        self.review_repository.upsert(meta)
        result = self.brief_repository.update_status(brief_id, "APPROVED")
        self.audit_service.record(
            "BRIEF_APPROVED",
            "CompetitorBrief",
            brief_id,
            actor=reviewer.strip(),
            related_ids={"vendor_ids": brief.vendor_ids},
            details={"review_minutes": meta.review_minutes},
            is_synthetic=brief.is_demo,
        )
        self.usage_service.record(
            "brief_reviewed", "CompetitorBrief", brief_id,
            actor=reviewer.strip(), is_synthetic=brief.is_demo,
        )
        return result

    def finalize(self, brief_id: str) -> CompetitorBrief:
        brief = self.brief_repository.get(brief_id)
        if brief is None or brief.status != "APPROVED":
            raise ValueError("Brief must be APPROVED before FINAL")
        return self.brief_repository.update_status(brief_id, "FINAL")

    def queue(self) -> dict[str, list[Any]]:
        return {
            "briefs_awaiting_review": [
                brief for brief in self.brief_repository.list_all()
                if brief.status in {"DRAFT", "IN_REVIEW", "NEEDS_REVISION"}
            ],
            "claims_awaiting_review": self.claim_repository.list_all(review_status="PENDING"),
            "unsupported_claims": self.claim_repository.list_all(support_level="UNSUPPORTED"),
            "partially_supported_claims": self.claim_repository.list_all(support_level="PARTIALLY_SUPPORTED"),
            "evidence_needing_validation": [
                item for item in self.evidence_repository.list_all(include_archived=True)
                if item.validation_status in {"Warning", "Invalid"}
            ],
        }


class SavedComparisonService:
    def __init__(self, repository: SavedComparisonRepository, brief_repository: BriefRepository) -> None:
        self.repository = repository
        self.brief_repository = brief_repository

    def save(self, brief_id: str) -> SavedComparison:
        existing = self.repository.get_by_brief(brief_id)
        if existing:
            return existing
        brief = self.brief_repository.get(brief_id)
        if brief is None or brief.brief_type != "COMPARISON":
            raise ValueError("Only a Comparison Brief can be saved")
        return self.repository.create(
            SavedComparison(
                comparison_id=f"comparison_{uuid4().hex}",
                brief_id=brief.brief_id,
                selected_vendors=brief.vendor_ids,
                claim_ids=[claim.claim_id for claim in brief.claims],
                summary=brief.executive_summary,
                created_at=utc_now(),
                is_synthetic=brief.is_demo,
            )
        )


class ExecutiveBriefService:
    def __init__(
        self,
        repository: ExecutiveBriefRepository,
        brief_repository: BriefRepository,
        feed_repository: FeedRepository,
    ) -> None:
        self.repository = repository
        self.brief_repository = brief_repository
        self.feed_repository = feed_repository

    @staticmethod
    def _pick(brief: CompetitorBrief, names: set[str], fallback: list[str]) -> list[str]:
        picked = [
            claim_id for section, claim_ids in brief.sections.items()
            if section in names for claim_id in claim_ids
        ]
        return list(dict.fromkeys(picked or fallback))[:4]

    def create(self, brief_id: str) -> ExecutiveBrief:
        existing = self.repository.get_by_brief(brief_id)
        if existing:
            return existing
        brief = self.brief_repository.get(brief_id)
        if brief is None:
            raise KeyError(f"Unknown brief_id: {brief_id}")
        valid_claims = [
            claim for claim in brief.claims
            if claim.review_status != "REJECTED"
            and not (claim.claim_type == "FACT" and claim.support_level == "UNSUPPORTED")
        ]
        facts = [claim.claim_id for claim in valid_claims if claim.claim_type == "FACT"]
        recommendations = [
            claim.claim_id for claim in valid_claims if claim.claim_type == "RECOMMENDATION"
        ]
        fallback = [claim.claim_id for claim in valid_claims]
        sections = {
            "Competitor Snapshot": facts[:3] or fallback[:3],
            "What's Changed": facts[:2] or fallback[:2],
            "Top Strengths": self._pick(brief, {"Competitive Strengths"}, fallback),
            "Top Risks": self._pick(brief, {"Competitive Risks", "Competitive Weaknesses"}, fallback),
            "Key Procurement / Case Signals": self._pick(
                brief, {"Procurement Signals", "Institutional / Hospital Signals", "Case and Procurement Evidence"}, facts
            ),
            "Positioning Insight": self._pick(brief, {"Positioning", "Market Positioning", "Positioning Analysis"}, fallback),
            "Top Opportunity": recommendations[:2] or fallback[:2],
            "Recommended Action": recommendations[:3] or fallback[:3],
            "Evidence Sources": facts[:4] or fallback[:4],
        }
        selected_ids = {claim_id for ids in sections.values() for claim_id in ids}
        selected_claims = [claim for claim in valid_claims if claim.claim_id in selected_ids]
        evidence_ids = list(dict.fromkeys(
            evidence_id for claim in selected_claims for evidence_id in claim.evidence_ids
        ))
        feed_ids = [
            event.feed_id for event in self.feed_repository.list_all(limit=None)
            if event.brief_id == brief_id or event.vendor_id in brief.vendor_ids
        ][:5]
        return self.repository.create(
            ExecutiveBrief(
                executive_brief_id=f"executive_{uuid4().hex}",
                brief_id=brief_id,
                title=f"Executive Brief — {brief.title}",
                sections=sections,
                feed_ids=feed_ids,
                evidence_ids=evidence_ids,
                created_at=utc_now(),
                is_synthetic=brief.is_demo,
            )
        )


class SalesEnablementService:
    def __init__(self, repository: SalesEnablementRepository, brief_repository: BriefRepository) -> None:
        self.repository = repository
        self.brief_repository = brief_repository

    @staticmethod
    def _items(claims: list[Claim]) -> list[dict[str, Any]]:
        return [
            {
                "text": claim.claim_text,
                "claim_type": claim.claim_type,
                "support_level": claim.support_level,
                "evidence_ids": claim.evidence_ids,
                "source_claim_id": claim.claim_id,
            }
            for claim in claims
        ]

    def create(self, brief_id: str) -> SalesEnablementOutput:
        existing = self.repository.get_by_brief(brief_id)
        if existing:
            return existing
        brief = self.brief_repository.get(brief_id)
        if brief is None:
            raise KeyError(f"Unknown brief_id: {brief_id}")
        claims = [
            claim for claim in brief.claims
            if claim.review_status != "REJECTED"
            and claim.evidence_ids
            and not (claim.claim_type == "FACT" and claim.support_level == "UNSUPPORTED")
        ]
        facts = [claim for claim in claims if claim.claim_type == "FACT"]
        inferences = [claim for claim in claims if claim.claim_type == "INFERENCE"]
        recommendations = [claim for claim in claims if claim.claim_type == "RECOMMENDATION"]
        basis = recommendations or inferences or facts
        discovery = [
            {
                "text": f"Ask the customer how this observed competitor signal affects their priorities: {claim.claim_text}",
                "claim_type": "RECOMMENDATION",
                "support_level": "PARTIALLY_SUPPORTED",
                "evidence_ids": claim.evidence_ids,
                "source_claim_id": claim.claim_id,
            }
            for claim in basis[:3]
        ]
        talking = [
            {
                "text": f"Use the cited Evidence to discuss differentiation without overstating the market: {claim.claim_text}",
                "claim_type": "RECOMMENDATION",
                "support_level": "PARTIALLY_SUPPORTED",
                "evidence_ids": claim.evidence_ids,
                "source_claim_id": claim.claim_id,
            }
            for claim in basis[:3]
        ]
        sections = {
            "How We Differentiate": self._items(recommendations[:3] or inferences[:3]),
            "Observed Competitor Strengths": self._items(facts[:3] + inferences[:2]),
            "Observed Competitor Weaknesses": self._items(inferences[-3:]),
            "Potential Customer Concerns": self._items(inferences[:3]),
            "Suggested Discovery Questions": discovery,
            "Suggested Talking Points": talking,
        }
        source_claim_ids = list(dict.fromkeys(
            item["source_claim_id"] for items in sections.values() for item in items
        ))
        evidence_ids = list(dict.fromkeys(
            evidence_id for items in sections.values() for item in items
            for evidence_id in item["evidence_ids"]
        ))
        return self.repository.create(
            SalesEnablementOutput(
                sales_output_id=f"sales_{uuid4().hex}",
                brief_id=brief_id,
                title=f"Sales Enablement — {brief.title}",
                sections=sections,
                source_claim_ids=source_claim_ids,
                evidence_ids=evidence_ids,
                created_at=utc_now(),
                is_synthetic=brief.is_demo,
            )
        )


@dataclass(slots=True)
class ProductWorkflowServices:
    event_service: WorkflowEventService
    feed_repository: FeedRepository
    watchlist_service: WatchlistService
    market_map_service: MarketMapService
    opportunity_service: OpportunityService
    quality_service: EvidenceQualityService
    duplicate_group_service: DuplicateGroupService
    brief_workflow_service: BriefWorkflowService
    saved_comparison_service: SavedComparisonService
    executive_brief_service: ExecutiveBriefService
    sales_enablement_service: SalesEnablementService
    usage_service: UsageService
    audit_service: AuditService
    opportunity_repository: OpportunityRepository
    duplicate_group_repository: DuplicateGroupRepository
    review_repository: ReviewRepository
    saved_comparison_repository: SavedComparisonRepository
    executive_brief_repository: ExecutiveBriefRepository
    sales_enablement_repository: SalesEnablementRepository
    usage_repository: UsageRepository
    audit_repository: AuditRepository
    benchmark_service: Any
    analytics_service: Any

    def statistics(self) -> dict[str, Any]:
        quality = self.quality_service.distribution()
        market_map = self.market_map_service.build()
        return {
            "feed_events": self.feed_repository.count(),
            "watchlist_vendors": self.watchlist_service.repository.count(),
            "market_map_cells": len(market_map["cells"]),
            "opportunities_generated": self.opportunity_repository.count(),
            "evidence_quality": quality["quality"],
            "evidence_freshness": quality["freshness"],
            "duplicate_groups": self.duplicate_group_repository.count(),
            "briefs_reviewed": self.review_repository.reviewed_brief_count(),
            "executive_briefs": self.executive_brief_repository.count(),
            "sales_enablement_outputs": self.sales_enablement_repository.count(),
            "saved_comparisons": self.saved_comparison_repository.count(),
            "usage_events": self.usage_repository.count(),
            "audit_events": self.audit_repository.count(),
        }
