"""Marketing activation, change detection, and digest tests."""

from __future__ import annotations

from pathlib import Path
import os
import unittest
from uuid import uuid4

from streamlit.testing.v1 import AppTest

from src.healthcare.bootstrap import bootstrap_product_workflow


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Phase7MarketingActivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.database_path = PROJECT_ROOT / "data" / f"test_phase7_{uuid4().hex}.db"
        cls.foundation, cls.intelligence, cls.workflow = bootstrap_product_workflow(
            cls.database_path,
            seed_demo=True,
            seed_intelligence_demo=True,
            seed_workflow_demo=True,
        )
        cls.vendor_ids = [
            vendor.vendor_id for vendor in cls.foundation.vendor_service.list_vendors()[:3]
        ]

    @classmethod
    def tearDownClass(cls) -> None:
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(cls.database_path) + suffix)
            if path.exists():
                path.unlink()

    def test_activation_and_change_views_render_without_api_key(self) -> None:
        previous_database = os.environ.get("HEALTHCARE_DATABASE_PATH")
        previous_key = os.environ.pop("OPENAI_API_KEY", None)
        os.environ["HEALTHCARE_DATABASE_PATH"] = str(self.database_path)
        try:
            app = AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=45).run()
            self.assertFalse(app.exception, [item.message for item in app.exception])
            app.sidebar.radio[0].set_value("Activation").run()
            self.assertFalse(app.exception, [item.message for item in app.exception])
            app.sidebar.radio[0].set_value("Intelligence").run()
            app.radio[0].set_value("Changes").run()
            self.assertFalse(app.exception, [item.message for item in app.exception])
        finally:
            if previous_database is None:
                os.environ.pop("HEALTHCARE_DATABASE_PATH", None)
            else:
                os.environ["HEALTHCARE_DATABASE_PATH"] = previous_database
            if previous_key is not None:
                os.environ["OPENAI_API_KEY"] = previous_key

    def test_schema_and_demo_activation_outputs(self) -> None:
        database = self.foundation.category_repository.database
        with database.connect() as connection:
            version = connection.execute(
                "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
            ).fetchone()[0]
        self.assertEqual(version, "6.0")
        self.assertGreater(self.workflow.change_repository.count(), 0)
        self.assertGreater(self.workflow.marketing_action_repository.count(), 0)
        self.assertGreater(self.workflow.content_opportunity_repository.count(), 0)
        self.assertGreater(self.workflow.weekly_digest_repository.count(), 0)

    def test_change_detection_is_idempotent_and_traceable(self) -> None:
        before = self.workflow.change_repository.count()
        changes = self.workflow.change_detection_service.scan(self.vendor_ids)
        after = self.workflow.change_repository.count()
        self.assertEqual(before, after)
        self.assertTrue(changes)
        for item in changes:
            self.assertEqual(len(item.evidence_ids), 2)
            self.assertIn(item.significance, {"HIGH", "MEDIUM", "LOW"})
            self.assertTrue(all(
                self.foundation.evidence_service.get_evidence(evidence_id) is not None
                for evidence_id in item.evidence_ids
            ))

    def test_action_brief_creates_grounded_channel_outputs(self) -> None:
        brief, opportunities = self.workflow.marketing_action_service.create(
            self.vendor_ids,
            "Plan a source-backed demand-generation campaign",
            "Hospital CIOs",
            ["LinkedIn", "Short Video", "Email"],
            "Portfolio Health AI",
        )
        self.assertTrue({
            "Competitive Signals", "Content Gaps", "Differentiation Angle",
            "Campaign Big Idea", "Content Pillars", "Channel Plan",
            "Claims To Avoid", "30-Day Action Plan", "Evidence Scope",
        }.issubset(brief.sections))
        self.assertTrue(brief.evidence_ids)
        self.assertTrue(brief.change_ids)
        self.assertEqual({item.channel for item in opportunities}, {"LinkedIn", "Short Video", "Email"})
        self.assertTrue(all(item.evidence_ids for item in opportunities))
        markdown = self.workflow.marketing_action_service.markdown(brief)
        self.assertIn("30-Day Action Plan", markdown)
        self.assertIn(brief.evidence_ids[0], markdown)

    def test_weekly_digest_reuses_changes_and_content_grounding(self) -> None:
        digest = self.workflow.weekly_digest_service.create(30)
        self.assertTrue({
            "Executive Pulse", "Competitor Changes", "Marketing Implications",
            "Content Opportunities", "Next Actions",
        }.issubset(digest.sections))
        self.assertTrue(digest.change_ids)
        self.assertTrue(digest.evidence_ids)
        markdown = self.workflow.weekly_digest_service.markdown(digest)
        self.assertIn("Competitor Changes", markdown)
        self.assertIn("human review", markdown)


if __name__ == "__main__":
    unittest.main()
