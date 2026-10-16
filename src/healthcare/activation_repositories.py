"""SQLite repositories for marketing activation outputs."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .activation_models import (
    CompetitorChange,
    ContentOpportunity,
    MarketingActionBrief,
    WeeklyDigest,
)
from .database import Database


def _loads(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


class CompetitorChangeRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _from_row(row: sqlite3.Row) -> CompetitorChange:
        values = dict(row)
        values["evidence_ids"] = _loads(values["evidence_ids"], [])
        values["is_synthetic"] = bool(values["is_synthetic"])
        return CompetitorChange(**values)

    def create(self, item: CompetitorChange) -> CompetitorChange:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO competitor_changes(
                    change_id, vendor_id, change_type, significance, headline,
                    before_text, after_text, evidence_ids, detected_at, status,
                    is_synthetic, fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.change_id, item.vendor_id, item.change_type,
                    item.significance, item.headline, item.before_text,
                    item.after_text, json.dumps(item.evidence_ids, ensure_ascii=False),
                    item.detected_at, item.status, int(item.is_synthetic),
                    item.fingerprint,
                ),
            )
            row = connection.execute(
                "SELECT * FROM competitor_changes WHERE fingerprint = ?",
                (item.fingerprint,),
            ).fetchone()
        return self._from_row(row)

    def list_all(
        self,
        vendor_ids: list[str] | None = None,
        significance: str = "",
        limit: int | None = 200,
    ) -> list[CompetitorChange]:
        clauses: list[str] = []
        params: list[Any] = []
        if vendor_ids:
            placeholders = ", ".join("?" for _ in vendor_ids)
            clauses.append(f"vendor_id IN ({placeholders})")
            params.extend(vendor_ids)
        if significance:
            clauses.append("significance = ?")
            params.append(significance)
        query = "SELECT * FROM competitor_changes"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY detected_at DESC, significance, change_id"
        if limit is not None:
            query += " LIMIT ?"
            params.append(int(limit))
        with self.database.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._from_row(row) for row in rows]

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM competitor_changes").fetchone()[0])


class MarketingActionBriefRepository:
    JSON_FIELDS = {"channels", "vendor_ids", "evidence_ids", "change_ids", "sections"}

    def __init__(self, database: Database) -> None:
        self.database = database

    @classmethod
    def _from_row(cls, row: sqlite3.Row) -> MarketingActionBrief:
        values = dict(row)
        for field in cls.JSON_FIELDS:
            values[field] = _loads(values[field], {} if field == "sections" else [])
        values["is_synthetic"] = bool(values["is_synthetic"])
        return MarketingActionBrief(**values)

    def create(self, item: MarketingActionBrief) -> MarketingActionBrief:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO marketing_action_briefs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.action_brief_id, item.title, item.objective, item.audience,
                    json.dumps(item.channels, ensure_ascii=False),
                    json.dumps(item.vendor_ids, ensure_ascii=False),
                    json.dumps(item.evidence_ids, ensure_ascii=False),
                    json.dumps(item.change_ids, ensure_ascii=False),
                    json.dumps(item.sections, ensure_ascii=False), item.status,
                    item.created_at, int(item.is_synthetic),
                ),
            )
        return item

    def get(self, action_brief_id: str) -> MarketingActionBrief | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM marketing_action_briefs WHERE action_brief_id = ?",
                (action_brief_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self) -> list[MarketingActionBrief]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM marketing_action_briefs ORDER BY created_at DESC, action_brief_id"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM marketing_action_briefs").fetchone()[0])


class ContentOpportunityRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _from_row(row: sqlite3.Row) -> ContentOpportunity:
        values = dict(row)
        values["evidence_ids"] = _loads(values["evidence_ids"], [])
        values["source_change_ids"] = _loads(values["source_change_ids"], [])
        values["is_synthetic"] = bool(values["is_synthetic"])
        return ContentOpportunity(**values)

    def create(self, item: ContentOpportunity) -> ContentOpportunity:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO content_opportunities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.content_opportunity_id, item.action_brief_id, item.title,
                    item.channel, item.content_format, item.audience, item.hook,
                    item.angle, item.cta,
                    json.dumps(item.evidence_ids, ensure_ascii=False),
                    json.dumps(item.source_change_ids, ensure_ascii=False),
                    item.status, item.created_at, int(item.is_synthetic),
                ),
            )
        return item

    def list_all(self, action_brief_id: str = "") -> list[ContentOpportunity]:
        query = "SELECT * FROM content_opportunities"
        params: list[str] = []
        if action_brief_id:
            query += " WHERE action_brief_id = ?"
            params.append(action_brief_id)
        query += " ORDER BY created_at DESC, content_opportunity_id"
        with self.database.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._from_row(row) for row in rows]

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM content_opportunities").fetchone()[0])


class WeeklyDigestRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _from_row(row: sqlite3.Row) -> WeeklyDigest:
        values = dict(row)
        values["sections"] = _loads(values["sections"], {})
        values["change_ids"] = _loads(values["change_ids"], [])
        values["evidence_ids"] = _loads(values["evidence_ids"], [])
        values["is_synthetic"] = bool(values["is_synthetic"])
        return WeeklyDigest(**values)

    def create(self, item: WeeklyDigest) -> WeeklyDigest:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO weekly_digests VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item.digest_id, item.period_start, item.period_end, item.title,
                    json.dumps(item.sections, ensure_ascii=False),
                    json.dumps(item.change_ids, ensure_ascii=False),
                    json.dumps(item.evidence_ids, ensure_ascii=False),
                    item.created_at, int(item.is_synthetic),
                ),
            )
        return item

    def list_all(self) -> list[WeeklyDigest]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM weekly_digests ORDER BY created_at DESC, digest_id"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM weekly_digests").fetchone()[0])
