"""SQLite persistence for the Healthcare data and intelligence foundation."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator


SCHEMA_VERSION = "6.0"


class Database:
    """Small connection factory with explicit schema initialisation."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialise(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS solution_categories (
                    category_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL,
                    parent_id TEXT,
                    status TEXT NOT NULL DEFAULT 'Active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (parent_id) REFERENCES solution_categories(category_id)
                );

                CREATE TABLE IF NOT EXISTS vendors (
                    vendor_id TEXT PRIMARY KEY,
                    vendor_name TEXT NOT NULL,
                    vendor_type TEXT NOT NULL,
                    primary_market TEXT NOT NULL,
                    company_summary TEXT NOT NULL,
                    headquarters TEXT NOT NULL,
                    website TEXT NOT NULL,
                    target_customer_types TEXT NOT NULL DEFAULT '[]',
                    evidence_count INTEGER NOT NULL DEFAULT 0,
                    last_updated TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Active',
                    is_synthetic INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_id TEXT PRIMARY KEY,
                    vendor_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_title TEXT NOT NULL,
                    source_url TEXT NOT NULL DEFAULT '',
                    publication_date TEXT NOT NULL,
                    collected_at TEXT NOT NULL,
                    raw_text TEXT NOT NULL,
                    cleaned_text TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    solution_categories TEXT NOT NULL DEFAULT '[]',
                    hospital_name TEXT NOT NULL DEFAULT '',
                    procurement_entity TEXT NOT NULL DEFAULT '',
                    project_name TEXT NOT NULL DEFAULT '',
                    contract_value TEXT NOT NULL DEFAULT '',
                    currency TEXT NOT NULL DEFAULT '',
                    evidence_status TEXT NOT NULL,
                    validation_status TEXT NOT NULL,
                    source_authority TEXT NOT NULL,
                    traceable INTEGER NOT NULL DEFAULT 0,
                    content_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_synthetic INTEGER NOT NULL DEFAULT 0,
                    duplicate_of_evidence_id TEXT NOT NULL DEFAULT '',
                    duplicate_reasons TEXT NOT NULL DEFAULT '[]',
                    validation_messages TEXT NOT NULL DEFAULT '[]',
                    FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id)
                );

                CREATE INDEX IF NOT EXISTS idx_evidence_vendor
                    ON evidence(vendor_id);
                CREATE INDEX IF NOT EXISTS idx_evidence_source_type
                    ON evidence(source_type);
                CREATE INDEX IF NOT EXISTS idx_evidence_validation
                    ON evidence(validation_status);
                CREATE INDEX IF NOT EXISTS idx_evidence_content_hash
                    ON evidence(content_hash);
                CREATE INDEX IF NOT EXISTS idx_evidence_source_url
                    ON evidence(source_url);
                CREATE INDEX IF NOT EXISTS idx_vendor_status
                    ON vendors(status);

                CREATE TABLE IF NOT EXISTS evidence_packs (
                    evidence_pack_id TEXT PRIMARY KEY,
                    vendor_ids TEXT NOT NULL,
                    evidence_ids TEXT NOT NULL,
                    selection_criteria TEXT NOT NULL,
                    contains_synthetic_data INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS competitor_briefs (
                    brief_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    vendor_ids TEXT NOT NULL,
                    brief_type TEXT NOT NULL,
                    evidence_pack_id TEXT NOT NULL,
                    executive_summary TEXT NOT NULL,
                    sections TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    is_demo INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (evidence_pack_id) REFERENCES evidence_packs(evidence_pack_id)
                );

                CREATE TABLE IF NOT EXISTS claims (
                    claim_id TEXT PRIMARY KEY,
                    brief_id TEXT NOT NULL,
                    vendor_id TEXT NOT NULL DEFAULT '',
                    claim_text TEXT NOT NULL,
                    claim_type TEXT NOT NULL,
                    evidence_ids TEXT NOT NULL,
                    traceable INTEGER NOT NULL DEFAULT 0,
                    support_level TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    explanation TEXT NOT NULL DEFAULT '',
                    reviewed_at TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (brief_id) REFERENCES competitor_briefs(brief_id)
                );

                CREATE TABLE IF NOT EXISTS vendor_intelligence_profiles (
                    profile_id TEXT PRIMARY KEY,
                    vendor_id TEXT NOT NULL,
                    brief_id TEXT NOT NULL,
                    company_overview TEXT NOT NULL,
                    sections TEXT NOT NULL,
                    evidence_coverage TEXT NOT NULL,
                    last_intelligence_update TEXT NOT NULL,
                    is_demo INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id),
                    FOREIGN KEY (brief_id) REFERENCES competitor_briefs(brief_id)
                );

                CREATE TABLE IF NOT EXISTS generation_logs (
                    generation_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    vendor_ids TEXT NOT NULL,
                    evidence_pack_id TEXT NOT NULL,
                    evidence_ids TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    error TEXT NOT NULL DEFAULT '',
                    is_demo INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (evidence_pack_id) REFERENCES evidence_packs(evidence_pack_id)
                );

                CREATE INDEX IF NOT EXISTS idx_claims_brief
                    ON claims(brief_id);
                CREATE INDEX IF NOT EXISTS idx_claims_support
                    ON claims(support_level);
                CREATE INDEX IF NOT EXISTS idx_briefs_type
                    ON competitor_briefs(brief_type);
                CREATE INDEX IF NOT EXISTS idx_profiles_vendor
                    ON vendor_intelligence_profiles(vendor_id);
                CREATE INDEX IF NOT EXISTS idx_generation_task
                    ON generation_logs(task_type);

                CREATE TABLE IF NOT EXISTS feed_events (
                    feed_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    vendor_id TEXT NOT NULL DEFAULT '',
                    evidence_id TEXT NOT NULL DEFAULT '',
                    brief_id TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    source_type TEXT NOT NULL DEFAULT '',
                    solution_categories TEXT NOT NULL DEFAULT '[]',
                    event_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    importance TEXT NOT NULL,
                    is_synthetic INTEGER NOT NULL DEFAULT 0,
                    dedupe_key TEXT NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS watchlist_entries (
                    watchlist_id TEXT PRIMARY KEY,
                    vendor_id TEXT NOT NULL UNIQUE,
                    watchlist_created_at TEXT NOT NULL,
                    last_viewed_at TEXT NOT NULL,
                    evidence_count_at_last_view INTEGER NOT NULL DEFAULT 0,
                    is_synthetic INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id)
                );

                CREATE TABLE IF NOT EXISTS opportunities (
                    opportunity_id TEXT PRIMARY KEY,
                    opportunity_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    evidence_ids TEXT NOT NULL DEFAULT '[]',
                    related_claim_ids TEXT NOT NULL DEFAULT '[]',
                    related_vendor_ids TEXT NOT NULL DEFAULT '[]',
                    evidence_statement TEXT NOT NULL,
                    inference TEXT NOT NULL,
                    recommendation TEXT NOT NULL,
                    confidence_basis TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    reviewer TEXT NOT NULL DEFAULT '',
                    reviewer_note TEXT NOT NULL DEFAULT '',
                    reviewed_at TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    is_synthetic INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS duplicate_groups (
                    duplicate_group_id TEXT PRIMARY KEY,
                    primary_evidence_id TEXT NOT NULL,
                    reasons TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (primary_evidence_id) REFERENCES evidence(evidence_id)
                );

                CREATE TABLE IF NOT EXISTS duplicate_group_members (
                    duplicate_group_id TEXT NOT NULL,
                    evidence_id TEXT NOT NULL,
                    member_role TEXT NOT NULL,
                    PRIMARY KEY (duplicate_group_id, evidence_id),
                    FOREIGN KEY (duplicate_group_id) REFERENCES duplicate_groups(duplicate_group_id),
                    FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id)
                );

                CREATE TABLE IF NOT EXISTS brief_reviews (
                    brief_id TEXT PRIMARY KEY,
                    reviewer TEXT NOT NULL DEFAULT '',
                    review_started_at TEXT NOT NULL DEFAULT '',
                    review_completed_at TEXT NOT NULL DEFAULT '',
                    review_minutes REAL NOT NULL DEFAULT 0,
                    review_notes TEXT NOT NULL DEFAULT '[]',
                    revision_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (brief_id) REFERENCES competitor_briefs(brief_id)
                );

                CREATE TABLE IF NOT EXISTS claim_review_notes (
                    note_id TEXT PRIMARY KEY,
                    claim_id TEXT NOT NULL,
                    reviewer TEXT NOT NULL,
                    note TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
                );

                CREATE TABLE IF NOT EXISTS saved_comparisons (
                    comparison_id TEXT PRIMARY KEY,
                    brief_id TEXT NOT NULL UNIQUE,
                    selected_vendors TEXT NOT NULL,
                    claim_ids TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    is_synthetic INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (brief_id) REFERENCES competitor_briefs(brief_id)
                );

                CREATE TABLE IF NOT EXISTS executive_briefs (
                    executive_brief_id TEXT PRIMARY KEY,
                    brief_id TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    sections TEXT NOT NULL,
                    feed_ids TEXT NOT NULL DEFAULT '[]',
                    evidence_ids TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    is_synthetic INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (brief_id) REFERENCES competitor_briefs(brief_id)
                );

                CREATE TABLE IF NOT EXISTS sales_enablement_outputs (
                    sales_output_id TEXT PRIMARY KEY,
                    brief_id TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    sections TEXT NOT NULL,
                    source_claim_ids TEXT NOT NULL DEFAULT '[]',
                    evidence_ids TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    is_synthetic INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (brief_id) REFERENCES competitor_briefs(brief_id)
                );

                CREATE TABLE IF NOT EXISTS usage_events (
                    usage_event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    actor TEXT NOT NULL DEFAULT '',
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    is_synthetic INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    audit_event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL DEFAULT '',
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    related_ids TEXT NOT NULL DEFAULT '{}',
                    details TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    is_synthetic INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS benchmark_runs (
                    benchmark_id TEXT PRIMARY KEY,
                    pair_id TEXT NOT NULL,
                    manifest_task_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    workflow_type TEXT NOT NULL,
                    vendor_ids TEXT NOT NULL DEFAULT '[]',
                    evidence_ids TEXT NOT NULL DEFAULT '[]',
                    output_requirement TEXT NOT NULL,
                    stage_times TEXT NOT NULL DEFAULT '{}',
                    total_minutes REAL NOT NULL DEFAULT 0,
                    started_at TEXT NOT NULL DEFAULT '',
                    ended_at TEXT NOT NULL DEFAULT '',
                    recorded_at TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    vendor_count INTEGER NOT NULL DEFAULT 0,
                    evidence_count INTEGER NOT NULL DEFAULT 0,
                    claim_count INTEGER NOT NULL DEFAULT 0,
                    brief_length INTEGER NOT NULL DEFAULT 0,
                    brief_id TEXT NOT NULL DEFAULT '',
                    review_result TEXT NOT NULL DEFAULT '',
                    edit_count INTEGER NOT NULL DEFAULT 0,
                    review_minutes REAL NOT NULL DEFAULT 0,
                    unsupported_claims_found INTEGER NOT NULL DEFAULT 0,
                    citation_errors_found INTEGER NOT NULL DEFAULT 0,
                    measurement_method TEXT NOT NULL,
                    run_status TEXT NOT NULL,
                    comparability_status TEXT NOT NULL DEFAULT 'PENDING',
                    non_comparable_reason TEXT NOT NULL DEFAULT '',
                    is_synthetic INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(pair_id, workflow_type)
                );

                CREATE TABLE IF NOT EXISTS competitor_changes (
                    change_id TEXT PRIMARY KEY,
                    vendor_id TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    significance TEXT NOT NULL,
                    headline TEXT NOT NULL,
                    before_text TEXT NOT NULL,
                    after_text TEXT NOT NULL,
                    evidence_ids TEXT NOT NULL DEFAULT '[]',
                    detected_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'NEW',
                    is_synthetic INTEGER NOT NULL DEFAULT 0,
                    fingerprint TEXT NOT NULL UNIQUE,
                    FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id)
                );

                CREATE TABLE IF NOT EXISTS marketing_action_briefs (
                    action_brief_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    audience TEXT NOT NULL,
                    channels TEXT NOT NULL DEFAULT '[]',
                    vendor_ids TEXT NOT NULL DEFAULT '[]',
                    evidence_ids TEXT NOT NULL DEFAULT '[]',
                    change_ids TEXT NOT NULL DEFAULT '[]',
                    sections TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'DRAFT',
                    created_at TEXT NOT NULL,
                    is_synthetic INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS content_opportunities (
                    content_opportunity_id TEXT PRIMARY KEY,
                    action_brief_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    content_format TEXT NOT NULL,
                    audience TEXT NOT NULL,
                    hook TEXT NOT NULL,
                    angle TEXT NOT NULL,
                    cta TEXT NOT NULL,
                    evidence_ids TEXT NOT NULL DEFAULT '[]',
                    source_change_ids TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'DRAFT',
                    created_at TEXT NOT NULL,
                    is_synthetic INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (action_brief_id) REFERENCES marketing_action_briefs(action_brief_id)
                );

                CREATE TABLE IF NOT EXISTS weekly_digests (
                    digest_id TEXT PRIMARY KEY,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    title TEXT NOT NULL,
                    sections TEXT NOT NULL DEFAULT '{}',
                    change_ids TEXT NOT NULL DEFAULT '[]',
                    evidence_ids TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    is_synthetic INTEGER NOT NULL DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_feed_date ON feed_events(event_date DESC);
                CREATE INDEX IF NOT EXISTS idx_feed_vendor ON feed_events(vendor_id);
                CREATE INDEX IF NOT EXISTS idx_feed_type ON feed_events(event_type);
                CREATE INDEX IF NOT EXISTS idx_opportunity_type ON opportunities(opportunity_type);
                CREATE INDEX IF NOT EXISTS idx_opportunity_review ON opportunities(review_status);
                CREATE INDEX IF NOT EXISTS idx_usage_type ON usage_events(event_type);
                CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_events(event_type);
                CREATE INDEX IF NOT EXISTS idx_benchmark_pair ON benchmark_runs(pair_id);
                CREATE INDEX IF NOT EXISTS idx_benchmark_task ON benchmark_runs(manifest_task_id);
                CREATE INDEX IF NOT EXISTS idx_benchmark_status
                    ON benchmark_runs(run_status, comparability_status);
                CREATE INDEX IF NOT EXISTS idx_changes_vendor
                    ON competitor_changes(vendor_id, detected_at DESC);
                CREATE INDEX IF NOT EXISTS idx_changes_significance
                    ON competitor_changes(significance, detected_at DESC);
                CREATE INDEX IF NOT EXISTS idx_content_action_brief
                    ON content_opportunities(action_brief_id);
                """
            )
            connection.execute(
                """
                UPDATE competitor_briefs
                SET status = CASE status
                    WHEN 'Generated' THEN 'DRAFT'
                    WHEN 'Needs Review' THEN 'DRAFT'
                    WHEN 'Approved' THEN 'APPROVED'
                    WHEN 'Archived' THEN 'FINAL'
                    ELSE status
                END
                """
            )
            connection.execute(
                """
                UPDATE claims
                SET review_status = CASE review_status
                    WHEN 'Pending' THEN 'PENDING'
                    WHEN 'Approved' THEN 'APPROVED'
                    WHEN 'Edited' THEN 'EDITED'
                    WHEN 'Rejected' THEN 'REJECTED'
                    WHEN 'Unsupported' THEN 'UNSUPPORTED'
                    ELSE review_status
                END
                """
            )
            connection.execute(
                """
                INSERT INTO schema_metadata(key, value)
                VALUES ('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (SCHEMA_VERSION,),
            )

    def reset_data(self) -> None:
        """Clear domain rows while retaining the schema.

        Used only by explicit demo seeding and isolated tests.
        """
        with self.connect() as connection:
            connection.execute("DELETE FROM schema_metadata WHERE key = 'phase4_demo_seeded'")
            connection.execute("DELETE FROM schema_metadata WHERE key = 'phase7_demo_seeded'")
            connection.execute("DELETE FROM content_opportunities")
            connection.execute("DELETE FROM marketing_action_briefs")
            connection.execute("DELETE FROM weekly_digests")
            connection.execute("DELETE FROM competitor_changes")
            connection.execute("DELETE FROM benchmark_runs")
            connection.execute("DELETE FROM audit_events")
            connection.execute("DELETE FROM usage_events")
            connection.execute("DELETE FROM sales_enablement_outputs")
            connection.execute("DELETE FROM executive_briefs")
            connection.execute("DELETE FROM saved_comparisons")
            connection.execute("DELETE FROM claim_review_notes")
            connection.execute("DELETE FROM brief_reviews")
            connection.execute("DELETE FROM duplicate_group_members")
            connection.execute("DELETE FROM duplicate_groups")
            connection.execute("DELETE FROM opportunities")
            connection.execute("DELETE FROM watchlist_entries")
            connection.execute("DELETE FROM feed_events")
            connection.execute("DELETE FROM generation_logs")
            connection.execute("DELETE FROM vendor_intelligence_profiles")
            connection.execute("DELETE FROM claims")
            connection.execute("DELETE FROM competitor_briefs")
            connection.execute("DELETE FROM evidence_packs")
            connection.execute("DELETE FROM evidence")
            connection.execute("DELETE FROM vendors")
            connection.execute("DELETE FROM solution_categories")

    def reset_intelligence_data(self) -> None:
        """Clear only generated Phase 3 data, preserving Phase 2 Vendors/Evidence."""
        with self.connect() as connection:
            connection.execute("DELETE FROM schema_metadata WHERE key = 'phase4_demo_seeded'")
            connection.execute("DELETE FROM schema_metadata WHERE key = 'phase7_demo_seeded'")
            connection.execute("DELETE FROM content_opportunities")
            connection.execute("DELETE FROM marketing_action_briefs")
            connection.execute("DELETE FROM weekly_digests")
            connection.execute("DELETE FROM competitor_changes")
            connection.execute("DELETE FROM benchmark_runs")
            connection.execute("DELETE FROM audit_events")
            connection.execute("DELETE FROM usage_events")
            connection.execute("DELETE FROM sales_enablement_outputs")
            connection.execute("DELETE FROM executive_briefs")
            connection.execute("DELETE FROM saved_comparisons")
            connection.execute("DELETE FROM claim_review_notes")
            connection.execute("DELETE FROM brief_reviews")
            connection.execute("DELETE FROM opportunities")
            connection.execute("DELETE FROM feed_events WHERE brief_id <> ''")
            connection.execute("DELETE FROM generation_logs")
            connection.execute("DELETE FROM vendor_intelligence_profiles")
            connection.execute("DELETE FROM claims")
            connection.execute("DELETE FROM competitor_briefs")
            connection.execute("DELETE FROM evidence_packs")
