"""Phase 5 analytics, evaluation, and benchmark entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MANUAL_STAGE_KEYS = (
    "manual_evidence_review_minutes",
    "manual_selection_minutes",
    "manual_analysis_minutes",
    "manual_writing_minutes",
    "manual_source_linking_minutes",
    "manual_qa_minutes",
)

AI_STAGE_KEYS = (
    "ai_pack_minutes",
    "ai_generation_minutes",
    "ai_validation_minutes",
    "ai_review_minutes",
    "ai_edit_minutes",
    "ai_qa_minutes",
    "ai_export_minutes",
)


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    metric: str
    definition: str
    formula: str
    included_records: str
    excluded_records: str


@dataclass(slots=True)
class BenchmarkTask:
    task_id: str
    task_type: str
    vendor_ids: list[str]
    evidence_ids: list[str]
    output_requirement: str
    required_sections: list[str]
    is_synthetic: bool


@dataclass(slots=True)
class BenchmarkRun:
    benchmark_id: str
    pair_id: str
    manifest_task_id: str
    task_type: str
    workflow_type: str
    vendor_ids: list[str]
    evidence_ids: list[str]
    output_requirement: str
    stage_times: dict[str, float]
    total_minutes: float
    started_at: str
    ended_at: str
    recorded_at: str
    notes: str
    vendor_count: int
    evidence_count: int
    claim_count: int
    brief_length: int
    brief_id: str
    review_result: str
    edit_count: int
    review_minutes: float
    unsupported_claims_found: int
    citation_errors_found: int
    measurement_method: str
    run_status: str
    comparability_status: str
    non_comparable_reason: str
    is_synthetic: bool

    def as_record(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "pair_id": self.pair_id,
            "manifest_task_id": self.manifest_task_id,
            "task_type": self.task_type,
            "workflow_type": self.workflow_type,
            "vendor_ids": self.vendor_ids,
            "evidence_ids": self.evidence_ids,
            "stage_times": self.stage_times,
            "total_minutes": self.total_minutes,
            "run_status": self.run_status,
            "comparability_status": self.comparability_status,
            "brief_id": self.brief_id,
            "is_synthetic": self.is_synthetic,
        }
