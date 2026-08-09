"""Versioned, layered Phase 3 Healthcare intelligence prompts."""

from __future__ import annotations

import json
from typing import Any


VENDOR_INTELLIGENCE_PROMPT_VERSION = "healthcare_intelligence_v1"
COMPARISON_PROMPT_VERSION = "comparison_v1"
BRIEF_PROMPT_VERSION = "brief_generation_v1"


SYSTEM_PROMPT = (
    "You are a Healthcare IT market intelligence analyst. Return only the requested "
    "JSON structure. Never rely on unstated knowledge."
)

HEALTHCARE_DOMAIN_RULES = """
Do not invent products, hospital customers, government customers, market share,
contract values, technical metrics, customer counts, revenue, deployment scale,
government relationships, hospital partnerships, procurement outcomes, or rankings.
If Evidence is insufficient, write INSUFFICIENT EVIDENCE rather than completing a gap.
""".strip()

EVIDENCE_GROUNDING_RULES = """
Every FACT must cite one or more evidence_id values from the supplied Evidence Pack.
INFERENCE and RECOMMENDATION outputs must cite their Evidence basis. Never create or
alter an Evidence ID. FACT, INFERENCE, and RECOMMENDATION must remain distinct.
""".strip()

OUTPUT_SCHEMA_RULES = """
Return exactly one JSON object with keys: executive_summary, sections, claims.
claims must be a list of objects with exactly: claim_text, claim_type, evidence_ids,
support_level, explanation, vendor_id. claim_type is FACT, INFERENCE, or
RECOMMENDATION. support_level is SUPPORTED, PARTIALLY_SUPPORTED, or UNSUPPORTED.
sections maps section names to zero-based claim indexes. Do not include unknown fields.
""".strip()


def prompt_version_for(task_type: str) -> str:
    return (
        COMPARISON_PROMPT_VERSION
        if task_type == "COMPARISON"
        else VENDOR_INTELLIGENCE_PROMPT_VERSION
    )


def build_task_prompt(
    task_type: str,
    vendor_context: list[dict[str, Any]],
    evidence_payload: list[dict[str, Any]],
) -> str:
    task_instruction = (
        "Compare the selected Vendors across solution categories, target-customer signals, "
        "institutional/case Evidence, procurement Evidence, source coverage, observed "
        "capabilities, positioning, messaging themes, and Evidence strength. First produce "
        "evidence-backed comparison facts; then separately label similarities, differences, "
        "competitive strengths/risks, positioning gaps, and recommendations."
        if task_type == "COMPARISON"
        else "Create a Vendor Intelligence Profile covering Vendor overview, observed solution "
        "areas, target-customer signals, institutional/hospital Evidence, procurement signals, "
        "strengths, weaknesses, positioning, messaging, Evidence coverage, risks, suggested "
        "positioning, and sales enablement notes."
    )
    return "\n\n".join(
        [
            "TASK",
            task_instruction,
            "HEALTHCARE DOMAIN RULES",
            HEALTHCARE_DOMAIN_RULES,
            "EVIDENCE GROUNDING RULES",
            EVIDENCE_GROUNDING_RULES,
            "OUTPUT SCHEMA",
            OUTPUT_SCHEMA_RULES,
            "VENDOR CONTEXT",
            json.dumps(vendor_context, ensure_ascii=False, indent=2),
            "EVIDENCE PACK",
            json.dumps(evidence_payload, ensure_ascii=False, indent=2),
        ]
    )
