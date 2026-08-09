"""SQLite repositories for Phase 4 product workflows."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .database import Database
from .workflow_models import (
    AuditEvent,
    BriefReview,
    DuplicateGroup,
    ExecutiveBrief,
    FeedEvent,
    Opportunity,
    ReviewNote,
    SalesEnablementOutput,
    SavedComparison,
    UsageEvent,
    WatchlistEntry,
)


def _loads(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


class FeedRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _from_row(row: sqlite3.Row) -> FeedEvent:
        values = dict(row)
        values["solution_categories"] = _loads(values["solution_categories"], [])
        values["is_synthetic"] = bool(values["is_synthetic"])
        return FeedEvent(**values)

    def create(self, event: FeedEvent) -> FeedEvent:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO feed_events(
                    feed_id, event_type, vendor_id, evidence_id, brief_id,
                    title, summary, source_type, solution_categories,
                    event_date, created_at, importance, is_synthetic, dedupe_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.feed_id, event.event_type, event.vendor_id,
                    event.evidence_id, event.brief_id, event.title, event.summary,
                    event.source_type,
                    json.dumps(event.solution_categories, ensure_ascii=False),
                    event.event_date, event.created_at, event.importance,
                    int(event.is_synthetic), event.dedupe_key,
                ),
            )
            row = connection.execute(
                "SELECT * FROM feed_events WHERE dedupe_key = ?",
                (event.dedupe_key,),
            ).fetchone()
        return self._from_row(row)

    def list_all(
        self,
        vendor_id: str = "",
        event_type: str = "",
        solution_category: str = "",
        source_type: str = "",
        date_from: str = "",
        date_to: str = "",
        importance: str = "",
        limit: int | None = 200,
    ) -> list[FeedEvent]:
        clauses: list[str] = []
        params: list[Any] = []
        for column, value in (
            ("vendor_id", vendor_id),
            ("event_type", event_type),
            ("source_type", source_type),
            ("importance", importance),
        ):
            if value:
                clauses.append(f"{column} = ?")
                params.append(value)
        if solution_category:
            clauses.append("solution_categories LIKE ?")
            params.append(f'%"{solution_category}"%')
        if date_from:
            clauses.append("event_date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("event_date <= ?")
            params.append(date_to)
        query = "SELECT * FROM feed_events"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY event_date DESC, created_at DESC, feed_id"
        if limit is not None:
            query += " LIMIT ?"
            params.append(int(limit))
        with self.database.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._from_row(row) for row in rows]

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM feed_events").fetchone()[0])


class WatchlistRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _from_row(row: sqlite3.Row) -> WatchlistEntry:
        values = dict(row)
        values["is_synthetic"] = bool(values["is_synthetic"])
        return WatchlistEntry(**values)

    def create(self, entry: WatchlistEntry) -> WatchlistEntry:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO watchlist_entries(
                    watchlist_id, vendor_id, watchlist_created_at, last_viewed_at,
                    evidence_count_at_last_view, is_synthetic
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.watchlist_id, entry.vendor_id, entry.watchlist_created_at,
                    entry.last_viewed_at, entry.evidence_count_at_last_view,
                    int(entry.is_synthetic),
                ),
            )
        return entry

    def get_by_vendor(self, vendor_id: str) -> WatchlistEntry | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM watchlist_entries WHERE vendor_id = ?", (vendor_id,)
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self) -> list[WatchlistEntry]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM watchlist_entries ORDER BY watchlist_created_at DESC"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def update_view(self, vendor_id: str, viewed_at: str, evidence_count: int) -> WatchlistEntry:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE watchlist_entries
                SET last_viewed_at = ?, evidence_count_at_last_view = ?
                WHERE vendor_id = ?
                """,
                (viewed_at, evidence_count, vendor_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Vendor is not followed: {vendor_id}")
        result = self.get_by_vendor(vendor_id)
        if result is None:
            raise KeyError(f"Vendor is not followed: {vendor_id}")
        return result

    def delete(self, vendor_id: str) -> bool:
        with self.database.connect() as connection:
            return connection.execute(
                "DELETE FROM watchlist_entries WHERE vendor_id = ?", (vendor_id,)
            ).rowcount == 1

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM watchlist_entries").fetchone()[0])


class OpportunityRepository:
    JSON_FIELDS = {"evidence_ids", "related_claim_ids", "related_vendor_ids"}

    def __init__(self, database: Database) -> None:
        self.database = database

    @classmethod
    def _from_row(cls, row: sqlite3.Row) -> Opportunity:
        values = dict(row)
        for field in cls.JSON_FIELDS:
            values[field] = _loads(values[field], [])
        values["is_synthetic"] = bool(values["is_synthetic"])
        return Opportunity(**values)

    def create(self, item: Opportunity) -> Opportunity:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO opportunities(
                    opportunity_id, opportunity_type, title, evidence_ids,
                    related_claim_ids, related_vendor_ids, evidence_statement,
                    inference, recommendation, confidence_basis, review_status,
                    reviewer, reviewer_note, reviewed_at, created_at, is_synthetic
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.opportunity_id, item.opportunity_type, item.title,
                    json.dumps(item.evidence_ids, ensure_ascii=False),
                    json.dumps(item.related_claim_ids, ensure_ascii=False),
                    json.dumps(item.related_vendor_ids, ensure_ascii=False),
                    item.evidence_statement, item.inference, item.recommendation,
                    item.confidence_basis, item.review_status, item.reviewer,
                    item.reviewer_note, item.reviewed_at, item.created_at,
                    int(item.is_synthetic),
                ),
            )
        return item

    def get(self, opportunity_id: str) -> Opportunity | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM opportunities WHERE opportunity_id = ?", (opportunity_id,)
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self, opportunity_type: str = "", review_status: str = "") -> list[Opportunity]:
        clauses: list[str] = []
        params: list[str] = []
        if opportunity_type:
            clauses.append("opportunity_type = ?")
            params.append(opportunity_type)
        if review_status:
            clauses.append("review_status = ?")
            params.append(review_status)
        query = "SELECT * FROM opportunities"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC, opportunity_id"
        with self.database.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._from_row(row) for row in rows]

    def update_review(
        self, opportunity_id: str, status: str, reviewer: str, note: str, reviewed_at: str
    ) -> Opportunity:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE opportunities
                SET review_status = ?, reviewer = ?, reviewer_note = ?, reviewed_at = ?
                WHERE opportunity_id = ?
                """,
                (status, reviewer, note, reviewed_at, opportunity_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Unknown opportunity_id: {opportunity_id}")
        result = self.get(opportunity_id)
        if result is None:
            raise KeyError(f"Unknown opportunity_id: {opportunity_id}")
        return result

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0])


class DuplicateGroupRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def replace_all(self, groups: list[DuplicateGroup]) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM duplicate_group_members")
            connection.execute("DELETE FROM duplicate_groups")
            for group in groups:
                connection.execute(
                    "INSERT INTO duplicate_groups VALUES (?, ?, ?, ?)",
                    (
                        group.duplicate_group_id, group.primary_evidence_id,
                        json.dumps(group.reasons, ensure_ascii=False), group.created_at,
                    ),
                )
                for evidence_id in group.member_evidence_ids:
                    connection.execute(
                        "INSERT INTO duplicate_group_members VALUES (?, ?, ?)",
                        (
                            group.duplicate_group_id, evidence_id,
                            "PRIMARY" if evidence_id == group.primary_evidence_id else "SUPPORTING_COPY",
                        ),
                    )

    def list_all(self) -> list[DuplicateGroup]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM duplicate_groups ORDER BY created_at DESC, duplicate_group_id"
            ).fetchall()
            groups: list[DuplicateGroup] = []
            for row in rows:
                members = connection.execute(
                    "SELECT evidence_id FROM duplicate_group_members WHERE duplicate_group_id = ? ORDER BY member_role, evidence_id",
                    (row["duplicate_group_id"],),
                ).fetchall()
                groups.append(
                    DuplicateGroup(
                        duplicate_group_id=row["duplicate_group_id"],
                        primary_evidence_id=row["primary_evidence_id"],
                        member_evidence_ids=[member["evidence_id"] for member in members],
                        reasons=_loads(row["reasons"], []),
                        created_at=row["created_at"],
                    )
                )
        return groups

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM duplicate_groups").fetchone()[0])


class ReviewRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _review_from_row(row: sqlite3.Row) -> BriefReview:
        values = dict(row)
        values["review_notes"] = _loads(values["review_notes"], [])
        return BriefReview(**values)

    def get(self, brief_id: str) -> BriefReview | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM brief_reviews WHERE brief_id = ?", (brief_id,)
            ).fetchone()
        return self._review_from_row(row) if row else None

    def upsert(self, review: BriefReview) -> BriefReview:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO brief_reviews(
                    brief_id, reviewer, review_started_at, review_completed_at,
                    review_minutes, review_notes, revision_count, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(brief_id) DO UPDATE SET
                    reviewer=excluded.reviewer,
                    review_started_at=excluded.review_started_at,
                    review_completed_at=excluded.review_completed_at,
                    review_minutes=excluded.review_minutes,
                    review_notes=excluded.review_notes,
                    revision_count=excluded.revision_count,
                    updated_at=excluded.updated_at
                """,
                (
                    review.brief_id, review.reviewer, review.review_started_at,
                    review.review_completed_at, review.review_minutes,
                    json.dumps(review.review_notes, ensure_ascii=False),
                    review.revision_count, review.updated_at,
                ),
            )
        return review

    def add_claim_note(self, note: ReviewNote) -> ReviewNote:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO claim_review_notes VALUES (?, ?, ?, ?, ?)",
                (note.note_id, note.claim_id, note.reviewer, note.note, note.created_at),
            )
        return note

    def list_claim_notes(self, claim_id: str) -> list[ReviewNote]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM claim_review_notes WHERE claim_id = ? ORDER BY created_at, note_id",
                (claim_id,),
            ).fetchall()
        return [ReviewNote(**dict(row)) for row in rows]

    def reviewed_brief_count(self) -> int:
        with self.database.connect() as connection:
            return int(
                connection.execute(
                    "SELECT COUNT(*) FROM competitor_briefs WHERE status IN ('APPROVED', 'FINAL')"
                ).fetchone()[0]
            )


class SavedComparisonRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _from_row(row: sqlite3.Row) -> SavedComparison:
        values = dict(row)
        values["selected_vendors"] = _loads(values["selected_vendors"], [])
        values["claim_ids"] = _loads(values["claim_ids"], [])
        values["is_synthetic"] = bool(values["is_synthetic"])
        return SavedComparison(**values)

    def create(self, item: SavedComparison) -> SavedComparison:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO saved_comparisons VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    item.comparison_id, item.brief_id,
                    json.dumps(item.selected_vendors, ensure_ascii=False),
                    json.dumps(item.claim_ids, ensure_ascii=False), item.summary,
                    item.created_at, int(item.is_synthetic),
                ),
            )
        return item

    def get_by_brief(self, brief_id: str) -> SavedComparison | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM saved_comparisons WHERE brief_id = ?", (brief_id,)
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self) -> list[SavedComparison]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM saved_comparisons ORDER BY created_at DESC"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM saved_comparisons").fetchone()[0])


class ExecutiveBriefRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _from_row(row: sqlite3.Row) -> ExecutiveBrief:
        values = dict(row)
        values["sections"] = _loads(values["sections"], {})
        values["feed_ids"] = _loads(values["feed_ids"], [])
        values["evidence_ids"] = _loads(values["evidence_ids"], [])
        values["is_synthetic"] = bool(values["is_synthetic"])
        return ExecutiveBrief(**values)

    def create(self, item: ExecutiveBrief) -> ExecutiveBrief:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO executive_briefs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item.executive_brief_id, item.brief_id, item.title,
                    json.dumps(item.sections, ensure_ascii=False),
                    json.dumps(item.feed_ids, ensure_ascii=False),
                    json.dumps(item.evidence_ids, ensure_ascii=False),
                    item.created_at, int(item.is_synthetic),
                ),
            )
        return item

    def get_by_brief(self, brief_id: str) -> ExecutiveBrief | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM executive_briefs WHERE brief_id = ?", (brief_id,)
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self) -> list[ExecutiveBrief]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM executive_briefs ORDER BY created_at DESC"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM executive_briefs").fetchone()[0])


class SalesEnablementRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _from_row(row: sqlite3.Row) -> SalesEnablementOutput:
        values = dict(row)
        values["sections"] = _loads(values["sections"], {})
        values["source_claim_ids"] = _loads(values["source_claim_ids"], [])
        values["evidence_ids"] = _loads(values["evidence_ids"], [])
        values["is_synthetic"] = bool(values["is_synthetic"])
        return SalesEnablementOutput(**values)

    def create(self, item: SalesEnablementOutput) -> SalesEnablementOutput:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO sales_enablement_outputs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item.sales_output_id, item.brief_id, item.title,
                    json.dumps(item.sections, ensure_ascii=False),
                    json.dumps(item.source_claim_ids, ensure_ascii=False),
                    json.dumps(item.evidence_ids, ensure_ascii=False),
                    item.created_at, int(item.is_synthetic),
                ),
            )
        return item

    def get_by_brief(self, brief_id: str) -> SalesEnablementOutput | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM sales_enablement_outputs WHERE brief_id = ?", (brief_id,)
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self) -> list[SalesEnablementOutput]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM sales_enablement_outputs ORDER BY created_at DESC"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(
                connection.execute("SELECT COUNT(*) FROM sales_enablement_outputs").fetchone()[0]
            )


class UsageRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, item: UsageEvent) -> UsageEvent:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO usage_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item.usage_event_id, item.event_type, item.entity_type,
                    item.entity_id, item.actor,
                    json.dumps(item.metadata, ensure_ascii=False), item.created_at,
                    int(item.is_synthetic),
                ),
            )
        return item

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0])


class AuditRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, item: AuditEvent) -> AuditEvent:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item.audit_event_id, item.event_type, item.actor,
                    item.entity_type, item.entity_id,
                    json.dumps(item.related_ids, ensure_ascii=False),
                    json.dumps(item.details, ensure_ascii=False), item.created_at,
                    int(item.is_synthetic),
                ),
            )
        return item

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0])
