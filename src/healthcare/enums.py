"""Controlled vocabularies for the Phase 2 Healthcare data foundation."""

VENDOR_TYPES = (
    "Healthcare IT Vendor",
    "Hospital Software Vendor",
    "Healthcare Data Vendor",
    "Digital Health Solution Provider",
    "Integrated Healthcare Technology Provider",
    "Other",
)

TARGET_CUSTOMER_TYPES = (
    "Hospital",
    "Healthcare Group",
    "Regional Health Authority",
    "Government",
    "Medical Institution",
    "Insurance / Payer",
    "Other",
)

SOURCE_TYPES = (
    "Vendor Website",
    "Solution Page",
    "Hospital Case Study",
    "Public Procurement",
    "Tender Announcement",
    "Industry Report",
    "Company Announcement",
    "Press Release",
    "News",
    "Manual Entry",
    "CSV Import",
    "JSON Import",
)

EVIDENCE_STATUSES = (
    "New",
    "Validated",
    "Needs Review",
    "Rejected",
    "Archived",
)

VALIDATION_STATUSES = (
    "Valid",
    "Warning",
    "Invalid",
)

SOURCE_AUTHORITIES = (
    "High",
    "Medium",
    "Low",
)

VENDOR_STATUSES = (
    "Active",
    "Archived",
)

URL_OPTIONAL_SOURCE_TYPES = (
    "Manual Entry",
    "CSV Import",
    "JSON Import",
)

SOURCE_AUTHORITY_GUIDANCE = {
    "Vendor Website": "High",
    "Solution Page": "High",
    "Hospital Case Study": "High",
    "Public Procurement": "High",
    "Tender Announcement": "High",
    "Company Announcement": "Medium",
    "Industry Report": "Medium",
    "Press Release": "Medium",
    "News": "Medium",
    "Manual Entry": "Low",
    "CSV Import": "Low",
    "JSON Import": "Low",
}

CLAIM_TYPES = (
    "FACT",
    "INFERENCE",
    "RECOMMENDATION",
)

SUPPORT_LEVELS = (
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "UNSUPPORTED",
)

CLAIM_REVIEW_STATUSES = (
    "PENDING",
    "APPROVED",
    "EDITED",
    "REJECTED",
    "UNSUPPORTED",
)

BRIEF_TYPES = (
    "VENDOR_INTELLIGENCE",
    "COMPARISON",
)

BRIEF_STATUSES = (
    "DRAFT",
    "IN_REVIEW",
    "NEEDS_REVISION",
    "APPROVED",
    "FINAL",
)

GENERATION_TASK_TYPES = (
    "VENDOR_INTELLIGENCE",
    "COMPARISON",
)

FEED_EVENT_TYPES = (
    "NEW_EVIDENCE",
    "VENDOR_UPDATED",
    "NEW_CASE_STUDY",
    "NEW_PROCUREMENT_SIGNAL",
    "NEW_SOLUTION_SIGNAL",
    "BRIEF_GENERATED",
    "CLAIM_REVIEWED",
    "IMPORTANT_INTELLIGENCE",
)

IMPORTANCE_LEVELS = ("LOW", "MEDIUM", "HIGH")
FRESHNESS_STATUSES = ("FRESH", "AGING", "OUTDATED")
EVIDENCE_QUALITY_LEVELS = ("HIGH", "MEDIUM", "LOW")

OPPORTUNITY_TYPES = (
    "SOLUTION_WHITE_SPACE",
    "MESSAGING_WHITE_SPACE",
    "COMPETITOR_WEAKNESS",
    "EVIDENCE_GAP",
    "SALES_ENABLEMENT",
)

OPPORTUNITY_REVIEW_STATUSES = ("PENDING", "APPROVED", "REJECTED")

USAGE_EVENT_TYPES = (
    "vendor_view",
    "evidence_view",
    "comparison_run",
    "brief_generated",
    "brief_reviewed",
    "export",
    "watchlist_add",
)

AUDIT_EVENT_TYPES = (
    "EVIDENCE_ADDED",
    "EVIDENCE_VALIDATED",
    "CLAIM_GENERATED",
    "CLAIM_EDITED",
    "CLAIM_REVIEWED",
    "BRIEF_GENERATED",
    "BRIEF_APPROVED",
    "COMPARISON_GENERATED",
    "OPPORTUNITY_GENERATED",
)
