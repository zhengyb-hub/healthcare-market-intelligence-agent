"""Evidence-grounded change detection and marketing activation services."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
import hashlib
from typing import Any
from uuid import uuid4

from .activation_models import (
    CompetitorChange,
    ContentOpportunity,
    MarketingActionBrief,
    WeeklyDigest,
)
from .activation_repositories import (
    CompetitorChangeRepository,
    ContentOpportunityRepository,
    MarketingActionBriefRepository,
    WeeklyDigestRepository,
)
from .models import Evidence, utc_now
from .repositories import EvidenceRepository, SolutionCategoryRepository, VendorRepository


ACTIVATION_CHANNELS = (
    "LinkedIn",
    "Short Video",
    "Thought Leadership",
    "Email",
    "Sales Enablement",
)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in values if item))


class ChangeDetectionService:
    """Compare successive evidence records and persist reviewable change signals."""

    def __init__(
        self,
        repository: CompetitorChangeRepository,
        evidence_repository: EvidenceRepository,
        vendor_repository: VendorRepository,
    ) -> None:
        self.repository = repository
        self.evidence_repository = evidence_repository
        self.vendor_repository = vendor_repository

    @staticmethod
    def _change_type(current: Evidence, previous: Evidence) -> str:
        added = set(current.solution_categories) - set(previous.solution_categories)
        removed = set(previous.solution_categories) - set(current.solution_categories)
        if added or removed:
            return "SOLUTION_COVERAGE_SHIFT"
        if current.source_type in {"Public Procurement", "Tender Announcement"}:
            return "PROCUREMENT_SIGNAL"
        if current.source_type == "Hospital Case Study":
            return "CUSTOMER_PROOF_SIGNAL"
        return "MESSAGING_SHIFT"

    @staticmethod
    def _significance(current: Evidence, change_type: str) -> str:
        if change_type in {"SOLUTION_COVERAGE_SHIFT", "PROCUREMENT_SIGNAL"}:
            return "HIGH" if current.source_authority == "High" else "MEDIUM"
        return "MEDIUM" if current.source_authority in {"High", "Medium"} else "LOW"

    @staticmethod
    def _summary(item: Evidence) -> str:
        return (item.summary or item.source_title or item.cleaned_text[:240]).strip()

    def scan(self, vendor_ids: list[str] | None = None) -> list[CompetitorChange]:
        selected = set(vendor_ids or [])
        evidence = [
            item for item in self.evidence_repository.list_all(include_archived=False)
            if item.validation_status == "Valid"
            and not item.duplicate_of_evidence_id
            and (not selected or item.vendor_id in selected)
        ]
        by_vendor_source: dict[tuple[str, str], list[Evidence]] = defaultdict(list)
        by_vendor: dict[str, list[Evidence]] = defaultdict(list)
        for item in evidence:
            by_vendor_source[(item.vendor_id, item.source_type)].append(item)
            by_vendor[item.vendor_id].append(item)

        pairs: list[tuple[Evidence, Evidence]] = []
        vendors_with_pairs: set[str] = set()
        for (vendor_id, _), items in by_vendor_source.items():
            ordered = sorted(items, key=lambda item: (item.publication_date, item.evidence_id))
            if len(ordered) >= 2:
                pairs.append((ordered[-2], ordered[-1]))
                vendors_with_pairs.add(vendor_id)
        for vendor_id, items in by_vendor.items():
            if vendor_id in vendors_with_pairs or len(items) < 2:
                continue
            ordered = sorted(items, key=lambda item: (item.publication_date, item.evidence_id))
            pairs.append((ordered[-2], ordered[-1]))

        results: list[CompetitorChange] = []
        for previous, current in pairs:
            vendor = self.vendor_repository.get(current.vendor_id)
            change_type = self._change_type(current, previous)
            fingerprint = hashlib.sha256(
                f"{current.vendor_id}|{previous.evidence_id}|{current.evidence_id}|{change_type}".encode("utf-8")
            ).hexdigest()
            label = change_type.replace("_", " ").title()
            item = CompetitorChange(
                change_id=f"change_{uuid4().hex}",
                vendor_id=current.vendor_id,
                change_type=change_type,
                significance=self._significance(current, change_type),
                headline=f"{vendor.vendor_name if vendor else current.vendor_id}: {label}",
                before_text=self._summary(previous),
                after_text=self._summary(current),
                evidence_ids=[previous.evidence_id, current.evidence_id],
                detected_at=utc_now(),
                status="NEW",
                is_synthetic=previous.is_synthetic or current.is_synthetic,
                fingerprint=fingerprint,
            )
            results.append(self.repository.create(item))
        return results


class MarketingActionBriefService:
    """Turn grounded competitor signals into an actionable marketing plan."""

    def __init__(
        self,
        repository: MarketingActionBriefRepository,
        content_repository: ContentOpportunityRepository,
        change_repository: CompetitorChangeRepository,
        change_service: ChangeDetectionService,
        evidence_repository: EvidenceRepository,
        vendor_repository: VendorRepository,
        category_repository: SolutionCategoryRepository,
    ) -> None:
        self.repository = repository
        self.content_repository = content_repository
        self.change_repository = change_repository
        self.change_service = change_service
        self.evidence_repository = evidence_repository
        self.vendor_repository = vendor_repository
        self.category_repository = category_repository

    def _eligible_evidence(self, vendor_ids: list[str]) -> list[Evidence]:
        selected = set(vendor_ids)
        return [
            item for item in self.evidence_repository.list_all(include_archived=False)
            if item.vendor_id in selected
            and item.validation_status == "Valid"
            and not item.duplicate_of_evidence_id
        ]

    def _content_opportunities(
        self,
        brief: MarketingActionBrief,
        focus: str,
    ) -> list[ContentOpportunity]:
        specs = {
            "LinkedIn": (
                "Carousel",
                f"What competitor evidence reveals about {focus}",
                "Translate verified market signals into a five-slide decision narrative.",
                "Save the evidence checklist",
            ),
            "Short Video": (
                "30-second video script",
                f"Three competitor signals changing the {focus} conversation",
                "Open with the change, show one cited proof point, and close with a practical response.",
                "View the full intelligence brief",
            ),
            "Thought Leadership": (
                "Article outline",
                f"A practical buyer guide to {focus}",
                "Address an under-explained buyer decision using cited competitor and customer signals.",
                "Download the buyer checklist",
            ),
            "Email": (
                "Three-message nurture sequence",
                f"From market signal to a safer {focus} decision",
                "Sequence evidence, implication, and next step without presenting inference as fact.",
                "Request a focused assessment",
            ),
            "Sales Enablement": (
                "One-page battlecard",
                f"How to discuss {focus} with evidence",
                "Give sales teams a grounded differentiation angle, discovery prompt, and claim guardrail.",
                "Open the source-backed battlecard",
            ),
        }
        opportunities: list[ContentOpportunity] = []
        evidence_ids = brief.evidence_ids[:4]
        change_ids = brief.change_ids[:3]
        for channel in brief.channels:
            content_format, hook, angle, cta = specs[channel]
            item = ContentOpportunity(
                content_opportunity_id=f"content_{uuid4().hex}",
                action_brief_id=brief.action_brief_id,
                title=f"{channel} opportunity — {focus}",
                channel=channel,
                content_format=content_format,
                audience=brief.audience,
                hook=hook,
                angle=angle,
                cta=cta,
                evidence_ids=evidence_ids,
                source_change_ids=change_ids,
                status="DRAFT",
                created_at=utc_now(),
                is_synthetic=brief.is_synthetic,
            )
            opportunities.append(self.content_repository.create(item))
        return opportunities

    def create(
        self,
        vendor_ids: list[str],
        objective: str,
        audience: str,
        channels: list[str],
        target_brand: str = "Your Brand",
    ) -> tuple[MarketingActionBrief, list[ContentOpportunity]]:
        vendor_ids = _unique(vendor_ids)
        if not 1 <= len(vendor_ids) <= 5:
            raise ValueError("Select between one and five competitors")
        if not objective.strip() or not audience.strip():
            raise ValueError("Objective and audience are required")
        invalid_channels = [channel for channel in channels if channel not in ACTIVATION_CHANNELS]
        if invalid_channels or not channels:
            raise ValueError("Select at least one supported channel")
        vendors = [self.vendor_repository.get(vendor_id) for vendor_id in vendor_ids]
        if any(vendor is None for vendor in vendors):
            raise ValueError("Every selected competitor must exist")
        evidence = self._eligible_evidence(vendor_ids)
        if not evidence:
            raise ValueError("Selected competitors do not have eligible Evidence")
        changes = self.change_repository.list_all(vendor_ids=vendor_ids, limit=None)
        if not changes:
            self.change_service.scan(vendor_ids)
            changes = self.change_repository.list_all(vendor_ids=vendor_ids, limit=None)

        category_counts = Counter(
            category_id for item in evidence for category_id in item.solution_categories
        )
        categories = {item.category_id: item.name for item in self.category_repository.list_all()}
        ranked = sorted(category_counts.items(), key=lambda item: (item[1], item[0]))
        focus_categories = [categories.get(category_id, category_id) for category_id, _ in ranked[:3]]
        focus = focus_categories[0] if focus_categories else "healthcare technology value"
        competitor_names = [vendor.vendor_name for vendor in vendors if vendor is not None]
        selected_evidence = sorted(
            evidence,
            key=lambda item: (item.publication_date, item.source_authority, item.evidence_id),
            reverse=True,
        )[:16]
        high_authority = sum(item.source_authority == "High" for item in selected_evidence)
        source_mix = Counter(item.source_type for item in selected_evidence)
        signal_lines = [
            f"{change.headline}: {change.after_text}" for change in changes[:4]
        ] or [
            f"{item.source_title}: {item.summary}" for item in selected_evidence[:4]
        ]
        content_gaps = [
            f"Develop an evidence-led perspective on {name}; it is less represented in the selected competitor evidence set."
            for name in focus_categories
        ] or ["Address an under-explained buyer decision using the strongest available source evidence."]
        sections = {
            "Competitive Signals": signal_lines,
            "Content Gaps": content_gaps,
            "Differentiation Angle": [
                f"Position {target_brand.strip() or 'Your Brand'} around a clearer, lower-risk path to {focus} for {audience.strip()}.",
                f"Use {high_authority} high-authority records in the selected Evidence set and label analytical inference explicitly.",
            ],
            "Campaign Big Idea": [
                f"Make {focus} easier to evaluate: turn competitor claims into a source-backed decision guide for {audience.strip()}."
            ],
            "Content Pillars": [
                f"Market change: explain what has shifted across {', '.join(competitor_names)}.",
                f"Buyer clarity: translate {focus} into practical evaluation questions.",
                "Proof and trust: show where claims are supported, partial, or still need validation.",
            ],
            "Channel Plan": [
                f"{channel}: adapt one grounded insight to the channel's native format."
                for channel in channels
            ],
            "Claims To Avoid": [
                "Do not present monitored Evidence coverage as total market share.",
                "Do not convert an inference or recommendation into an externally verified fact.",
                "Do not reuse outdated or low-authority Evidence without an explicit qualification.",
            ],
            "30-Day Action Plan": [
                "Week 1 — validate the strongest changes and agree the campaign thesis.",
                "Week 2 — produce one flagship asset and channel-specific derivatives.",
                "Week 3 — publish, capture audience questions, and route unsupported claims to review.",
                "Week 4 — compare response quality, refresh Evidence, and revise the next content cycle.",
            ],
            "Evidence Scope": [
                f"{len(selected_evidence)} selected records across {len(source_mix)} source types; {high_authority} are high authority.",
                "All records are from the monitored dataset; this output is decision support, not a market-wide fact base.",
            ],
        }
        brief = MarketingActionBrief(
            action_brief_id=f"action_{uuid4().hex}",
            title=f"Marketing Action Brief — {target_brand.strip() or 'Your Brand'} vs {', '.join(competitor_names)}",
            objective=objective.strip(),
            audience=audience.strip(),
            channels=_unique(channels),
            vendor_ids=vendor_ids,
            evidence_ids=[item.evidence_id for item in selected_evidence],
            change_ids=[item.change_id for item in changes[:8]],
            sections=sections,
            status="DRAFT",
            created_at=utc_now(),
            is_synthetic=any(item.is_synthetic for item in selected_evidence),
        )
        brief = self.repository.create(brief)
        opportunities = self._content_opportunities(brief, focus)
        return brief, opportunities

    @staticmethod
    def markdown(brief: MarketingActionBrief) -> str:
        lines = [
            f"# {brief.title}",
            "",
            f"**Objective:** {brief.objective}",
            f"**Audience:** {brief.audience}",
            f"**Channels:** {', '.join(brief.channels)}",
            f"**Status:** {brief.status}",
            "",
        ]
        for title, items in brief.sections.items():
            lines.extend([f"## {title}", "", *(f"- {item}" for item in items), ""])
        lines.extend([
            "## Evidence IDs", "", *(f"- `{item}`" for item in brief.evidence_ids), "",
            "_Synthetic evaluation output when marked as synthetic; human review is required._",
        ])
        return "\n".join(lines)


class WeeklyDigestService:
    def __init__(
        self,
        repository: WeeklyDigestRepository,
        change_repository: CompetitorChangeRepository,
        change_service: ChangeDetectionService,
        content_repository: ContentOpportunityRepository,
        vendor_repository: VendorRepository,
    ) -> None:
        self.repository = repository
        self.change_repository = change_repository
        self.change_service = change_service
        self.content_repository = content_repository
        self.vendor_repository = vendor_repository

    def create(self, lookback_days: int = 7) -> WeeklyDigest:
        if lookback_days not in {7, 30, 90, 365}:
            raise ValueError("Digest lookback must be 7, 30, 90, or 365 days")
        changes = self.change_repository.list_all(limit=12)
        if not changes:
            self.change_service.scan()
            changes = self.change_repository.list_all(limit=12)
        period_end = date.today()
        period_start = period_end - timedelta(days=lookback_days)
        vendor_names = {
            vendor.vendor_id: vendor.vendor_name
            for vendor in self.vendor_repository.list_all(include_archived=True)
        }
        opportunities = self.content_repository.list_all()[:5]
        high_priority = [item for item in changes if item.significance == "HIGH"]
        selected = changes[:8]
        sections: dict[str, list[dict[str, Any] | str]] = {
            "Executive Pulse": [
                f"{len(selected)} recent detected changes across {len({item.vendor_id for item in selected})} monitored competitors.",
                f"{len(high_priority)} high-significance changes require marketing review.",
            ],
            "Competitor Changes": [
                {
                    "vendor": vendor_names.get(item.vendor_id, item.vendor_id),
                    "change": item.headline,
                    "significance": item.significance,
                    "evidence_ids": item.evidence_ids,
                }
                for item in selected
            ],
            "Marketing Implications": [
                f"Review {item.headline.lower()} before the next campaign or sales-content update."
                for item in high_priority[:4]
            ] or ["No high-significance change is currently present; continue monitoring."],
            "Content Opportunities": [
                {
                    "channel": item.channel,
                    "hook": item.hook,
                    "cta": item.cta,
                    "evidence_ids": item.evidence_ids,
                }
                for item in opportunities
            ] or ["Generate a Marketing Action Brief to create channel-specific opportunities."],
            "Next Actions": [
                "Validate the highest-significance change against its linked Evidence.",
                "Choose one content opportunity and retain its Evidence IDs during production.",
                "Refresh aging Evidence before making an external factual claim.",
            ],
        }
        evidence_ids = _unique([
            evidence_id for item in selected for evidence_id in item.evidence_ids
        ] + [
            evidence_id for item in opportunities for evidence_id in item.evidence_ids
        ])
        digest = WeeklyDigest(
            digest_id=f"digest_{uuid4().hex}",
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            title=f"Competitor Intelligence Digest — {period_end.isoformat()}",
            sections=sections,
            change_ids=[item.change_id for item in selected],
            evidence_ids=evidence_ids,
            created_at=utc_now(),
            is_synthetic=any(item.is_synthetic for item in selected) or any(
                item.is_synthetic for item in opportunities
            ),
        )
        return self.repository.create(digest)

    @staticmethod
    def markdown(digest: WeeklyDigest) -> str:
        lines = [
            f"# {digest.title}", "",
            f"**Period:** {digest.period_start} to {digest.period_end}", "",
        ]
        for title, entries in digest.sections.items():
            lines.extend([f"## {title}", ""])
            for entry in entries:
                if isinstance(entry, dict):
                    readable = "; ".join(
                        f"{key.replace('_', ' ').title()}: {', '.join(value) if isinstance(value, list) else value}"
                        for key, value in entry.items()
                    )
                    lines.append(f"- {readable}")
                else:
                    lines.append(f"- {entry}")
            lines.append("")
        lines.append("_Generated from the monitored Evidence set; human review is required._")
        return "\n".join(lines)
