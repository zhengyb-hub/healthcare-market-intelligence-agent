"""Unified Phase 5 metrics, benchmark, and evaluation services."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any
from uuid import uuid4

from .analytics_models import (
    AI_STAGE_KEYS,
    MANUAL_STAGE_KEYS,
    BenchmarkRun,
    BenchmarkTask,
    MetricDefinition,
)
from .analytics_repositories import BenchmarkRepository
from .database import Database
from .models import utc_now


WORKFLOW_TYPES = {"MANUAL", "AI_ASSISTED"}
REVIEW_RESULTS = {"PASS", "NEEDS_REVISION", "FAIL"}
RUN_STATUSES = {"DRAFT", "COMPLETE"}


class BenchmarkService:
    """Persist comparable workflow observations and calculate paired results."""

    def __init__(self, repository: BenchmarkRepository, manifest_path: str | Path) -> None:
        self.repository = repository
        self.database = repository.database
        self.manifest_path = Path(manifest_path)

    def manifest(self) -> dict[str, Any]:
        payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        payload["tasks"] = [asdict(self._task(item)) for item in payload.get("tasks", [])]
        return payload

    def tasks(self) -> list[BenchmarkTask]:
        return [self._task(item) for item in self.manifest().get("tasks", [])]

    def task(self, task_id: str) -> BenchmarkTask:
        for item in self.tasks():
            if item.task_id == task_id:
                return item
        raise KeyError(f"Unknown evaluation task: {task_id}")

    @staticmethod
    def _task(values: dict[str, Any]) -> BenchmarkTask:
        return BenchmarkTask(
            task_id=str(values["task_id"]),
            task_type=str(values["task_type"]),
            vendor_ids=list(values["vendor_ids"]),
            evidence_ids=list(values["evidence_ids"]),
            output_requirement=str(values["output_requirement"]),
            required_sections=list(values.get("required_sections", [])),
            is_synthetic=bool(values.get("is_synthetic", False)),
        )

    def validate_manifest(self) -> dict[str, Any]:
        tasks = self.tasks()
        task_ids = [item.task_id for item in tasks]
        errors: list[str] = []
        if len(tasks) < 5:
            errors.append("Evaluation manifest must contain at least five tasks.")
        if len(task_ids) != len(set(task_ids)):
            errors.append("Evaluation task IDs must be unique.")
        with self.database.connect() as connection:
            vendor_ids = {row[0] for row in connection.execute("SELECT vendor_id FROM vendors")}
            evidence_rows = {
                row["evidence_id"]: row
                for row in connection.execute(
                    """
                    SELECT evidence_id, vendor_id, validation_status, evidence_status,
                           duplicate_of_evidence_id, is_synthetic
                    FROM evidence
                    """
                )
            }
        for task in tasks:
            if not task.vendor_ids or not task.evidence_ids:
                errors.append(f"{task.task_id}: Vendor and Evidence sets must be non-empty.")
            missing_vendors = sorted(set(task.vendor_ids) - vendor_ids)
            if missing_vendors:
                errors.append(f"{task.task_id}: missing Vendors {missing_vendors}")
            for evidence_id in task.evidence_ids:
                row = evidence_rows.get(evidence_id)
                if row is None:
                    errors.append(f"{task.task_id}: missing Evidence {evidence_id}")
                    continue
                if row["vendor_id"] not in task.vendor_ids:
                    errors.append(f"{task.task_id}: Evidence {evidence_id} has the wrong Vendor.")
                if row["validation_status"] != "Valid" or row["evidence_status"] != "Validated":
                    errors.append(f"{task.task_id}: Evidence {evidence_id} is not validated.")
                if row["duplicate_of_evidence_id"]:
                    errors.append(f"{task.task_id}: Evidence {evidence_id} is a duplicate member.")
                if task.is_synthetic != bool(row["is_synthetic"]):
                    errors.append(f"{task.task_id}: synthetic flag does not match {evidence_id}.")
        return {
            "result": "PASS" if not errors else "FAIL",
            "task_count": len(tasks),
            "errors": errors,
        }

    @staticmethod
    def stage_keys(workflow_type: str) -> tuple[str, ...]:
        if workflow_type == "MANUAL":
            return MANUAL_STAGE_KEYS
        if workflow_type == "AI_ASSISTED":
            return AI_STAGE_KEYS
        raise ValueError(f"Unsupported workflow_type: {workflow_type}")

    def record_run(
        self,
        task_id: str,
        workflow_type: str,
        stage_times: dict[str, float],
        *,
        run_status: str = "COMPLETE",
        notes: str = "",
        started_at: str = "",
        ended_at: str = "",
        claim_count: int = 0,
        brief_length: int = 0,
        brief_id: str = "",
        review_result: str = "",
        edit_count: int = 0,
        review_minutes: float | None = None,
        unsupported_claims_found: int = 0,
        citation_errors_found: int = 0,
        measurement_method: str = "MANUAL_ENTRY",
    ) -> BenchmarkRun:
        if workflow_type not in WORKFLOW_TYPES:
            raise ValueError("workflow_type must be MANUAL or AI_ASSISTED")
        if run_status not in RUN_STATUSES:
            raise ValueError("run_status must be DRAFT or COMPLETE")
        task = self.task(task_id)
        required_keys = self.stage_keys(workflow_type)
        unknown = sorted(set(stage_times) - set(required_keys))
        missing = sorted(set(required_keys) - set(stage_times))
        if unknown or missing:
            raise ValueError(f"Stage keys mismatch; missing={missing}, unknown={unknown}")
        clean_times = {key: round(float(stage_times[key]), 6) for key in required_keys}
        if any(value < 0 for value in clean_times.values()):
            raise ValueError("Stage times cannot be negative")
        total_minutes = round(sum(clean_times.values()), 6)
        if run_status == "COMPLETE":
            if total_minutes <= 0:
                raise ValueError("A complete benchmark requires positive measured time")
            if claim_count <= 0 or brief_length <= 0:
                raise ValueError("A complete benchmark requires Claim count and Brief length")
            if review_result not in REVIEW_RESULTS:
                raise ValueError("A complete benchmark requires PASS, NEEDS_REVISION, or FAIL")
        pair_id = f"pair_{task.task_id}"
        existing = self.repository.get_by_pair(pair_id, workflow_type)
        run = BenchmarkRun(
            benchmark_id=existing.benchmark_id if existing else f"benchmark_{uuid4().hex}",
            pair_id=pair_id,
            manifest_task_id=task.task_id,
            task_type=task.task_type,
            workflow_type=workflow_type,
            vendor_ids=task.vendor_ids,
            evidence_ids=task.evidence_ids,
            output_requirement=task.output_requirement,
            stage_times=clean_times,
            total_minutes=total_minutes,
            started_at=started_at,
            ended_at=ended_at,
            recorded_at=utc_now(),
            notes=notes,
            vendor_count=len(task.vendor_ids),
            evidence_count=len(task.evidence_ids),
            claim_count=int(claim_count),
            brief_length=int(brief_length),
            brief_id=brief_id,
            review_result=review_result,
            edit_count=int(edit_count),
            review_minutes=(
                float(review_minutes)
                if review_minutes is not None
                else clean_times.get("ai_review_minutes", 0.0)
            ),
            unsupported_claims_found=int(unsupported_claims_found),
            citation_errors_found=int(citation_errors_found),
            measurement_method=measurement_method,
            run_status=run_status,
            comparability_status="PENDING",
            non_comparable_reason="",
            is_synthetic=task.is_synthetic,
        )
        saved = self.repository.save(run)
        self.evaluate_pair(pair_id)
        return self.repository.get(saved.benchmark_id) or saved

    def evaluate_pair(self, pair_id: str) -> dict[str, str]:
        runs = {item.workflow_type: item for item in self.repository.list_by_pair(pair_id)}
        if set(runs) != WORKFLOW_TYPES:
            status, reason = "PENDING", "Both Manual and AI-assisted runs are required."
        elif any(item.run_status != "COMPLETE" for item in runs.values()):
            status, reason = "PENDING", "Both workflows must be complete."
        else:
            manual, assisted = runs["MANUAL"], runs["AI_ASSISTED"]
            reasons: list[str] = []
            if manual.task_type != assisted.task_type:
                reasons.append("task_type differs")
            if manual.vendor_ids != assisted.vendor_ids:
                reasons.append("Vendor set differs")
            if manual.evidence_ids != assisted.evidence_ids:
                reasons.append("Evidence set differs")
            if manual.output_requirement != assisted.output_requirement:
                reasons.append("output requirement differs")
            if manual.vendor_count != assisted.vendor_count:
                reasons.append("Vendor count differs")
            if manual.evidence_count != assisted.evidence_count:
                reasons.append("Evidence count differs")
            claim_ratio = min(manual.claim_count, assisted.claim_count) / max(
                manual.claim_count, assisted.claim_count
            )
            length_ratio = min(manual.brief_length, assisted.brief_length) / max(
                manual.brief_length, assisted.brief_length
            )
            if claim_ratio < 0.75:
                reasons.append("Claim count differs by more than 25%")
            if length_ratio < 0.70:
                reasons.append("Brief length differs by more than 30%")
            status = "NON_COMPARABLE" if reasons else "COMPARABLE"
            reason = "; ".join(reasons)
        self.repository.update_comparability(pair_id, status, reason)
        return {"status": status, "reason": reason}

    def history(self) -> list[BenchmarkRun]:
        return self.repository.list_all()

    @staticmethod
    def _distribution(values: list[float]) -> dict[str, float | None]:
        if not values:
            return {"median": None, "mean": None, "min": None, "max": None, "stddev": None}
        return {
            "median": round(median(values), 3),
            "mean": round(mean(values), 3),
            "min": round(min(values), 3),
            "max": round(max(values), 3),
            "stddev": round(stdev(values), 3) if len(values) > 1 else 0.0,
        }

    def summary(self) -> dict[str, Any]:
        pairs: dict[str, dict[str, BenchmarkRun]] = {}
        for run in self.repository.list_all():
            if run.run_status == "COMPLETE" and run.comparability_status == "COMPARABLE":
                pairs.setdefault(run.pair_id, {})[run.workflow_type] = run
        valid_pairs = [pair for pair in pairs.values() if set(pair) == WORKFLOW_TYPES]
        manual_values = [pair["MANUAL"].total_minutes for pair in valid_pairs]
        ai_values = [pair["AI_ASSISTED"].total_minutes for pair in valid_pairs]
        manual_stats = self._distribution(manual_values)
        ai_stats = self._distribution(ai_values)
        manual_median = manual_stats["median"]
        ai_median = ai_stats["median"]
        if manual_median is None or ai_median is None or manual_median <= 0:
            time_saved = reduction = speed_multiple = None
        else:
            time_saved = round(manual_median - ai_median, 3)
            reduction = round(time_saved / manual_median * 100, 3)
            speed_multiple = round(manual_median / ai_median, 3) if ai_median > 0 else None
        all_runs = self.repository.list_all()
        return {
            "paired_sample_size": len(valid_pairs),
            "manual": manual_stats,
            "ai_assisted": ai_stats,
            "time_saved_minutes": time_saved,
            "time_reduction_pct": reduction,
            "speed_multiple": speed_multiple,
            "total_run_records": len(all_runs),
            "complete_run_records": sum(item.run_status == "COMPLETE" for item in all_runs),
            "draft_run_records": sum(item.run_status == "DRAFT" for item in all_runs),
            "non_comparable_pairs": len(
                {item.pair_id for item in all_runs if item.comparability_status == "NON_COMPARABLE"}
            ),
        }


class AnalyticsService:
    """The sole calculation surface for dashboard and evaluation metrics."""

    def __init__(
        self,
        database: Database,
        benchmark_service: BenchmarkService,
        quality_service: Any,
    ) -> None:
        self.database = database
        self.benchmark_service = benchmark_service
        self.quality_service = quality_service

    @staticmethod
    def definitions() -> dict[str, MetricDefinition]:
        definitions = [
            MetricDefinition("vendor_count", "All Vendor records.", "COUNT(vendors)", "Every Vendor status and environment.", "None."),
            MetricDefinition("active_vendor_count", "Vendors with status Active.", "COUNT(vendors WHERE status='Active')", "Active Vendors.", "Inactive or archived Vendors."),
            MetricDefinition("evidence_count", "All persisted Evidence records.", "COUNT(evidence)", "Valid, Warning, Invalid, primary, duplicate, and synthetic records.", "None."),
            MetricDefinition("validated_evidence_count", "Evidence that passed both workflow and validation status checks.", "COUNT(evidence WHERE evidence_status='Validated' AND validation_status='Valid')", "Valid Evidence, including explicitly flagged duplicate records.", "Warning/Needs Review and Invalid/Rejected records."),
            MetricDefinition("duplicate_evidence_count", "Evidence records linked to a canonical Evidence record.", "COUNT(evidence WHERE duplicate_of_evidence_id <> '')", "Duplicate member records.", "Primary/canonical records."),
            MetricDefinition("brief_count", "All persisted structured competitor Briefs.", "COUNT(competitor_briefs)", "Every Brief type/status in the evaluation database.", "None."),
            MetricDefinition("final_brief_count", "Briefs in FINAL workflow state.", "COUNT(competitor_briefs WHERE status='FINAL')", "Final Briefs.", "Draft, in-review, revision, and approved Briefs."),
            MetricDefinition("claim_count", "All Claims generated for structured Briefs.", "COUNT(claims)", "Every support and review status.", "None."),
            MetricDefinition("supported_claim_count", "Claims classified SUPPORTED.", "COUNT(claims WHERE support_level='SUPPORTED')", "Supported Claims.", "Other support levels."),
            MetricDefinition("partially_supported_claim_count", "Claims classified PARTIALLY_SUPPORTED.", "COUNT(claims WHERE support_level='PARTIALLY_SUPPORTED')", "Partially supported Claims.", "Other support levels."),
            MetricDefinition("unsupported_claim_count", "Claims classified UNSUPPORTED.", "COUNT(claims WHERE support_level='UNSUPPORTED')", "Unsupported Claims.", "Other support levels."),
            MetricDefinition("invalid_citation_count", "Citation references that are missing or outside the Claim's Evidence Pack.", "COUNT(each cited Evidence ID that does not exist or is not in the owning Evidence Pack)", "All Claim citation references.", "Empty unsupported Claims are not invalid citations."),
            MetricDefinition("reviewed_claim_count", "Claims explicitly reviewed or included in a completed Brief review.", "COUNT(claims WHERE reviewed_at <> '' OR owning Brief review is complete)", "Claims with a review timestamp plus every Claim in a completed Brief review.", "Automatically classified Claims in unreviewed Briefs."),
            MetricDefinition("traceable_claim_count", "Reviewed Claims with at least one citation where every Evidence ID exists and belongs to the owning Evidence Pack.", "COUNT(traceable reviewed Claims)", "Reviewed Claims with valid pack-contained Evidence identities.", "Pending Claims, empty citations, missing Evidence, and out-of-pack citations."),
            MetricDefinition("traceability_rate", "Claim-level source traceability across reviewed Claims; support level is independent.", "traceable_claim_count / reviewed_claim_count * 100", "Reviewed Claims only.", "Pending Claims."),
            MetricDefinition("comparison_count", "Structured Briefs of type COMPARISON.", "COUNT(competitor_briefs WHERE brief_type='COMPARISON')", "Comparison Briefs.", "Single-Vendor Briefs."),
            MetricDefinition("opportunity_count", "Persisted Opportunity hypotheses.", "COUNT(opportunities)", "All review statuses.", "None."),
            MetricDefinition("executive_brief_count", "Persisted Executive Brief outputs.", "COUNT(executive_briefs)", "All Executive Brief outputs.", "None."),
            MetricDefinition("sales_enablement_count", "Persisted Sales Enablement outputs.", "COUNT(sales_enablement_outputs)", "All Sales outputs.", "None."),
            MetricDefinition("review_count", "Briefs with a completed review timestamp.", "COUNT(brief_reviews WHERE review_completed_at <> '')", "Completed Brief reviews.", "Started or absent reviews."),
            MetricDefinition("average_review_time", "Mean positive measured minutes across completed Brief reviews.", "AVG(brief_reviews.review_minutes WHERE completed AND review_minutes > 0)", "Completed reviews with a positive measured duration.", "Incomplete reviews and zero-duration demo timestamps."),
            MetricDefinition("average_edit_count", "Mean revision count across completed Brief reviews.", "AVG(brief_reviews.revision_count WHERE completed)", "Completed reviews.", "Incomplete reviews."),
            MetricDefinition("finalisation_rate", "Share of all Briefs in FINAL state.", "final_brief_count / brief_count * 100", "All Briefs.", "None."),
        ]
        return {item.metric: item for item in definitions}

    def _traceability(self) -> dict[str, Any]:
        with self.database.connect() as connection:
            evidence_ids = {row[0] for row in connection.execute("SELECT evidence_id FROM evidence")}
            rows = connection.execute(
                """
                SELECT c.claim_id, c.evidence_ids, c.review_status, c.reviewed_at,
                       p.evidence_ids AS pack_ids,
                       COALESCE(r.review_completed_at, '') AS review_completed_at
                FROM claims c
                JOIN competitor_briefs b ON b.brief_id = c.brief_id
                JOIN evidence_packs p ON p.evidence_pack_id = b.evidence_pack_id
                LEFT JOIN brief_reviews r ON r.brief_id = c.brief_id
                """
            ).fetchall()
        reviewed = traceable = invalid_count = 0
        for row in rows:
            cited = list(json.loads(row["evidence_ids"]))
            pack_ids = set(json.loads(row["pack_ids"]))
            invalid = [item for item in cited if item not in evidence_ids or item not in pack_ids]
            invalid_count += len(set(invalid))
            if not row["reviewed_at"] and not row["review_completed_at"]:
                continue
            reviewed += 1
            if cited and not invalid:
                traceable += 1
        return {
            "reviewed_claim_count": reviewed,
            "traceable_claim_count": traceable,
            "invalid_citation_count": invalid_count,
            "traceability_rate": round(traceable / reviewed * 100, 3) if reviewed else None,
        }

    def snapshot(self) -> dict[str, Any]:
        with self.database.connect() as connection:
            scalar_queries = {
                "vendor_count": "SELECT COUNT(*) FROM vendors",
                "active_vendor_count": "SELECT COUNT(*) FROM vendors WHERE status='Active'",
                "evidence_count": "SELECT COUNT(*) FROM evidence",
                "validated_evidence_count": "SELECT COUNT(*) FROM evidence WHERE evidence_status='Validated' AND validation_status='Valid'",
                "duplicate_evidence_count": "SELECT COUNT(*) FROM evidence WHERE duplicate_of_evidence_id <> ''",
                "solution_category_count": "SELECT COUNT(*) FROM solution_categories WHERE status='Active'",
                "brief_count": "SELECT COUNT(*) FROM competitor_briefs",
                "final_brief_count": "SELECT COUNT(*) FROM competitor_briefs WHERE status='FINAL'",
                "claim_count": "SELECT COUNT(*) FROM claims",
                "supported_claim_count": "SELECT COUNT(*) FROM claims WHERE support_level='SUPPORTED'",
                "partially_supported_claim_count": "SELECT COUNT(*) FROM claims WHERE support_level='PARTIALLY_SUPPORTED'",
                "unsupported_claim_count": "SELECT COUNT(*) FROM claims WHERE support_level='UNSUPPORTED'",
                "comparison_count": "SELECT COUNT(*) FROM competitor_briefs WHERE brief_type='COMPARISON'",
                "opportunity_count": "SELECT COUNT(*) FROM opportunities",
                "executive_brief_count": "SELECT COUNT(*) FROM executive_briefs",
                "sales_enablement_count": "SELECT COUNT(*) FROM sales_enablement_outputs",
                "review_count": "SELECT COUNT(*) FROM brief_reviews WHERE review_completed_at <> ''",
                "average_review_time": "SELECT AVG(review_minutes) FROM brief_reviews WHERE review_completed_at <> '' AND review_minutes > 0",
                "average_edit_count": "SELECT AVG(revision_count) FROM brief_reviews WHERE review_completed_at <> ''",
                "usage_event_count": "SELECT COUNT(*) FROM usage_events",
                "audit_event_count": "SELECT COUNT(*) FROM audit_events",
            }
            metrics = {
                key: connection.execute(query).fetchone()[0]
                for key, query in scalar_queries.items()
            }
            metrics["evidence_by_vendor"] = {
                row["vendor_id"]: int(row["n"])
                for row in connection.execute(
                    "SELECT vendor_id, COUNT(*) n FROM evidence GROUP BY vendor_id ORDER BY vendor_id"
                )
            }
            metrics["briefs_by_type"] = {
                row["brief_type"]: int(row["n"])
                for row in connection.execute(
                    "SELECT brief_type, COUNT(*) n FROM competitor_briefs GROUP BY brief_type"
                )
            }
        for key in ("average_review_time", "average_edit_count"):
            metrics[key] = round(float(metrics[key]), 3) if metrics[key] is not None else None
        metrics.update(self._traceability())
        metrics["finalisation_rate"] = (
            round(metrics["final_brief_count"] / metrics["brief_count"] * 100, 3)
            if metrics["brief_count"] else None
        )
        for key, count_key in (
            ("supported_claim_pct", "supported_claim_count"),
            ("partially_supported_claim_pct", "partially_supported_claim_count"),
            ("unsupported_claim_pct", "unsupported_claim_count"),
        ):
            metrics[key] = (
                round(metrics[count_key] / metrics["claim_count"] * 100, 3)
                if metrics["claim_count"] else None
            )
        quality = self.quality_service.distribution()
        metrics["evidence_quality"] = quality["quality"]
        metrics["evidence_freshness"] = quality["freshness"]
        metrics["benchmark"] = self.benchmark_service.summary()
        metrics["environment"] = "SYNTHETIC_EVALUATION"
        return metrics

    @staticmethod
    def _shown(value: Any, suffix: str = "") -> str:
        if value is None:
            return "NOT AVAILABLE"
        if isinstance(value, float):
            return f"{value:.3f}".rstrip("0").rstrip(".") + suffix
        return f"{value}{suffix}"

    def export_artifacts(self, output_dir: str | Path) -> dict[str, Path]:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        snapshot = self.snapshot()

        definitions = self.definitions()
        metric_rows = []
        for key, definition in definitions.items():
            actual = snapshot.get(key)
            metric_rows.append(
                f"| {key} | {definition.definition} | {definition.formula} | "
                f"{definition.included_records} | {definition.excluded_records} | {self._shown(actual)} |"
            )
        audit = "\n".join(
            [
                "# Metric Audit",
                "",
                "All results below are calculated from the current SQLite database. The environment is synthetic evaluation, not production usage.",
                "",
                "## 180 vs 183 reconciliation",
                "",
                "Phase 2 seeded 180 Evidence records. Phase 4 added three distinct workflow/freshness Evidence records through EvidenceService, producing the current total of 183. No migration-created rows were found; duplicate members remain persisted and are reported separately rather than deleted.",
                "",
                "| Metric | Definition | SQL / Formula | Included Records | Excluded Records | Actual Result |",
                "| --- | --- | --- | --- | --- | ---: |",
                *metric_rows,
                "",
                "## Environment classification",
                "",
                "These are Evaluation Metrics from a synthetic portfolio dataset. They must not be described as live client or production usage.",
            ]
        )
        audit_path = output / "METRIC_AUDIT.md"
        audit_path.write_text(audit + "\n", encoding="utf-8")

        report = self._evaluation_report(snapshot)
        report_path = output / "EVALUATION_REPORT.md"
        report_path.write_text(report + "\n", encoding="utf-8")
        return {
            "metric_audit": audit_path,
            "evaluation_report": report_path,
        }

    def _evaluation_report(self, snapshot: dict[str, Any]) -> str:
        benchmark = snapshot["benchmark"]
        manifest = self.benchmark_service.manifest()
        manifest_check = self.benchmark_service.validate_manifest()
        return "\n".join(
            [
                "# Phase 5 Evaluation Report", "",
                "## Evaluation Setup", "",
                "Environment: synthetic portfolio evaluation backed by the project SQLite database. Metrics are generated by one AnalyticsService.", "",
                "## Dataset", "",
                f"- Active Vendors: {snapshot['active_vendor_count']}",
                f"- Evidence Records: {snapshot['evidence_count']}",
                f"- Validated Evidence: {snapshot['validated_evidence_count']}",
                f"- Manifest validation: {manifest_check['result']}", "",
                "## Benchmark Tasks", "",
                f"The frozen `{self.benchmark_service.manifest_path.name}` contains {len(manifest['tasks'])} tasks. Each Manual/AI pair must use the same task, Vendor set, Evidence set, and output requirement.", "",
                "## Manual Workflow", "",
                "Evidence review, selection/organisation, analysis, writing, source linking, and final QA are entered from an actual human timer. Random or estimated Manual timings are prohibited.", "",
                "## AI-Assisted Workflow", "",
                "Evidence Pack creation, generation, validation, review, editing, final QA, and export are stored separately. Automated phases, including rule-based QA, can be timed by the evaluation runner; human review and editing must be completed before the run is eligible.", "",
                "## Results", "",
                f"- Complete comparable pairs: {benchmark['paired_sample_size']}",
                f"- Manual median: {self._shown(benchmark['manual']['median'], ' minutes')}",
                f"- AI-assisted median: {self._shown(benchmark['ai_assisted']['median'], ' minutes')}",
                f"- Time saved: {self._shown(benchmark['time_saved_minutes'], ' minutes')}",
                f"- Time reduction: {self._shown(benchmark['time_reduction_pct'], '%')}",
                f"- Speed multiple: {self._shown(benchmark['speed_multiple'], 'x')}", "",
                "## Traceability", "",
                f"- Reviewed Claims: {snapshot['reviewed_claim_count']}",
                f"- Traceable Claims: {snapshot['traceable_claim_count']}",
                f"- Source Traceability Rate: {self._shown(snapshot['traceability_rate'], '%')}",
                f"- Invalid Citations: {snapshot['invalid_citation_count']}", "",
                "Traceability is calculated at Claim level and is independent from support level.", "",
                "## Support Distribution", "",
                f"- Supported: {snapshot['supported_claim_count']} ({snapshot['supported_claim_pct']}%)",
                f"- Partially Supported: {snapshot['partially_supported_claim_count']} ({snapshot['partially_supported_claim_pct']}%)",
                f"- Unsupported: {snapshot['unsupported_claim_count']} ({snapshot['unsupported_claim_pct']}%)", "",
                "## Review Results", "",
                f"Completed Brief reviews: {snapshot['review_count']}; average recorded review time: {self._shown(snapshot['average_review_time'], ' minutes')}; average revision count: {self._shown(snapshot['average_edit_count'])}.", "",
                "## Limitations", "",
                "- The dataset, Vendors, Evidence, and generated outputs are synthetic evaluation artifacts.",
                "- Current single-Vendor tasks use the complete validated non-duplicate Evidence available per selected Vendor (14 records), below the suggested 20-30-record scope.",
                "- A preparation-time reduction is unavailable until at least five real, complete, comparable paired runs have been recorded.",
                "- The current reviewed-Claim traceability sample comes from one completed synthetic Brief review; frozen Phase 5 task review is pending.",
                "- Review and first-pass metrics remain directional while the reviewed sample is small.", "",
                "## Reproduction", "",
                "1. `python scripts/seed_demo_data.py --reset`", "2. `python scripts/seed_phase3_demo.py`", "3. `python scripts/seed_phase4_demo.py`",
                "4. `python scripts/run_evaluation.py`", "5. Enter actual Manual and remaining human AI stage times in the Benchmark page.",
                "6. `python scripts/check_data_integrity.py`",
            ]
        )
