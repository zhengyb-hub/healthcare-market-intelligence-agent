"""Phase 6 productisation, navigation, demo, and release-safety tests."""

from __future__ import annotations

import os
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest

from src.healthcare.bootstrap import bootstrap_product_workflow
from src.healthcare.integrity import run_integrity_checks
from src.healthcare.ui import PORTFOLIO_VERSION, PRIMARY_NAVIGATION


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE = PROJECT_ROOT / ".test_tmp" / "phase6_productisation.db"


class Phase6ProductisationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        TEST_DATABASE.parent.mkdir(parents=True, exist_ok=True)
        if TEST_DATABASE.exists():
            TEST_DATABASE.unlink()
        cls.previous_database = os.environ.get("HEALTHCARE_DATABASE_PATH")
        cls.previous_api_key = os.environ.pop("OPENAI_API_KEY", None)
        os.environ["HEALTHCARE_DATABASE_PATH"] = str(TEST_DATABASE)
        cls.foundation, cls.intelligence, cls.workflow = bootstrap_product_workflow(
            TEST_DATABASE,
            seed_demo=True,
            seed_intelligence_demo=True,
            seed_workflow_demo=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.previous_database is None:
            os.environ.pop("HEALTHCARE_DATABASE_PATH", None)
        else:
            os.environ["HEALTHCARE_DATABASE_PATH"] = cls.previous_database
        if cls.previous_api_key is not None:
            os.environ["OPENAI_API_KEY"] = cls.previous_api_key
        if TEST_DATABASE.exists():
            TEST_DATABASE.unlink()

    def test_release_identity_and_information_architecture(self) -> None:
        self.assertEqual(PORTFOLIO_VERSION, "1.0.0-rc1")
        self.assertEqual(len(PRIMARY_NAVIGATION), 9)
        self.assertEqual(
            PRIMARY_NAVIGATION,
            (
                "Overview", "Intelligence", "Vendors", "Evidence", "Market",
                "Briefs", "Review", "Analytics", "Settings",
            ),
        )

    def test_e2e_demo_claim_evidence_and_export(self) -> None:
        briefs = self.intelligence.brief_repository.list_all()
        self.assertTrue(briefs)
        brief = briefs[0]
        pack = self.intelligence.evidence_pack_service.get_pack(brief.evidence_pack_id)
        self.assertIsNotNone(pack)
        self.assertTrue(pack.evidence_ids)
        validation = self.intelligence.traceability_service.validate_brief(
            brief.brief_id,
            update_claims=False,
        )
        self.assertEqual(validation["invalid_citations_detected"], 0)
        self.assertIn(brief.title, self.intelligence.export_service.markdown(brief))
        self.assertIn('"claims"', self.intelligence.export_service.json(brief))
        self.assertIn("claim_id", self.intelligence.export_service.claims_csv(brief))

    def test_e2e_watchlist_market_comparison_opportunity_and_executive_output(self) -> None:
        watchlist = self.workflow.watchlist_service.list_details()
        self.assertGreaterEqual(len(watchlist), 3)
        market_map = self.workflow.market_map_service.build(
            [item["vendor"].vendor_id for item in watchlist[:3]]
        )
        self.assertTrue(market_map["cells"])
        comparisons = self.intelligence.brief_repository.list_all("COMPARISON")
        self.assertTrue(comparisons)
        self.assertTrue(self.workflow.opportunity_repository.list_all())
        self.assertIsNotNone(
            self.workflow.executive_brief_repository.get_by_brief(comparisons[0].brief_id)
        )

    def test_manual_benchmark_kpis_remain_unavailable(self) -> None:
        summary = self.workflow.benchmark_service.summary()
        self.assertEqual(summary["paired_sample_size"], 0)
        self.assertIsNone(summary["manual"]["median"])
        self.assertIsNone(summary["ai_assisted"]["median"])
        self.assertIsNone(summary["time_reduction_pct"])
        self.assertIsNone(summary["speed_multiple"])

    def test_demo_data_integrity(self) -> None:
        report = run_integrity_checks(self.foundation.category_repository.database)
        self.assertEqual(report["status"], "PASS", report)

    def test_all_primary_workspaces_render_without_api_key(self) -> None:
        app = AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=45).run()
        self.assertFalse(app.exception, [item.message for item in app.exception])
        for page in PRIMARY_NAVIGATION[1:]:
            app.sidebar.radio[0].set_value(page).run()
            self.assertFalse(
                app.exception,
                f"{page}: {[item.message for item in app.exception]}",
            )
        self.assertNotIn("OPENAI_API_KEY", os.environ)


if __name__ == "__main__":
    unittest.main()
