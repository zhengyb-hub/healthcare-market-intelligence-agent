"""SQLite repositories for Phase 3 intelligence entities."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .database import Database
from .intelligence_models import (
    Claim,
    CompetitorBrief,
    EvidencePack,
    GenerationLog,
    VendorIntelligenceProfile,
)


def _loads(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


class EvidencePackRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, pack: EvidencePack) -> EvidencePack:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO evidence_packs(
                    evidence_pack_id, vendor_ids, evidence_ids,
                    selection_criteria, contains_synthetic_data, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    pack.evidence_pack_id,
                    json.dumps(pack.vendor_ids, ensure_ascii=False),
                    json.dumps(pack.evidence_ids, ensure_ascii=False),
                    json.dumps(pack.selection_criteria, ensure_ascii=False),
                    int(pack.contains_synthetic_data),
                    pack.created_at,
                ),
            )
        return pack

    @staticmethod
    def _from_row(row: sqlite3.Row) -> EvidencePack:
        values = dict(row)
        values["vendor_ids"] = _loads(values["vendor_ids"], [])
        values["evidence_ids"] = _loads(values["evidence_ids"], [])
        values["selection_criteria"] = _loads(values["selection_criteria"], {})
        values["contains_synthetic_data"] = bool(values["contains_synthetic_data"])
        return EvidencePack(**values)

    def get(self, evidence_pack_id: str) -> EvidencePack | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM evidence_packs WHERE evidence_pack_id = ?",
                (evidence_pack_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self) -> list[EvidencePack]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM evidence_packs ORDER BY created_at DESC, evidence_pack_id"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM evidence_packs").fetchone()[0])


class ClaimRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, claim: Claim) -> Claim:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO claims(
                    claim_id, brief_id, vendor_id, claim_text, claim_type,
                    evidence_ids, traceable, support_level, review_status,
                    explanation, reviewed_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    claim.claim_id,
                    claim.brief_id,
                    claim.vendor_id,
                    claim.claim_text,
                    claim.claim_type,
                    json.dumps(claim.evidence_ids, ensure_ascii=False),
                    int(claim.traceable),
                    claim.support_level,
                    claim.review_status,
                    claim.explanation,
                    claim.reviewed_at,
                    claim.created_at,
                    claim.updated_at,
                ),
            )
        return claim

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Claim:
        values = dict(row)
        values["evidence_ids"] = _loads(values["evidence_ids"], [])
        values["traceable"] = bool(values["traceable"])
        return Claim(**values)

    def get(self, claim_id: str) -> Claim | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM claims WHERE claim_id = ?",
                (claim_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list_by_brief(self, brief_id: str) -> list[Claim]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM claims WHERE brief_id = ? ORDER BY created_at, claim_id",
                (brief_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def list_all(self, review_status: str = "", support_level: str = "") -> list[Claim]:
        clauses: list[str] = []
        params: list[str] = []
        if review_status:
            clauses.append("review_status = ?")
            params.append(review_status)
        if support_level:
            clauses.append("support_level = ?")
            params.append(support_level)
        query = "SELECT * FROM claims"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY updated_at DESC, claim_id"
        with self.database.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._from_row(row) for row in rows]

    def update(self, claim_id: str, values: dict[str, Any]) -> Claim:
        allowed = {
            "claim_text",
            "claim_type",
            "evidence_ids",
            "traceable",
            "support_level",
            "review_status",
            "explanation",
            "reviewed_at",
            "updated_at",
        }
        updates = {key: value for key, value in values.items() if key in allowed}
        if "evidence_ids" in updates:
            updates["evidence_ids"] = json.dumps(updates["evidence_ids"], ensure_ascii=False)
        if "traceable" in updates:
            updates["traceable"] = int(bool(updates["traceable"]))
        if not updates:
            result = self.get(claim_id)
            if result is None:
                raise KeyError(f"Unknown claim_id: {claim_id}")
            return result
        assignments = ", ".join(f"{column} = ?" for column in updates)
        with self.database.connect() as connection:
            cursor = connection.execute(
                f"UPDATE claims SET {assignments} WHERE claim_id = ?",
                [*updates.values(), claim_id],
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Unknown claim_id: {claim_id}")
        result = self.get(claim_id)
        if result is None:
            raise KeyError(f"Unknown claim_id: {claim_id}")
        return result

    def counts_by_support(self) -> dict[str, int]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT support_level, COUNT(*) AS count FROM claims GROUP BY support_level"
            ).fetchall()
        return {row["support_level"]: int(row["count"]) for row in rows}

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM claims").fetchone()[0])


class BriefRepository:
    def __init__(self, database: Database, claim_repository: ClaimRepository) -> None:
        self.database = database
        self.claim_repository = claim_repository

    def create(self, brief: CompetitorBrief) -> CompetitorBrief:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO competitor_briefs(
                    brief_id, title, vendor_ids, brief_type, evidence_pack_id,
                    executive_summary, sections, generated_at, status,
                    model, prompt_version, is_demo
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    brief.brief_id,
                    brief.title,
                    json.dumps(brief.vendor_ids, ensure_ascii=False),
                    brief.brief_type,
                    brief.evidence_pack_id,
                    brief.executive_summary,
                    json.dumps(brief.sections, ensure_ascii=False),
                    brief.generated_at,
                    brief.status,
                    brief.model,
                    brief.prompt_version,
                    int(brief.is_demo),
                ),
            )
        return brief

    def _from_row(self, row: sqlite3.Row) -> CompetitorBrief:
        values = dict(row)
        values["vendor_ids"] = _loads(values["vendor_ids"], [])
        values["sections"] = _loads(values["sections"], {})
        values["is_demo"] = bool(values["is_demo"])
        values["claims"] = self.claim_repository.list_by_brief(values["brief_id"])
        return CompetitorBrief(**values)

    def get(self, brief_id: str) -> CompetitorBrief | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM competitor_briefs WHERE brief_id = ?",
                (brief_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self, brief_type: str = "") -> list[CompetitorBrief]:
        query = "SELECT * FROM competitor_briefs"
        params: tuple[str, ...] = ()
        if brief_type:
            query += " WHERE brief_type = ?"
            params = (brief_type,)
        query += " ORDER BY generated_at DESC, brief_id"
        with self.database.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._from_row(row) for row in rows]

    def update_status(self, brief_id: str, status: str) -> CompetitorBrief:
        with self.database.connect() as connection:
            cursor = connection.execute(
                "UPDATE competitor_briefs SET status = ? WHERE brief_id = ?",
                (status, brief_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Unknown brief_id: {brief_id}")
        result = self.get(brief_id)
        if result is None:
            raise KeyError(f"Unknown brief_id: {brief_id}")
        return result

    def count(self, brief_type: str = "") -> int:
        query = "SELECT COUNT(*) FROM competitor_briefs"
        params: tuple[str, ...] = ()
        if brief_type:
            query += " WHERE brief_type = ?"
            params = (brief_type,)
        with self.database.connect() as connection:
            return int(connection.execute(query, params).fetchone()[0])


class VendorProfileRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, profile: VendorIntelligenceProfile) -> VendorIntelligenceProfile:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO vendor_intelligence_profiles(
                    profile_id, vendor_id, brief_id, company_overview, sections,
                    evidence_coverage, last_intelligence_update, is_demo
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.profile_id,
                    profile.vendor_id,
                    profile.brief_id,
                    profile.company_overview,
                    json.dumps(profile.sections, ensure_ascii=False),
                    json.dumps(profile.evidence_coverage, ensure_ascii=False),
                    profile.last_intelligence_update,
                    int(profile.is_demo),
                ),
            )
        return profile

    @staticmethod
    def _from_row(row: sqlite3.Row) -> VendorIntelligenceProfile:
        values = dict(row)
        values["sections"] = _loads(values["sections"], {})
        values["evidence_coverage"] = _loads(values["evidence_coverage"], {})
        values["is_demo"] = bool(values["is_demo"])
        return VendorIntelligenceProfile(**values)

    def get(self, profile_id: str) -> VendorIntelligenceProfile | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM vendor_intelligence_profiles WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self, vendor_id: str = "") -> list[VendorIntelligenceProfile]:
        query = "SELECT * FROM vendor_intelligence_profiles"
        params: tuple[str, ...] = ()
        if vendor_id:
            query += " WHERE vendor_id = ?"
            params = (vendor_id,)
        query += " ORDER BY last_intelligence_update DESC, profile_id"
        with self.database.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._from_row(row) for row in rows]

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(
                connection.execute("SELECT COUNT(*) FROM vendor_intelligence_profiles").fetchone()[0]
            )


class GenerationLogRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, log: GenerationLog) -> GenerationLog:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO generation_logs(
                    generation_id, task_type, vendor_ids, evidence_pack_id,
                    evidence_ids, model, prompt_version, generated_at,
                    success, error, is_demo
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log.generation_id,
                    log.task_type,
                    json.dumps(log.vendor_ids, ensure_ascii=False),
                    log.evidence_pack_id,
                    json.dumps(log.evidence_ids, ensure_ascii=False),
                    log.model,
                    log.prompt_version,
                    log.generated_at,
                    int(log.success),
                    log.error,
                    int(log.is_demo),
                ),
            )
        return log

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM generation_logs").fetchone()[0])
