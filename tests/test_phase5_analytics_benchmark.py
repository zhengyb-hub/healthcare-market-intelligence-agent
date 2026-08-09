from __future__ import annotations

import json
from pathlib import Path
import unittest
from uuid import uuid4

from src.healthcare.analytics_models import AI_STAGE_KEYS, MANUAL_STAGE_KEYS
from src.healthcare.bootstrap import bootstrap_product_workflow

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Phase5AnalyticsBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.database_path = PROJECT_ROOT / "data" / f"test_phase5_{uuid4().hex}.db"
        cls.foundation, cls.intelligence, cls.workflow = bootstrap_product_workflow(
            cls.database_path,
            seed_demo=True,
            seed_intelligence_demo=True,
            seed_workflow_demo=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(cls.database_path) + suffix)
            if path.exists():
                path.unlink()

    def setUp(self) -> None:
        with self.foundation.category_repository.database.connect() as connection:
            connection.execute("DELETE FROM benchmark_runs")
        self.output_dir = PROJECT_ROOT / "data" / f"test_phase5_artifacts_{uuid4().hex}"
        self.output_dir.mkdir()
        self.benchmark = self.workflow.benchmark_service
        self.analytics = self.workflow.analytics_service

    def tearDown(self) -> None:
        for path in self.output_dir.glob("*"):
            path.unlink()
        self.output_dir.rmdir()

    @staticmethod
    def _manual_times(base: float = 10.0) -> dict[str, float]:
        return {key: base + index for index, key in enumerate(MANUAL_STAGE_KEYS)}

    @staticmethod
    def _ai_times(base: float = 2.0) -> dict[str, float]:
        return {key: base + index / 10 for index, key in enumerate(AI_STAGE_KEYS)}

    def _complete_pair(self, task_id: str, manual_base: float = 10, ai_base: float = 2) -> None:
        common = {"claim_count": 10, "brief_length": 1000, "review_result": "PASS"}
        self.benchmark.record_run(
            task_id, "MANUAL", self._manual_times(manual_base), **common
        )
        self.benchmark.record_run(
            task_id, "AI_ASSISTED", self._ai_times(ai_base), **common
        )

    def test_metric_definitions_cover_required_metrics(self) -> None:
        required = {
            "vendor_count", "active_vendor_count", "evidence_count",
            "validated_evidence_count", "duplicate_evidence_count", "brief_count",
            "final_brief_count", "claim_count", "supported_claim_count",
            "partially_supported_claim_count", "unsupported_claim_count",
            "invalid_citation_count", "traceable_claim_count", "traceability_rate",
            "comparison_count", "opportunity_count", "executive_brief_count",
            "sales_enablement_count", "review_count",
        }
        self.assertTrue(required.issubset(self.analytics.definitions()))

    def test_evidence_count_consistency_and_reconciliation(self) -> None:
        snapshot = self.analytics.snapshot()
        self.assertEqual(snapshot["evidence_count"], 183)
        self.assertEqual(snapshot["validated_evidence_count"], 171)
        self.assertEqual(snapshot["duplicate_evidence_count"], 6)
        self.assertEqual(sum(snapshot["evidence_quality"].values()), 183)
        self.assertEqual(sum(snapshot["evidence_freshness"].values()), 183)

    def test_claim_level_traceability_uses_reviewed_denominator(self) -> None:
        snapshot = self.analytics.snapshot()
        self.assertEqual(snapshot["reviewed_claim_count"], 8)
        self.assertEqual(snapshot["traceable_claim_count"], 7)
        self.assertAlmostEqual(snapshot["traceability_rate"], 7 / 8 * 100, places=3)
        self.assertEqual(snapshot["invalid_citation_count"], 0)

    def test_manual_total_is_sum_of_complete_stage_set(self) -> None:
        task_id = self.benchmark.tasks()[0].task_id
        times = self._manual_times()
        run = self.benchmark.record_run(
            task_id, "MANUAL", times,
            claim_count=10, brief_length=1000, review_result="PASS",
        )
        self.assertEqual(run.total_minutes, sum(times.values()))

    def test_ai_total_is_sum_of_complete_workflow_not_model_time_only(self) -> None:
        task_id = self.benchmark.tasks()[0].task_id
        times = self._ai_times()
        run = self.benchmark.record_run(
            task_id, "AI_ASSISTED", times,
            claim_count=10, brief_length=1000, review_result="PASS",
        )
        self.assertEqual(run.total_minutes, sum(times.values()))
        self.assertIn("ai_review_minutes", run.stage_times)
        self.assertIn("ai_export_minutes", run.stage_times)

    def test_time_reduction_uses_paired_medians(self) -> None:
        tasks = self.benchmark.tasks()[:5]
        for index, task in enumerate(tasks):
            self._complete_pair(task.task_id, 10 + index, 2 + index / 10)
        summary = self.benchmark.summary()
        expected = (
            summary["manual"]["median"] - summary["ai_assisted"]["median"]
        ) / summary["manual"]["median"] * 100
        self.assertEqual(summary["paired_sample_size"], 5)
        self.assertAlmostEqual(summary["time_reduction_pct"], expected, places=3)

    def test_distribution_includes_mean_min_max_and_standard_deviation(self) -> None:
        for index, task in enumerate(self.benchmark.tasks()[:5]):
            self._complete_pair(task.task_id, 10 + index, 2 + index / 10)
        summary = self.benchmark.summary()
        for workflow in ("manual", "ai_assisted"):
            self.assertTrue(
                {"median", "mean", "min", "max", "stddev"}.issubset(summary[workflow])
            )

    def test_non_comparable_pair_is_excluded(self) -> None:
        task_id = self.benchmark.tasks()[0].task_id
        self._complete_pair(task_id)
        pair_id = f"pair_{task_id}"
        with self.foundation.category_repository.database.connect() as connection:
            connection.execute(
                "UPDATE benchmark_runs SET evidence_ids='[]', evidence_count=0 "
                "WHERE pair_id=? AND workflow_type='AI_ASSISTED'",
                (pair_id,),
            )
        result = self.benchmark.evaluate_pair(pair_id)
        self.assertEqual(result["status"], "NON_COMPARABLE")
        self.assertEqual(self.benchmark.summary()["paired_sample_size"], 0)

    def test_evaluation_manifest_is_frozen_valid_and_synthetic(self) -> None:
        result = self.benchmark.validate_manifest()
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["task_count"], 6)
        self.assertTrue(all(task.is_synthetic for task in self.benchmark.tasks()))

    def test_cv_metrics_export_and_validation(self) -> None:
        paths = self.analytics.export_artifacts(self.output_dir)
        payload = json.loads(paths["cv_metrics"].read_text(encoding="utf-8"))
        self.assertEqual(payload["evidence_records"], 183)
        self.assertEqual(self.analytics.validate_cv_file(paths["cv_metrics"])["result"], "PASS")

    def test_cv_evidence_uses_same_values_as_snapshot(self) -> None:
        paths = self.analytics.export_artifacts(self.output_dir)
        payload = json.loads(paths["cv_metrics"].read_text(encoding="utf-8"))
        evidence = paths["cv_evidence"].read_text(encoding="utf-8")
        self.assertIn(f"CV Value: {payload['evidence_records']}", evidence)
        self.assertIn(f"Sample Size: {payload['reviewed_claims']}", evidence)

    def test_dashboard_snapshot_and_cv_export_share_service(self) -> None:
        snapshot = self.analytics.snapshot()
        cv = self.analytics.cv_metrics()
        self.assertEqual(cv["vendors_monitored"], snapshot["active_vendor_count"])
        self.assertEqual(cv["competitor_briefs"], snapshot["brief_count"])
        self.assertEqual(cv["traceability_pct"], snapshot["traceability_rate"])

    def test_benchmark_synthetic_flag_is_persisted(self) -> None:
        task_id = self.benchmark.tasks()[0].task_id
        run = self.benchmark.record_run(
            task_id, "MANUAL", self._manual_times(),
            claim_count=10, brief_length=1000, review_result="PASS",
        )
        self.assertTrue(run.is_synthetic)

    def test_benchmark_persists_across_bootstrap(self) -> None:
        task_id = self.benchmark.tasks()[0].task_id
        run = self.benchmark.record_run(
            task_id, "MANUAL", self._manual_times(),
            claim_count=10, brief_length=1000, review_result="PASS",
        )
        _, _, rebuilt = bootstrap_product_workflow(self.database_path, seed_demo=False)
        self.assertIsNotNone(rebuilt.benchmark_service.repository.get(run.benchmark_id))

    def test_benchmark_history_reports_draft_and_complete(self) -> None:
        first, second = self.benchmark.tasks()[:2]
        self.benchmark.record_run(
            first.task_id, "MANUAL", self._manual_times(),
            claim_count=10, brief_length=1000, review_result="PASS",
        )
        self.benchmark.record_run(
            second.task_id, "AI_ASSISTED", {key: 0 for key in AI_STAGE_KEYS},
            run_status="DRAFT", claim_count=10, brief_length=1000,
        )
        summary = self.benchmark.summary()
        self.assertEqual(summary["total_run_records"], 2)
        self.assertEqual(summary["complete_run_records"], 1)
        self.assertEqual(summary["draft_run_records"], 1)

    def test_phase4_demo_seed_is_idempotent_after_phase5_briefs(self) -> None:
        from src.healthcare.demo_workflow_seed import seed_phase4_demo

        before = self.analytics.snapshot()
        seed_phase4_demo(self.foundation, self.intelligence, self.workflow)
        after = self.analytics.snapshot()
        self.assertEqual(after["brief_count"], before["brief_count"])
        self.assertEqual(after["review_count"], before["review_count"])
        self.assertEqual(after["executive_brief_count"], before["executive_brief_count"])


if __name__ == "__main__":
    unittest.main()
