"""SQLite persistence for Phase 5 benchmark runs."""

from __future__ import annotations

import json
import sqlite3

from .analytics_models import BenchmarkRun
from .database import Database


class BenchmarkRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _from_row(row: sqlite3.Row) -> BenchmarkRun:
        values = dict(row)
        values["vendor_ids"] = json.loads(values["vendor_ids"])
        values["evidence_ids"] = json.loads(values["evidence_ids"])
        values["stage_times"] = {
            key: float(value)
            for key, value in json.loads(values["stage_times"]).items()
        }
        values["is_synthetic"] = bool(values["is_synthetic"])
        return BenchmarkRun(**values)

    def save(self, run: BenchmarkRun) -> BenchmarkRun:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO benchmark_runs(
                    benchmark_id, pair_id, manifest_task_id, task_type, workflow_type,
                    vendor_ids, evidence_ids, output_requirement, stage_times,
                    total_minutes, started_at, ended_at, recorded_at, notes,
                    vendor_count, evidence_count, claim_count, brief_length, brief_id,
                    review_result, edit_count, review_minutes,
                    unsupported_claims_found, citation_errors_found,
                    measurement_method, run_status, comparability_status,
                    non_comparable_reason, is_synthetic
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pair_id, workflow_type) DO UPDATE SET
                    benchmark_id=excluded.benchmark_id,
                    manifest_task_id=excluded.manifest_task_id,
                    task_type=excluded.task_type,
                    vendor_ids=excluded.vendor_ids,
                    evidence_ids=excluded.evidence_ids,
                    output_requirement=excluded.output_requirement,
                    stage_times=excluded.stage_times,
                    total_minutes=excluded.total_minutes,
                    started_at=excluded.started_at,
                    ended_at=excluded.ended_at,
                    recorded_at=excluded.recorded_at,
                    notes=excluded.notes,
                    vendor_count=excluded.vendor_count,
                    evidence_count=excluded.evidence_count,
                    claim_count=excluded.claim_count,
                    brief_length=excluded.brief_length,
                    brief_id=excluded.brief_id,
                    review_result=excluded.review_result,
                    edit_count=excluded.edit_count,
                    review_minutes=excluded.review_minutes,
                    unsupported_claims_found=excluded.unsupported_claims_found,
                    citation_errors_found=excluded.citation_errors_found,
                    measurement_method=excluded.measurement_method,
                    run_status=excluded.run_status,
                    comparability_status=excluded.comparability_status,
                    non_comparable_reason=excluded.non_comparable_reason,
                    is_synthetic=excluded.is_synthetic
                """,
                (
                    run.benchmark_id, run.pair_id, run.manifest_task_id,
                    run.task_type, run.workflow_type,
                    json.dumps(run.vendor_ids, ensure_ascii=False),
                    json.dumps(run.evidence_ids, ensure_ascii=False),
                    run.output_requirement,
                    json.dumps(run.stage_times, ensure_ascii=False, sort_keys=True),
                    run.total_minutes, run.started_at, run.ended_at,
                    run.recorded_at, run.notes, run.vendor_count,
                    run.evidence_count, run.claim_count, run.brief_length,
                    run.brief_id, run.review_result, run.edit_count,
                    run.review_minutes, run.unsupported_claims_found,
                    run.citation_errors_found, run.measurement_method,
                    run.run_status, run.comparability_status,
                    run.non_comparable_reason, int(run.is_synthetic),
                ),
            )
        saved = self.get_by_pair(run.pair_id, run.workflow_type)
        if saved is None:
            raise RuntimeError("Benchmark persistence failed")
        return saved

    def get(self, benchmark_id: str) -> BenchmarkRun | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM benchmark_runs WHERE benchmark_id = ?",
                (benchmark_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def get_by_pair(self, pair_id: str, workflow_type: str) -> BenchmarkRun | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM benchmark_runs WHERE pair_id = ? AND workflow_type = ?",
                (pair_id, workflow_type),
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self) -> list[BenchmarkRun]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM benchmark_runs ORDER BY recorded_at DESC, benchmark_id"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def list_by_pair(self, pair_id: str) -> list[BenchmarkRun]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM benchmark_runs WHERE pair_id = ? ORDER BY workflow_type",
                (pair_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def update_comparability(self, pair_id: str, status: str, reason: str) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE benchmark_runs
                SET comparability_status = ?, non_comparable_reason = ?
                WHERE pair_id = ?
                """,
                (status, reason, pair_id),
            )

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM benchmark_runs").fetchone()[0])
