"""Deterministic Phase 4 product-workflow demonstration seed."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .intelligence_services import MarketIntelligenceServices
from .services import DataFoundationService
from .workflow_services import ProductWorkflowServices


def _add_freshness_examples(
    foundation: DataFoundationService,
    vendor_ids: list[str],
) -> None:
    examples = [
        ("evidence_phase4_fresh_case", vendor_ids[0], "Hospital Case Study", 30, "digital_hospital"),
        ("evidence_phase4_aging_procurement", vendor_ids[1], "Public Procurement", 120, "regional_healthcare_platform"),
        ("evidence_phase4_outdated_solution", vendor_ids[2], "Solution Page", 240, "healthcare_data_platform"),
    ]
    for evidence_id, vendor_id, source_type, age_days, category_id in examples:
        if foundation.evidence_service.get_evidence(evidence_id) is not None:
            continue
        foundation.evidence_service.create_evidence(
            {
                "evidence_id": evidence_id,
                "vendor_id": vendor_id,
                "source_type": source_type,
                "source_title": f"Synthetic Phase 4 {source_type} workflow signal",
                "source_url": f"https://demo.invalid/phase4/{evidence_id}",
                "publication_date": (date.today() - timedelta(days=age_days)).isoformat(),
                "raw_text": (
                    f"Synthetic Phase 4 evidence {evidence_id} for {vendor_id}, created through the real EvidenceService "
                    "to test Feed, Watchlist, freshness, audit, and traceability workflows."
                ),
                "summary": "Synthetic workflow signal; demonstration use only.",
                "solution_categories": [category_id],
                "hospital_name": "Synthetic Phase 4 Hospital" if source_type == "Hospital Case Study" else "",
                "procurement_entity": "Synthetic Phase 4 Authority" if source_type == "Public Procurement" else "",
                "project_name": "Synthetic Phase 4 Workflow Project",
                "contract_value": "1200000" if source_type == "Public Procurement" else "",
                "currency": "CNY" if source_type == "Public Procurement" else "",
                "is_synthetic": True,
            }
        )


def seed_phase4_demo(
    foundation: DataFoundationService,
    intelligence: MarketIntelligenceServices,
    workflow: ProductWorkflowServices,
) -> dict[str, Any]:
    database = foundation.category_repository.database
    with database.connect() as connection:
        seeded = connection.execute(
            "SELECT value FROM schema_metadata WHERE key = 'phase4_demo_seeded'"
        ).fetchone()
    if seeded and seeded[0] == "1":
        return workflow.statistics()

    vendors = foundation.vendor_service.list_vendors()
    if len(vendors) < 3:
        raise ValueError("Phase 4 demo requires at least three Vendors")
    selected_ids = [vendor.vendor_id for vendor in vendors[:3]]
    for vendor_id in selected_ids:
        workflow.watchlist_service.follow(vendor_id, actor="synthetic-demo")
    _add_freshness_examples(foundation, selected_ids)
    for evidence in foundation.evidence_service.list_evidence(include_archived=True):
        workflow.event_service.evidence_added(evidence, record_audit=False)
    for brief in intelligence.brief_repository.list_all():
        workflow.event_service.brief_generated(brief, record_audit=False)
    workflow.duplicate_group_service.rebuild()
    for brief in intelligence.brief_repository.list_all("COMPARISON"):
        workflow.saved_comparison_service.save(brief.brief_id)
    if workflow.opportunity_repository.count() == 0:
        workflow.opportunity_service.generate(selected_ids)
    briefs = intelligence.brief_repository.list_all()
    for brief in briefs:
        workflow.executive_brief_service.create(brief.brief_id)
        workflow.sales_enablement_service.create(brief.brief_id)
    review_target = next(
        (brief for brief in briefs if brief.brief_type == "VENDOR_INTELLIGENCE"), None
    )
    if review_target and review_target.status == "DRAFT":
        workflow.brief_workflow_service.start_review(
            review_target.brief_id,
            "Synthetic Demo Reviewer",
            "Phase 4 deterministic workflow review.",
        )
        for claim in intelligence.claim_repository.list_by_brief(review_target.brief_id):
            if claim.review_status == "PENDING":
                workflow.brief_workflow_service.review_claim(
                    claim.claim_id,
                    "approve",
                    "Synthetic Demo Reviewer",
                    note="Reviewed against linked synthetic Evidence.",
                )
        workflow.brief_workflow_service.approve(
            review_target.brief_id,
            "Synthetic Demo Reviewer",
            "Traceability and Claim review complete.",
        )
        workflow.brief_workflow_service.finalize(review_target.brief_id)
    with database.connect() as connection:
        connection.execute(
            """
            INSERT INTO schema_metadata(key, value) VALUES ('phase4_demo_seeded', '1')
            ON CONFLICT(key) DO UPDATE SET value='1'
            """
        )
    return workflow.statistics()
