"""Repository boundary between Healthcare services and SQLite."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from .database import Database
from .models import Evidence, SolutionCategory, Vendor, utc_now


def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


class SolutionCategoryRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def upsert(self, category: SolutionCategory) -> SolutionCategory:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO solution_categories(
                    category_id, name, description, parent_id, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(category_id) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    parent_id=excluded.parent_id,
                    status=excluded.status,
                    updated_at=excluded.updated_at
                """,
                (
                    category.category_id,
                    category.name,
                    category.description,
                    category.parent_id,
                    category.status,
                    category.created_at,
                    category.updated_at,
                ),
            )
        return category

    def list_all(self, active_only: bool = True) -> list[SolutionCategory]:
        query = "SELECT * FROM solution_categories"
        params: tuple[Any, ...] = ()
        if active_only:
            query += " WHERE status = ?"
            params = ("Active",)
        query += " ORDER BY name"
        with self.database.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [SolutionCategory(**dict(row)) for row in rows]

    def get(self, category_id: str) -> SolutionCategory | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM solution_categories WHERE category_id = ?",
                (category_id,),
            ).fetchone()
        return SolutionCategory(**dict(row)) if row else None

    def valid_ids(self) -> set[str]:
        return {category.category_id for category in self.list_all(active_only=True)}


class VendorRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _solution_categories(
        connection: sqlite3.Connection,
        vendor_id: str,
    ) -> list[str]:
        rows = connection.execute(
            "SELECT solution_categories FROM evidence WHERE vendor_id = ?",
            (vendor_id,),
        ).fetchall()
        categories: set[str] = set()
        for row in rows:
            categories.update(_json_list(row["solution_categories"]))
        return sorted(categories)

    @classmethod
    def _row_to_vendor(
        cls,
        connection: sqlite3.Connection,
        row: sqlite3.Row,
    ) -> Vendor:
        values = dict(row)
        values["target_customer_types"] = _json_list(values["target_customer_types"])
        values["is_synthetic"] = bool(values["is_synthetic"])
        values["solution_categories"] = cls._solution_categories(
            connection,
            values["vendor_id"],
        )
        return Vendor(**values)

    def create(self, vendor: Vendor) -> Vendor:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO vendors(
                    vendor_id, vendor_name, vendor_type, primary_market,
                    company_summary, headquarters, website,
                    target_customer_types, evidence_count, last_updated,
                    created_at, updated_at, status, is_synthetic
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vendor.vendor_id,
                    vendor.vendor_name,
                    vendor.vendor_type,
                    vendor.primary_market,
                    vendor.company_summary,
                    vendor.headquarters,
                    vendor.website,
                    json.dumps(vendor.target_customer_types, ensure_ascii=False),
                    vendor.evidence_count,
                    vendor.last_updated,
                    vendor.created_at,
                    vendor.updated_at,
                    vendor.status,
                    int(vendor.is_synthetic),
                ),
            )
        return vendor

    def get(self, vendor_id: str) -> Vendor | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM vendors WHERE vendor_id = ?",
                (vendor_id,),
            ).fetchone()
            return self._row_to_vendor(connection, row) if row else None

    def list_all(
        self,
        include_archived: bool = False,
        search: str = "",
    ) -> list[Vendor]:
        clauses: list[str] = []
        params: list[Any] = []
        if not include_archived:
            clauses.append("status <> 'Archived'")
        if search.strip():
            clauses.append("(vendor_name LIKE ? OR company_summary LIKE ?)")
            term = f"%{search.strip()}%"
            params.extend([term, term])
        query = "SELECT * FROM vendors"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY vendor_name"
        with self.database.connect() as connection:
            rows = connection.execute(query, params).fetchall()
            return [self._row_to_vendor(connection, row) for row in rows]

    def update(self, vendor_id: str, values: dict[str, Any]) -> Vendor:
        allowed = {
            "vendor_name",
            "vendor_type",
            "primary_market",
            "company_summary",
            "headquarters",
            "website",
            "target_customer_types",
            "status",
            "is_synthetic",
        }
        updates = {key: value for key, value in values.items() if key in allowed}
        if not updates:
            existing = self.get(vendor_id)
            if existing is None:
                raise KeyError(f"Unknown vendor_id: {vendor_id}")
            return existing
        if "target_customer_types" in updates:
            updates["target_customer_types"] = json.dumps(
                updates["target_customer_types"],
                ensure_ascii=False,
            )
        if "is_synthetic" in updates:
            updates["is_synthetic"] = int(bool(updates["is_synthetic"]))
        updates["updated_at"] = utc_now()
        assignments = ", ".join(f"{column} = ?" for column in updates)
        with self.database.connect() as connection:
            cursor = connection.execute(
                f"UPDATE vendors SET {assignments} WHERE vendor_id = ?",
                [*updates.values(), vendor_id],
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Unknown vendor_id: {vendor_id}")
        result = self.get(vendor_id)
        if result is None:
            raise KeyError(f"Unknown vendor_id: {vendor_id}")
        return result

    def archive(self, vendor_id: str) -> Vendor:
        return self.update(vendor_id, {"status": "Archived"})

    def refresh_metrics(self, vendor_id: str) -> None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS evidence_count, MAX(updated_at) AS last_evidence_at
                FROM evidence
                WHERE vendor_id = ? AND evidence_status <> 'Archived'
                """,
                (vendor_id,),
            ).fetchone()
            connection.execute(
                """
                UPDATE vendors
                SET evidence_count = ?, last_updated = ?, updated_at = ?
                WHERE vendor_id = ?
                """,
                (
                    int(row["evidence_count"]),
                    row["last_evidence_at"] or utc_now(),
                    utc_now(),
                    vendor_id,
                ),
            )


class EvidenceRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _row_to_evidence(row: sqlite3.Row) -> Evidence:
        values = dict(row)
        values["solution_categories"] = _json_list(values["solution_categories"])
        values["duplicate_reasons"] = _json_list(values["duplicate_reasons"])
        values["validation_messages"] = _json_list(values["validation_messages"])
        values["traceable"] = bool(values["traceable"])
        values["is_synthetic"] = bool(values["is_synthetic"])
        return Evidence(**values)

    def create(self, evidence: Evidence) -> Evidence:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO evidence(
                    evidence_id, vendor_id, source_type, source_title, source_url,
                    publication_date, collected_at, raw_text, cleaned_text, summary,
                    solution_categories, hospital_name, procurement_entity,
                    project_name, contract_value, currency, evidence_status,
                    validation_status, source_authority, traceable, content_hash,
                    created_at, updated_at, is_synthetic,
                    duplicate_of_evidence_id, duplicate_reasons, validation_messages
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence.evidence_id,
                    evidence.vendor_id,
                    evidence.source_type,
                    evidence.source_title,
                    evidence.source_url,
                    evidence.publication_date,
                    evidence.collected_at,
                    evidence.raw_text,
                    evidence.cleaned_text,
                    evidence.summary,
                    json.dumps(evidence.solution_categories, ensure_ascii=False),
                    evidence.hospital_name,
                    evidence.procurement_entity,
                    evidence.project_name,
                    evidence.contract_value,
                    evidence.currency,
                    evidence.evidence_status,
                    evidence.validation_status,
                    evidence.source_authority,
                    int(evidence.traceable),
                    evidence.content_hash,
                    evidence.created_at,
                    evidence.updated_at,
                    int(evidence.is_synthetic),
                    evidence.duplicate_of_evidence_id,
                    json.dumps(evidence.duplicate_reasons, ensure_ascii=False),
                    json.dumps(evidence.validation_messages, ensure_ascii=False),
                ),
            )
        return evidence

    def get(self, evidence_id: str) -> Evidence | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM evidence WHERE evidence_id = ?",
                (evidence_id,),
            ).fetchone()
        return self._row_to_evidence(row) if row else None

    def list_all(
        self,
        vendor_id: str = "",
        source_type: str = "",
        solution_category: str = "",
        validation_status: str = "",
        search: str = "",
        include_archived: bool = False,
        limit: int | None = None,
    ) -> list[Evidence]:
        clauses: list[str] = []
        params: list[Any] = []
        if vendor_id:
            clauses.append("vendor_id = ?")
            params.append(vendor_id)
        if source_type:
            clauses.append("source_type = ?")
            params.append(source_type)
        if solution_category:
            clauses.append("solution_categories LIKE ?")
            params.append(f'%"{solution_category}"%')
        if validation_status:
            clauses.append("validation_status = ?")
            params.append(validation_status)
        if search.strip():
            clauses.append(
                "(source_title LIKE ? OR raw_text LIKE ? OR cleaned_text LIKE ? OR summary LIKE ?)"
            )
            term = f"%{search.strip()}%"
            params.extend([term, term, term, term])
        if not include_archived:
            clauses.append("evidence_status <> 'Archived'")
        query = "SELECT * FROM evidence"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY publication_date DESC, evidence_id"
        if limit is not None:
            query += " LIMIT ?"
            params.append(int(limit))
        with self.database.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_evidence(row) for row in rows]

    def find_exact_duplicates(
        self,
        source_url: str,
        content_hash: str,
    ) -> list[tuple[str, list[str]]]:
        clauses: list[str] = []
        params: list[str] = []
        if source_url.strip():
            clauses.append("source_url = ?")
            params.append(source_url.strip())
        if content_hash.strip():
            clauses.append("content_hash = ?")
            params.append(content_hash.strip())
        if not clauses:
            return []
        query = (
            "SELECT evidence_id, source_url, content_hash FROM evidence WHERE "
            + " OR ".join(clauses)
            + " ORDER BY created_at, evidence_id"
        )
        with self.database.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        matches: list[tuple[str, list[str]]] = []
        for row in rows:
            reasons: list[str] = []
            if source_url.strip() and row["source_url"] == source_url.strip():
                reasons.append("Same URL")
            if content_hash.strip() and row["content_hash"] == content_hash.strip():
                reasons.extend(["Exact Text Duplicate", "Same Content Hash"])
            matches.append((row["evidence_id"], sorted(set(reasons))))
        return matches

    def title_candidates(self, vendor_id: str) -> list[tuple[str, str]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT evidence_id, source_title FROM evidence WHERE vendor_id = ?",
                (vendor_id,),
            ).fetchall()
        return [(row["evidence_id"], row["source_title"]) for row in rows]

    def distributions(self) -> dict[str, dict[str, int]]:
        result: dict[str, dict[str, int]] = {}
        with self.database.connect() as connection:
            for key, column in (
                ("source_types", "source_type"),
                ("validation_statuses", "validation_status"),
            ):
                rows = connection.execute(
                    f"SELECT {column} AS label, COUNT(*) AS count FROM evidence GROUP BY {column} ORDER BY count DESC, label"
                ).fetchall()
                result[key] = {row["label"]: int(row["count"]) for row in rows}

            category_counts: dict[str, int] = {}
            rows = connection.execute(
                "SELECT solution_categories FROM evidence"
            ).fetchall()
            for row in rows:
                for category_id in _json_list(row["solution_categories"]):
                    category_counts[category_id] = category_counts.get(category_id, 0) + 1
            result["solution_categories"] = dict(
                sorted(category_counts.items(), key=lambda item: (-item[1], item[0]))
            )
        return result

    def count(self) -> int:
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM evidence").fetchone()[0])

    def duplicate_count(self) -> int:
        with self.database.connect() as connection:
            return int(
                connection.execute(
                    "SELECT COUNT(*) FROM evidence WHERE duplicate_of_evidence_id <> ''"
                ).fetchone()[0]
            )
