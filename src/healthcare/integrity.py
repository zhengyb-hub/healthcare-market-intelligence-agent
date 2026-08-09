"""Database integrity checks independent from the Streamlit UI."""

from __future__ import annotations

from datetime import date, datetime
import json
from typing import Any

from .database import Database
from .analytics_models import AI_STAGE_KEYS, MANUAL_STAGE_KEYS
from .enums import (
    BRIEF_STATUSES,
    BRIEF_TYPES,
    CLAIM_REVIEW_STATUSES,
    CLAIM_TYPES,
    EVIDENCE_STATUSES,
    FEED_EVENT_TYPES,
    GENERATION_TASK_TYPES,
    IMPORTANCE_LEVELS,
    OPPORTUNITY_REVIEW_STATUSES,
    OPPORTUNITY_TYPES,
    SOURCE_TYPES,
    SUPPORT_LEVELS,
    VALIDATION_STATUSES,
    VENDOR_STATUSES,
    USAGE_EVENT_TYPES,
    AUDIT_EVENT_TYPES,
)


def _date_is_valid(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False


def run_integrity_checks(database: Database) -> dict[str, Any]:
    issues: dict[str, list[str]] = {
        "duplicate_vendor_ids": [],
        "duplicate_evidence_ids": [],
        "missing_vendor_references": [],
        "invalid_solution_categories": [],
        "invalid_source_types": [],
        "missing_content_hashes": [],
        "invalid_dates": [],
        "invalid_statuses": [],
        "orphan_evidence": [],
        "unmarked_duplicates": [],
        "vendor_metric_mismatches": [],
        "invalid_phase3_json": [],
        "orphan_evidence_pack_references": [],
        "orphan_brief_references": [],
        "orphan_claim_references": [],
        "orphan_profile_references": [],
        "orphan_generation_log_references": [],
        "invalid_phase3_statuses": [],
        "invalid_claim_evidence_ids": [],
        "claim_evidence_outside_pack": [],
        "invalid_phase4_json": [],
        "orphan_phase4_references": [],
        "invalid_phase4_statuses": [],
        "invalid_duplicate_groups": [],
        "synthetic_flag_mismatches": [],
        "invalid_phase5_json": [],
        "invalid_phase5_statuses": [],
        "orphan_phase5_references": [],
        "benchmark_total_mismatches": [],
    }

    with database.connect() as connection:
        for table, target in (
            ("vendors", "duplicate_vendor_ids"),
            ("evidence", "duplicate_evidence_ids"),
        ):
            id_column = "vendor_id" if table == "vendors" else "evidence_id"
            rows = connection.execute(
                f"SELECT {id_column}, COUNT(*) AS count FROM {table} GROUP BY {id_column} HAVING COUNT(*) > 1"
            ).fetchall()
            issues[target].extend(row[id_column] for row in rows)

        orphan_rows = connection.execute(
            """
            SELECT e.evidence_id
            FROM evidence e
            LEFT JOIN vendors v ON v.vendor_id = e.vendor_id
            WHERE v.vendor_id IS NULL
            """
        ).fetchall()
        orphan_ids = [row["evidence_id"] for row in orphan_rows]
        issues["missing_vendor_references"].extend(orphan_ids)
        issues["orphan_evidence"].extend(orphan_ids)

        valid_categories = {
            row["category_id"]
            for row in connection.execute(
                "SELECT category_id FROM solution_categories WHERE status = 'Active'"
            ).fetchall()
        }
        evidence_rows = connection.execute(
            """
            SELECT evidence_id, source_type, solution_categories, content_hash,
                   publication_date, collected_at, evidence_status,
                   validation_status, duplicate_of_evidence_id, content_hash
            FROM evidence
            """
        ).fetchall()
        for row in evidence_rows:
            evidence_id = row["evidence_id"]
            try:
                category_ids = json.loads(row["solution_categories"])
            except json.JSONDecodeError:
                category_ids = ["<invalid-json>"]
            invalid_categories = sorted(set(category_ids) - valid_categories)
            if invalid_categories:
                issues["invalid_solution_categories"].append(
                    f"{evidence_id}: {', '.join(invalid_categories)}"
                )
            if row["source_type"] not in SOURCE_TYPES:
                issues["invalid_source_types"].append(evidence_id)
            if not str(row["content_hash"]).strip():
                issues["missing_content_hashes"].append(evidence_id)
            if not _date_is_valid(row["publication_date"]) or not _date_is_valid(
                row["collected_at"]
            ):
                issues["invalid_dates"].append(evidence_id)
            if (
                row["evidence_status"] not in EVIDENCE_STATUSES
                or row["validation_status"] not in VALIDATION_STATUSES
            ):
                issues["invalid_statuses"].append(evidence_id)

        invalid_vendor_status = connection.execute(
            "SELECT vendor_id FROM vendors WHERE status NOT IN ('Active', 'Archived')"
        ).fetchall()
        issues["invalid_statuses"].extend(row["vendor_id"] for row in invalid_vendor_status)

        duplicate_hashes = connection.execute(
            """
            SELECT content_hash
            FROM evidence
            GROUP BY content_hash
            HAVING content_hash <> '' AND COUNT(*) > 1
            """
        ).fetchall()
        for hash_row in duplicate_hashes:
            rows = connection.execute(
                """
                SELECT evidence_id, duplicate_of_evidence_id
                FROM evidence
                WHERE content_hash = ?
                ORDER BY created_at, evidence_id
                """,
                (hash_row["content_hash"],),
            ).fetchall()
            for row in rows[1:]:
                if not row["duplicate_of_evidence_id"]:
                    issues["unmarked_duplicates"].append(row["evidence_id"])

        metric_rows = connection.execute(
            """
            SELECT v.vendor_id, v.evidence_count, COUNT(e.evidence_id) AS actual_count
            FROM vendors v
            LEFT JOIN evidence e
              ON e.vendor_id = v.vendor_id AND e.evidence_status <> 'Archived'
            GROUP BY v.vendor_id, v.evidence_count
            """
        ).fetchall()
        for row in metric_rows:
            if int(row["evidence_count"]) != int(row["actual_count"]):
                issues["vendor_metric_mismatches"].append(
                    f"{row['vendor_id']}: stored={row['evidence_count']} actual={row['actual_count']}"
                )

        validation_distribution = {
            row["validation_status"]: int(row["count"])
            for row in connection.execute(
                """
                SELECT validation_status, COUNT(*) AS count
                FROM evidence
                GROUP BY validation_status
                ORDER BY validation_status
                """
            ).fetchall()
        }
        counts = {
            "vendors": int(connection.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]),
            "evidence": int(connection.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]),
            "solution_categories": int(
                connection.execute("SELECT COUNT(*) FROM solution_categories").fetchone()[0]
            ),
            "duplicates_detected": int(
                connection.execute(
                    "SELECT COUNT(*) FROM evidence WHERE duplicate_of_evidence_id <> ''"
                ).fetchone()[0]
            ),
            "evidence_packs": int(
                connection.execute("SELECT COUNT(*) FROM evidence_packs").fetchone()[0]
            ),
            "competitor_briefs": int(
                connection.execute("SELECT COUNT(*) FROM competitor_briefs").fetchone()[0]
            ),
            "claims": int(connection.execute("SELECT COUNT(*) FROM claims").fetchone()[0]),
            "vendor_intelligence_profiles": int(
                connection.execute(
                    "SELECT COUNT(*) FROM vendor_intelligence_profiles"
                ).fetchone()[0]
            ),
            "generation_logs": int(
                connection.execute("SELECT COUNT(*) FROM generation_logs").fetchone()[0]
            ),
            "feed_events": int(connection.execute("SELECT COUNT(*) FROM feed_events").fetchone()[0]),
            "watchlist_vendors": int(connection.execute("SELECT COUNT(*) FROM watchlist_entries").fetchone()[0]),
            "opportunities": int(connection.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]),
            "duplicate_groups": int(connection.execute("SELECT COUNT(*) FROM duplicate_groups").fetchone()[0]),
            "brief_reviews": int(connection.execute("SELECT COUNT(*) FROM brief_reviews").fetchone()[0]),
            "saved_comparisons": int(connection.execute("SELECT COUNT(*) FROM saved_comparisons").fetchone()[0]),
            "executive_briefs": int(connection.execute("SELECT COUNT(*) FROM executive_briefs").fetchone()[0]),
            "sales_enablement_outputs": int(connection.execute("SELECT COUNT(*) FROM sales_enablement_outputs").fetchone()[0]),
            "usage_events": int(connection.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0]),
            "audit_events": int(connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]),
            "benchmark_runs": int(connection.execute("SELECT COUNT(*) FROM benchmark_runs").fetchone()[0]),
        }

        vendor_ids = {
            row["vendor_id"]
            for row in connection.execute("SELECT vendor_id FROM vendors").fetchall()
        }
        evidence_ids = {
            row["evidence_id"]
            for row in connection.execute("SELECT evidence_id FROM evidence").fetchall()
        }
        pack_rows = connection.execute(
            "SELECT evidence_pack_id, vendor_ids, evidence_ids FROM evidence_packs"
        ).fetchall()
        packs: dict[str, dict[str, set[str]]] = {}
        for row in pack_rows:
            pack_id = row["evidence_pack_id"]
            try:
                pack_vendor_ids = set(json.loads(row["vendor_ids"]))
                pack_evidence_ids = set(json.loads(row["evidence_ids"]))
            except (json.JSONDecodeError, TypeError):
                issues["invalid_phase3_json"].append(pack_id)
                continue
            packs[pack_id] = {
                "vendor_ids": pack_vendor_ids,
                "evidence_ids": pack_evidence_ids,
            }
            for vendor_id in sorted(pack_vendor_ids - vendor_ids):
                issues["orphan_evidence_pack_references"].append(
                    f"{pack_id}: vendor={vendor_id}"
                )
            for evidence_id in sorted(pack_evidence_ids - evidence_ids):
                issues["orphan_evidence_pack_references"].append(
                    f"{pack_id}: evidence={evidence_id}"
                )

        brief_rows = connection.execute(
            """
            SELECT brief_id, vendor_ids, brief_type, evidence_pack_id, status, sections
            FROM competitor_briefs
            """
        ).fetchall()
        briefs: dict[str, str] = {}
        for row in brief_rows:
            brief_id = row["brief_id"]
            briefs[brief_id] = row["evidence_pack_id"]
            try:
                brief_vendor_ids = set(json.loads(row["vendor_ids"]))
                json.loads(row["sections"])
            except (json.JSONDecodeError, TypeError):
                issues["invalid_phase3_json"].append(brief_id)
                brief_vendor_ids = set()
            if row["evidence_pack_id"] not in packs:
                issues["orphan_brief_references"].append(
                    f"{brief_id}: pack={row['evidence_pack_id']}"
                )
            for vendor_id in sorted(brief_vendor_ids - vendor_ids):
                issues["orphan_brief_references"].append(
                    f"{brief_id}: vendor={vendor_id}"
                )
            if row["brief_type"] not in BRIEF_TYPES or row["status"] not in BRIEF_STATUSES:
                issues["invalid_phase3_statuses"].append(brief_id)

        claim_ids: set[str] = set()
        claim_rows = connection.execute(
            """
            SELECT claim_id, brief_id, vendor_id, claim_type, evidence_ids,
                   support_level, review_status
            FROM claims
            """
        ).fetchall()
        for row in claim_rows:
            claim_id = row["claim_id"]
            claim_ids.add(claim_id)
            pack_id = briefs.get(row["brief_id"])
            if pack_id is None:
                issues["orphan_claim_references"].append(
                    f"{claim_id}: brief={row['brief_id']}"
                )
            try:
                cited_ids = set(json.loads(row["evidence_ids"]))
            except (json.JSONDecodeError, TypeError):
                issues["invalid_phase3_json"].append(claim_id)
                cited_ids = set()
            for evidence_id in sorted(cited_ids - evidence_ids):
                issues["invalid_claim_evidence_ids"].append(
                    f"{claim_id}: evidence={evidence_id}"
                )
            if pack_id in packs:
                for evidence_id in sorted(cited_ids - packs[pack_id]["evidence_ids"]):
                    issues["claim_evidence_outside_pack"].append(
                        f"{claim_id}: evidence={evidence_id}"
                    )
                if row["vendor_id"] and row["vendor_id"] not in packs[pack_id]["vendor_ids"]:
                    issues["orphan_claim_references"].append(
                        f"{claim_id}: vendor={row['vendor_id']}"
                    )
            if (
                row["claim_type"] not in CLAIM_TYPES
                or row["support_level"] not in SUPPORT_LEVELS
                or row["review_status"] not in CLAIM_REVIEW_STATUSES
            ):
                issues["invalid_phase3_statuses"].append(claim_id)

        profile_rows = connection.execute(
            "SELECT profile_id, vendor_id, brief_id, sections, evidence_coverage FROM vendor_intelligence_profiles"
        ).fetchall()
        for row in profile_rows:
            profile_id = row["profile_id"]
            if row["vendor_id"] not in vendor_ids or row["brief_id"] not in briefs:
                issues["orphan_profile_references"].append(profile_id)
            try:
                json.loads(row["sections"])
                json.loads(row["evidence_coverage"])
            except (json.JSONDecodeError, TypeError):
                issues["invalid_phase3_json"].append(profile_id)

        log_rows = connection.execute(
            "SELECT generation_id, task_type, evidence_pack_id, evidence_ids FROM generation_logs"
        ).fetchall()
        for row in log_rows:
            generation_id = row["generation_id"]
            pack_id = row["evidence_pack_id"]
            if pack_id not in packs:
                issues["orphan_generation_log_references"].append(generation_id)
            if row["task_type"] not in GENERATION_TASK_TYPES:
                issues["invalid_phase3_statuses"].append(generation_id)
            try:
                logged_evidence_ids = set(json.loads(row["evidence_ids"]))
            except (json.JSONDecodeError, TypeError):
                issues["invalid_phase3_json"].append(generation_id)
                logged_evidence_ids = set()
            if pack_id in packs and logged_evidence_ids != packs[pack_id]["evidence_ids"]:
                issues["orphan_generation_log_references"].append(
                    f"{generation_id}: Evidence IDs differ from Pack"
                )

        evidence_synthetic = {
            row["evidence_id"]: bool(row["is_synthetic"])
            for row in connection.execute(
                "SELECT evidence_id, is_synthetic FROM evidence"
            ).fetchall()
        }
        brief_synthetic = {
            row["brief_id"]: bool(row["is_demo"])
            for row in connection.execute(
                "SELECT brief_id, is_demo FROM competitor_briefs"
            ).fetchall()
        }
        feed_rows = connection.execute(
            """
            SELECT feed_id, event_type, vendor_id, evidence_id, brief_id,
                   solution_categories, event_date, importance, is_synthetic
            FROM feed_events
            """
        ).fetchall()
        for row in feed_rows:
            feed_id = row["feed_id"]
            if row["event_type"] not in FEED_EVENT_TYPES or row["importance"] not in IMPORTANCE_LEVELS:
                issues["invalid_phase4_statuses"].append(feed_id)
            if row["vendor_id"] and row["vendor_id"] not in vendor_ids:
                issues["orphan_phase4_references"].append(f"{feed_id}: vendor")
            if row["evidence_id"] and row["evidence_id"] not in evidence_ids:
                issues["orphan_phase4_references"].append(f"{feed_id}: evidence")
            if row["brief_id"] and row["brief_id"] not in briefs:
                issues["orphan_phase4_references"].append(f"{feed_id}: brief")
            try:
                json.loads(row["solution_categories"])
            except (json.JSONDecodeError, TypeError):
                issues["invalid_phase4_json"].append(feed_id)
            if not _date_is_valid(row["event_date"]):
                issues["invalid_dates"].append(feed_id)
            if row["evidence_id"] and evidence_synthetic.get(row["evidence_id"]) and not row["is_synthetic"]:
                issues["synthetic_flag_mismatches"].append(feed_id)
            if row["brief_id"] and brief_synthetic.get(row["brief_id"]) and not row["is_synthetic"]:
                issues["synthetic_flag_mismatches"].append(feed_id)

        watch_rows = connection.execute(
            "SELECT watchlist_id, vendor_id FROM watchlist_entries"
        ).fetchall()
        for row in watch_rows:
            if row["vendor_id"] not in vendor_ids:
                issues["orphan_phase4_references"].append(row["watchlist_id"])

        opportunity_rows = connection.execute(
            """
            SELECT opportunity_id, opportunity_type, evidence_ids,
                   related_claim_ids, related_vendor_ids, review_status, is_synthetic
            FROM opportunities
            """
        ).fetchall()
        for row in opportunity_rows:
            opportunity_id = row["opportunity_id"]
            if (
                row["opportunity_type"] not in OPPORTUNITY_TYPES
                or row["review_status"] not in OPPORTUNITY_REVIEW_STATUSES
            ):
                issues["invalid_phase4_statuses"].append(opportunity_id)
            try:
                cited = set(json.loads(row["evidence_ids"]))
                related_claims = set(json.loads(row["related_claim_ids"]))
                related_vendors = set(json.loads(row["related_vendor_ids"]))
            except (json.JSONDecodeError, TypeError):
                issues["invalid_phase4_json"].append(opportunity_id)
                continue
            if not cited or cited - evidence_ids or related_claims - claim_ids or related_vendors - vendor_ids:
                issues["orphan_phase4_references"].append(opportunity_id)
            if any(evidence_synthetic.get(item, False) for item in cited) and not row["is_synthetic"]:
                issues["synthetic_flag_mismatches"].append(opportunity_id)

        duplicate_rows = connection.execute(
            """
            SELECT g.duplicate_group_id, g.primary_evidence_id,
                   SUM(CASE WHEN m.member_role = 'PRIMARY' THEN 1 ELSE 0 END) AS primary_count,
                   COUNT(m.evidence_id) AS member_count
            FROM duplicate_groups g
            LEFT JOIN duplicate_group_members m
              ON m.duplicate_group_id = g.duplicate_group_id
            GROUP BY g.duplicate_group_id, g.primary_evidence_id
            """
        ).fetchall()
        for row in duplicate_rows:
            if (
                row["primary_evidence_id"] not in evidence_ids
                or int(row["primary_count"]) != 1
                or int(row["member_count"]) < 2
            ):
                issues["invalid_duplicate_groups"].append(row["duplicate_group_id"])

        for table, id_column, reference_column, valid_references in (
            ("brief_reviews", "brief_id", "brief_id", set(briefs)),
            ("claim_review_notes", "note_id", "claim_id", claim_ids),
            ("saved_comparisons", "comparison_id", "brief_id", set(briefs)),
            ("executive_briefs", "executive_brief_id", "brief_id", set(briefs)),
            ("sales_enablement_outputs", "sales_output_id", "brief_id", set(briefs)),
        ):
            rows = connection.execute(
                f"SELECT {id_column}, {reference_column} FROM {table}"
            ).fetchall()
            for row in rows:
                if row[reference_column] not in valid_references:
                    issues["orphan_phase4_references"].append(row[id_column])

        for table, id_column, json_fields in (
            ("saved_comparisons", "comparison_id", ("selected_vendors", "claim_ids")),
            ("executive_briefs", "executive_brief_id", ("sections", "feed_ids", "evidence_ids")),
            ("sales_enablement_outputs", "sales_output_id", ("sections", "source_claim_ids", "evidence_ids")),
        ):
            rows = connection.execute(
                f"SELECT {id_column}, {', '.join(json_fields)} FROM {table}"
            ).fetchall()
            for row in rows:
                try:
                    for field in json_fields:
                        json.loads(row[field])
                except (json.JSONDecodeError, TypeError):
                    issues["invalid_phase4_json"].append(row[id_column])

        feed_ids = {row["feed_id"] for row in feed_rows}
        saved_rows = connection.execute(
            "SELECT comparison_id, brief_id, selected_vendors, claim_ids, is_synthetic FROM saved_comparisons"
        ).fetchall()
        for row in saved_rows:
            try:
                saved_vendors = set(json.loads(row["selected_vendors"]))
                saved_claims = set(json.loads(row["claim_ids"]))
            except (json.JSONDecodeError, TypeError):
                continue
            if saved_vendors - vendor_ids or saved_claims - claim_ids:
                issues["orphan_phase4_references"].append(row["comparison_id"])
            if brief_synthetic.get(row["brief_id"]) and not row["is_synthetic"]:
                issues["synthetic_flag_mismatches"].append(row["comparison_id"])

        executive_rows = connection.execute(
            "SELECT executive_brief_id, brief_id, sections, feed_ids, evidence_ids, is_synthetic FROM executive_briefs"
        ).fetchall()
        for row in executive_rows:
            try:
                section_claims = {
                    item for values in json.loads(row["sections"]).values() for item in values
                }
                cited_feeds = set(json.loads(row["feed_ids"]))
                cited_evidence = set(json.loads(row["evidence_ids"]))
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue
            if section_claims - claim_ids or cited_feeds - feed_ids or cited_evidence - evidence_ids:
                issues["orphan_phase4_references"].append(row["executive_brief_id"])
            if brief_synthetic.get(row["brief_id"]) and not row["is_synthetic"]:
                issues["synthetic_flag_mismatches"].append(row["executive_brief_id"])

        sales_rows = connection.execute(
            "SELECT sales_output_id, brief_id, sections, source_claim_ids, evidence_ids, is_synthetic FROM sales_enablement_outputs"
        ).fetchall()
        for row in sales_rows:
            try:
                sections = json.loads(row["sections"])
                source_claims = set(json.loads(row["source_claim_ids"]))
                cited_evidence = set(json.loads(row["evidence_ids"]))
                item_evidence = {
                    evidence_id
                    for items in sections.values()
                    for item in items
                    for evidence_id in item.get("evidence_ids", [])
                }
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue
            if source_claims - claim_ids or cited_evidence - evidence_ids or item_evidence - evidence_ids:
                issues["orphan_phase4_references"].append(row["sales_output_id"])
            if brief_synthetic.get(row["brief_id"]) and not row["is_synthetic"]:
                issues["synthetic_flag_mismatches"].append(row["sales_output_id"])

        usage_rows = connection.execute(
            "SELECT usage_event_id, event_type FROM usage_events"
        ).fetchall()
        issues["invalid_phase4_statuses"].extend(
            row["usage_event_id"] for row in usage_rows
            if row["event_type"] not in USAGE_EVENT_TYPES
        )
        audit_rows = connection.execute(
            "SELECT audit_event_id, event_type FROM audit_events"
        ).fetchall()
        issues["invalid_phase4_statuses"].extend(
            row["audit_event_id"] for row in audit_rows
            if row["event_type"] not in AUDIT_EVENT_TYPES
        )

        benchmark_rows = connection.execute(
            """
            SELECT benchmark_id, task_type, workflow_type, vendor_ids, evidence_ids,
                   stage_times, total_minutes, vendor_count, evidence_count,
                   claim_count, brief_length, brief_id, review_result,
                   run_status, comparability_status, is_synthetic
            FROM benchmark_runs
            """
        ).fetchall()
        for row in benchmark_rows:
            benchmark_id = row["benchmark_id"]
            if (
                row["workflow_type"] not in {"MANUAL", "AI_ASSISTED"}
                or row["run_status"] not in {"DRAFT", "COMPLETE"}
                or row["comparability_status"] not in {"PENDING", "COMPARABLE", "NON_COMPARABLE"}
            ):
                issues["invalid_phase5_statuses"].append(benchmark_id)
            try:
                run_vendors = list(json.loads(row["vendor_ids"]))
                run_evidence = list(json.loads(row["evidence_ids"]))
                stage_times = json.loads(row["stage_times"])
            except (json.JSONDecodeError, TypeError):
                issues["invalid_phase5_json"].append(benchmark_id)
                continue
            expected_keys = (
                set(MANUAL_STAGE_KEYS)
                if row["workflow_type"] == "MANUAL"
                else set(AI_STAGE_KEYS)
            )
            if set(stage_times) != expected_keys:
                issues["invalid_phase5_json"].append(benchmark_id)
            if set(run_vendors) - vendor_ids or set(run_evidence) - evidence_ids:
                issues["orphan_phase5_references"].append(benchmark_id)
            if row["brief_id"] and row["brief_id"] not in briefs:
                issues["orphan_phase5_references"].append(benchmark_id)
            if len(run_vendors) != row["vendor_count"] or len(run_evidence) != row["evidence_count"]:
                issues["benchmark_total_mismatches"].append(benchmark_id)
            if abs(sum(float(value) for value in stage_times.values()) - row["total_minutes"]) > 0.00001:
                issues["benchmark_total_mismatches"].append(benchmark_id)
            if row["run_status"] == "COMPLETE" and (
                row["total_minutes"] <= 0
                or row["claim_count"] <= 0
                or row["brief_length"] <= 0
                or row["review_result"] not in {"PASS", "NEEDS_REVISION", "FAIL"}
            ):
                issues["invalid_phase5_statuses"].append(benchmark_id)
            if any(evidence_synthetic.get(item, False) for item in run_evidence) and not row["is_synthetic"]:
                issues["synthetic_flag_mismatches"].append(benchmark_id)

    passed = not any(issues.values())
    return {
        "status": "PASS" if passed else "FAIL",
        "counts": counts,
        "validation_results": validation_distribution,
        "issues": issues,
    }
