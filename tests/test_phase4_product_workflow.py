"""Phase 4 product workflow, operational feature, and E2E tests."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import unittest
from uuid import uuid4

from src.healthcare.bootstrap import bootstrap_product_workflow


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Phase4ProductWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.database_path = PROJECT_ROOT / "data" / f"test_phase4_{uuid4().hex}.db"
        cls.foundation, cls.intelligence, cls.workflow = bootstrap_product_workflow(
            cls.database_path,
            seed_demo=True,
            seed_intelligence_demo=True,
            seed_workflow_demo=False,
        )
        cls.vendors = cls.foundation.vendor_service.list_vendors()

    @classmethod
    def tearDownClass(cls) -> None:
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(cls.database_path) + suffix)
            if path.exists():
                path.unlink()

    def setUp(self) -> None:
        database = self.foundation.category_repository.database
        with database.connect() as connection:
            connection.execute("DELETE FROM audit_events")
            connection.execute("DELETE FROM usage_events")
            connection.execute("DELETE FROM sales_enablement_outputs")
            connection.execute("DELETE FROM executive_briefs")
            connection.execute("DELETE FROM saved_comparisons")
            connection.execute("DELETE FROM claim_review_notes")
            connection.execute("DELETE FROM brief_reviews")
            connection.execute("DELETE FROM duplicate_group_members")
            connection.execute("DELETE FROM duplicate_groups")
            connection.execute("DELETE FROM opportunities")
            connection.execute("DELETE FROM watchlist_entries")
            connection.execute("DELETE FROM feed_events")
            connection.execute("UPDATE competitor_briefs SET status = 'DRAFT'")
            connection.execute(
                """
                UPDATE claims
                SET review_status = CASE
                    WHEN support_level = 'UNSUPPORTED' THEN 'UNSUPPORTED'
                    ELSE 'PENDING'
                END,
                reviewed_at = ''
                """
            )

    def _add_evidence(
        self,
        vendor_id: str,
        source_type: str = "Hospital Case Study",
        category: str = "digital_hospital",
        age_days: int = 10,
    ):
        evidence_id = f"evidence_test_phase4_{uuid4().hex}"
        return self.foundation.evidence_service.create_evidence(
            {
                "evidence_id": evidence_id,
                "vendor_id": vendor_id,
                "source_type": source_type,
                "source_title": f"Phase 4 workflow test {evidence_id}",
                "source_url": f"https://demo.invalid/tests/{evidence_id}",
                "publication_date": (date.today() - timedelta(days=age_days)).isoformat(),
                "raw_text": f"Unique Phase 4 workflow test Evidence {evidence_id}.",
                "summary": f"Test signal {evidence_id}.",
                "solution_categories": [category],
                "hospital_name": "Synthetic Test Hospital" if source_type == "Hospital Case Study" else "",
                "procurement_entity": "Synthetic Test Authority" if source_type == "Public Procurement" else "",
                "project_name": "Synthetic Test Project",
                "contract_value": "100000" if source_type == "Public Procurement" else "",
                "currency": "CNY" if source_type == "Public Procurement" else "",
                "is_synthetic": True,
            }
        )

    def _complete_review(self, brief_id: str, reviewer: str = "Test Reviewer"):
        service = self.workflow.brief_workflow_service
        service.start_review(brief_id, reviewer, "Review started")
        for claim in self.intelligence.claim_repository.list_by_brief(brief_id):
            if claim.review_status == "PENDING":
                service.review_claim(
                    claim.claim_id,
                    "approve",
                    reviewer,
                    note="Claim reviewed against Evidence.",
                )
        return service.approve(brief_id, reviewer, "Review complete")

    def test_feed_events_are_created_from_real_evidence_and_filterable(self) -> None:
        vendor = self.vendors[0]
        evidence = self._add_evidence(vendor.vendor_id, "Hospital Case Study")
        events = self.workflow.feed_repository.list_all(vendor_id=vendor.vendor_id, limit=None)
        event_types = {event.event_type for event in events}

        self.assertIn("NEW_EVIDENCE", event_types)
        self.assertIn("NEW_CASE_STUDY", event_types)
        self.assertIn("NEW_SOLUTION_SIGNAL", event_types)
        filtered = self.workflow.feed_repository.list_all(
            event_type="NEW_CASE_STUDY",
            solution_category="digital_hospital",
            source_type="Hospital Case Study",
            importance="HIGH",
        )
        self.assertEqual([event.evidence_id for event in filtered], [evidence.evidence_id])
        self.assertTrue(all(event.is_synthetic for event in filtered))

    def test_v4_migration_normalizes_existing_phase3_workflow_statuses(self) -> None:
        brief = self.intelligence.brief_repository.list_all()[0]
        claim = brief.claims[0]
        database = self.foundation.category_repository.database
        with database.connect() as connection:
            connection.execute(
                "UPDATE competitor_briefs SET status = 'Needs Review' WHERE brief_id = ?",
                (brief.brief_id,),
            )
            connection.execute(
                "UPDATE claims SET review_status = 'Pending' WHERE claim_id = ?",
                (claim.claim_id,),
            )
        database.initialise()
        self.assertEqual(self.intelligence.brief_repository.get(brief.brief_id).status, "DRAFT")
        self.assertEqual(self.intelligence.claim_repository.get(claim.claim_id).review_status, "PENDING")
        with database.connect() as connection:
            version = connection.execute(
                "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
            ).fetchone()[0]
        self.assertEqual(version, "5.0")

    def test_watchlist_add_remove_and_real_update_detection(self) -> None:
        vendor = self.vendors[0]
        entry = self.workflow.watchlist_service.follow(vendor.vendor_id)
        self.assertEqual(entry.vendor_id, vendor.vendor_id)
        self._add_evidence(vendor.vendor_id, "Public Procurement")
        details = self.workflow.watchlist_service.details(vendor.vendor_id)
        self.assertEqual(details["new_evidence_since_last_view"], 1)
        self.assertIn("New procurement activity", details["alerts"])
        self.workflow.watchlist_service.mark_viewed(vendor.vendor_id)
        self.assertEqual(
            self.workflow.watchlist_service.details(vendor.vendor_id)["new_evidence_since_last_view"],
            0,
        )
        self.assertTrue(self.workflow.watchlist_service.unfollow(vendor.vendor_id))
        self.assertEqual(self.workflow.watchlist_service.repository.count(), 0)

    def test_market_map_uses_validated_non_duplicate_evidence_and_links_cells(self) -> None:
        vendor_ids = [vendor.vendor_id for vendor in self.vendors[:3]]
        result = self.workflow.market_map_service.build(
            vendor_ids=vendor_ids,
            category_ids=["his", "emr_ehr"],
            minimum_evidence_count=1,
        )
        self.assertTrue(result["cells"])
        for cell in result["cells"]:
            self.assertIn(cell["vendor_id"], vendor_ids)
            self.assertIn(cell["category_id"], {"his", "emr_ehr"})
            self.assertIn(cell["support_status"], {"SUPPORTED", "PARTIALLY_SUPPORTED"})
            for evidence_id in cell["evidence_ids"]:
                evidence = self.foundation.evidence_service.get_evidence(evidence_id)
                self.assertEqual(evidence.validation_status, "Valid")
                self.assertEqual(evidence.evidence_status, "Validated")
                self.assertFalse(evidence.duplicate_of_evidence_id)

    def test_opportunities_have_evidence_inference_recommendation_and_review(self) -> None:
        vendor_ids = [vendor.vendor_id for vendor in self.vendors[:3]]
        for vendor_id in vendor_ids:
            self.workflow.watchlist_service.follow(vendor_id)
        opportunities = self.workflow.opportunity_service.generate(vendor_ids)
        self.assertEqual({item.opportunity_type for item in opportunities}, {
            "SOLUTION_WHITE_SPACE", "MESSAGING_WHITE_SPACE", "COMPETITOR_WEAKNESS",
            "EVIDENCE_GAP", "SALES_ENABLEMENT",
        })
        for item in opportunities:
            self.assertTrue(item.evidence_ids)
            self.assertTrue(item.evidence_statement)
            self.assertTrue(item.inference)
            self.assertTrue(item.recommendation)
            self.assertTrue(item.confidence_basis)
            self.assertTrue(item.is_synthetic)
            self.assertTrue(all(
                self.foundation.evidence_service.get_evidence(evidence_id) is not None
                for evidence_id in item.evidence_ids
            ))
        reviewed = self.workflow.opportunity_service.review(
            opportunities[0].opportunity_id, "APPROVED", "Opportunity Reviewer", "Validated scope"
        )
        self.assertEqual(reviewed.review_status, "APPROVED")
        self.assertEqual(reviewed.reviewer, "Opportunity Reviewer")

    def test_evidence_quality_and_freshness_rules_are_transparent(self) -> None:
        fresh = self._add_evidence(self.vendors[0].vendor_id, age_days=90)
        aging = self._add_evidence(self.vendors[0].vendor_id, age_days=91)
        old = self._add_evidence(self.vendors[0].vendor_id, age_days=181)
        assessments = [
            self.workflow.quality_service.assess(item)
            for item in (fresh, aging, old)
        ]
        self.assertEqual(
            [item.freshness_status for item in assessments],
            ["FRESH", "AGING", "OUTDATED"],
        )
        self.assertTrue(all(0 <= item.quality_score <= 10 for item in assessments))
        self.assertTrue(all(item.quality_components for item in assessments))
        self.assertTrue(all("Total" in item.quality_explanation[-1] for item in assessments))

    def test_duplicate_groups_retain_primary_and_supporting_copies(self) -> None:
        groups = self.workflow.duplicate_group_service.rebuild()
        self.assertGreaterEqual(len(groups), 6)
        for group in groups:
            self.assertIn(group.primary_evidence_id, group.member_evidence_ids)
            self.assertGreaterEqual(len(group.member_evidence_ids), 2)
            self.assertIsNotNone(
                self.foundation.evidence_service.get_evidence(group.primary_evidence_id)
            )

    def test_full_brief_and_claim_review_workflow_with_queue_and_notes(self) -> None:
        brief = self.intelligence.brief_repository.list_all()[0]
        service = self.workflow.brief_workflow_service
        started = service.start_review(brief.brief_id, "Reviewer One", "Initial review")
        self.assertEqual(started.status, "IN_REVIEW")
        first_pending = next(
            claim for claim in self.intelligence.claim_repository.list_by_brief(brief.brief_id)
            if claim.review_status == "PENDING"
        )
        reviewed = service.review_claim(
            first_pending.claim_id,
            "edit",
            "Reviewer One",
            {"claim_text": first_pending.claim_text + " Reviewed."},
            "Clarified wording",
        )
        self.assertEqual(reviewed.review_status, "EDITED")
        self.assertEqual(
            self.workflow.review_repository.list_claim_notes(first_pending.claim_id)[0].note,
            "Clarified wording",
        )
        revised = service.return_for_revision(brief.brief_id, "Reviewer One", "Address remaining Claims")
        self.assertEqual(revised.status, "NEEDS_REVISION")
        service.start_review(brief.brief_id, "Reviewer One")
        for claim in self.intelligence.claim_repository.list_by_brief(brief.brief_id):
            if claim.review_status == "PENDING":
                service.review_claim(claim.claim_id, "approve", "Reviewer One")
        approved = service.approve(brief.brief_id, "Reviewer One", "Approved")
        self.assertEqual(approved.status, "APPROVED")
        final = service.finalize(brief.brief_id)
        self.assertEqual(final.status, "FINAL")
        metadata = self.workflow.review_repository.get(brief.brief_id)
        self.assertEqual(metadata.revision_count, 1)
        self.assertTrue(metadata.review_completed_at)
        queue = service.queue()
        self.assertNotIn(brief.brief_id, {item.brief_id for item in queue["briefs_awaiting_review"]})

    def test_executive_and_sales_outputs_reuse_traceable_claims(self) -> None:
        brief = self.intelligence.brief_repository.list_all()[0]
        executive = self.workflow.executive_brief_service.create(brief.brief_id)
        sales = self.workflow.sales_enablement_service.create(brief.brief_id)
        claim_ids = {claim.claim_id for claim in brief.claims}

        self.assertTrue({
            "Competitor Snapshot", "What's Changed", "Top Strengths", "Top Risks",
            "Key Procurement / Case Signals", "Positioning Insight", "Top Opportunity",
            "Recommended Action", "Evidence Sources",
        }.issubset(executive.sections))
        self.assertTrue(all(
            claim_id in claim_ids
            for section_ids in executive.sections.values()
            for claim_id in section_ids
        ))
        self.assertTrue(all(
            self.foundation.evidence_service.get_evidence(evidence_id) is not None
            for evidence_id in executive.evidence_ids + sales.evidence_ids
        ))
        self.assertTrue({
            "How We Differentiate", "Observed Competitor Strengths",
            "Observed Competitor Weaknesses", "Potential Customer Concerns",
            "Suggested Discovery Questions", "Suggested Talking Points",
        }.issubset(sales.sections))
        for section in ("Suggested Discovery Questions", "Suggested Talking Points"):
            self.assertTrue(all(
                item["claim_type"] == "RECOMMENDATION" for item in sales.sections[section]
            ))
        self.assertTrue(executive.is_synthetic)
        self.assertTrue(sales.is_synthetic)

    def test_comparison_saving_usage_and_audit_logging(self) -> None:
        comparison = self.intelligence.brief_repository.list_all("COMPARISON")[0]
        saved = self.workflow.saved_comparison_service.save(comparison.brief_id)
        self.assertEqual(saved.selected_vendors, comparison.vendor_ids)
        self.assertEqual(saved.claim_ids, [claim.claim_id for claim in comparison.claims])
        event = self.workflow.usage_service.record(
            "comparison_run", "CompetitorBrief", comparison.brief_id,
            actor="Analyst", is_synthetic=True,
        )
        audit = self.workflow.audit_service.record(
            "COMPARISON_GENERATED", "CompetitorBrief", comparison.brief_id,
            actor="Analyst", is_synthetic=True,
        )
        self.assertEqual(event.event_type, "comparison_run")
        self.assertEqual(audit.event_type, "COMPARISON_GENERATED")
        self.assertEqual(self.workflow.usage_repository.count(), 1)
        self.assertEqual(self.workflow.audit_repository.count(), 1)

    def test_e2e_follow_evidence_refresh_review_and_executive_brief(self) -> None:
        vendor = self.vendors[0]
        self.workflow.watchlist_service.follow(vendor.vendor_id)
        evidence = self._add_evidence(vendor.vendor_id, "Hospital Case Study", "smart_healthcare")
        self.assertEqual(
            self.workflow.watchlist_service.details(vendor.vendor_id)["new_evidence_since_last_view"],
            1,
        )
        _, brief, report = self.intelligence.vendor_intelligence_service.generate(vendor.vendor_id)
        self.assertEqual(report["result"], "PASS")
        pack = self.intelligence.evidence_pack_service.get_pack(brief.evidence_pack_id)
        self.assertIn(evidence.evidence_id, pack.evidence_ids)
        approved = self._complete_review(brief.brief_id)
        self.assertEqual(approved.status, "APPROVED")
        executive = self.workflow.executive_brief_service.create(brief.brief_id)
        self.assertTrue(executive.evidence_ids)
        self.assertTrue(set(executive.evidence_ids).issubset(set(pack.evidence_ids)))
        feed_types = {
            event.event_type for event in self.workflow.feed_repository.list_all(
                vendor_id=vendor.vendor_id, limit=None
            )
        }
        self.assertIn("NEW_EVIDENCE", feed_types)
        self.assertIn("BRIEF_GENERATED", {
            event.event_type for event in self.workflow.feed_repository.list_all(limit=None)
        })

    def test_e2e_market_map_comparison_opportunity_review_and_sales(self) -> None:
        vendor_ids = [vendor.vendor_id for vendor in self.vendors[:3]]
        market_map = self.workflow.market_map_service.build(vendor_ids=vendor_ids)
        self.assertTrue(market_map["cells"])
        comparison, report = self.intelligence.comparison_service.generate(vendor_ids)
        self.assertEqual(report["result"], "PASS")
        saved = self.workflow.saved_comparison_service.save(comparison.brief_id)
        opportunities = self.workflow.opportunity_service.generate(vendor_ids)
        reviewed = self.workflow.opportunity_service.review(
            opportunities[0].opportunity_id, "APPROVED", "Opportunity Reviewer"
        )
        sales = self.workflow.sales_enablement_service.create(comparison.brief_id)

        self.assertEqual(saved.brief_id, comparison.brief_id)
        self.assertEqual(reviewed.review_status, "APPROVED")
        self.assertTrue(sales.evidence_ids)
        for opportunity in opportunities:
            self.assertTrue(all(
                self.foundation.evidence_service.get_evidence(evidence_id) is not None
                for evidence_id in opportunity.evidence_ids
            ))


if __name__ == "__main__":
    unittest.main()
