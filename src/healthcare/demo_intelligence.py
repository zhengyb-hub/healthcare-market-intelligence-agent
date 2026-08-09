"""Deterministic, Evidence-linked Phase 3 demo intelligence."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .models import Evidence, Vendor


def _claim(
    text: str,
    claim_type: str,
    evidence_ids: list[str],
    vendor_id: str,
    explanation: str,
) -> dict[str, Any]:
    return {
        "claim_text": text,
        "claim_type": claim_type,
        "evidence_ids": evidence_ids,
        "support_level": (
            "SUPPORTED"
            if claim_type == "FACT" and evidence_ids
            else "PARTIALLY_SUPPORTED"
            if evidence_ids
            else "UNSUPPORTED"
        ),
        "explanation": explanation,
        "vendor_id": vendor_id,
    }


def build_vendor_demo_output(
    vendor: Vendor,
    evidence: list[Evidence],
) -> dict[str, Any]:
    if not evidence:
        claims = [
            _claim(
                "INSUFFICIENT EVIDENCE: No validated Evidence was selected for this Vendor.",
                "INFERENCE",
                [],
                vendor.vendor_id,
                "The Evidence Pack is empty; no Vendor capability conclusion is generated.",
            )
        ]
        return {
            "executive_summary": "No evidence-backed intelligence could be generated.",
            "sections": {"Key Evidence": [0], "Competitive Risks": [0]},
            "claims": claims,
        }

    category_to_evidence: dict[str, list[Evidence]] = defaultdict(list)
    for item in evidence:
        for category in item.solution_categories:
            category_to_evidence[category].append(item)
    category_names = sorted(category_to_evidence)
    category_citations = [
        category_to_evidence[category][0].evidence_id
        for category in category_names[:4]
    ]
    cases = [item for item in evidence if item.source_type == "Hospital Case Study"]
    procurements = [
        item
        for item in evidence
        if item.source_type in {"Public Procurement", "Tender Announcement"}
    ]
    high_authority = [item for item in evidence if item.source_authority == "High"]
    basis = (high_authority or evidence)[:3]
    messaging_basis = evidence[:2]
    customer_signal_evidence = [
        item
        for item in evidence
        if item.source_type
        in {"Hospital Case Study", "Public Procurement", "Tender Announcement"}
    ]
    observed_customer_signals: list[str] = []
    if any(item.source_type == "Hospital Case Study" for item in customer_signal_evidence):
        observed_customer_signals.extend(["Hospitals", "Medical Institutions"])
    if any(
        item.source_type in {"Public Procurement", "Tender Announcement"}
        for item in customer_signal_evidence
    ):
        observed_customer_signals.extend(["Government", "Regional Health Authorities"])

    claims = [
        _claim(
            f"{vendor.vendor_name} has selected Evidence associated with the observed solution areas: "
            + ", ".join(category_names[:6])
            + ".",
            "FACT",
            category_citations,
            vendor.vendor_id,
            "The solution areas are read directly from the cited Evidence metadata.",
        ),
        _claim(
            (
                f"{vendor.vendor_name} has {len(cases)} selected Hospital Case Study record(s)."
                if cases
                else "INSUFFICIENT EVIDENCE: No selected Hospital Case Study supports an institutional deployment claim."
            ),
            "FACT" if cases else "INFERENCE",
            [item.evidence_id for item in cases[:3]],
            vendor.vendor_id,
            "The count and statement use only selected Evidence source types.",
        ),
        _claim(
            (
                f"{vendor.vendor_name} has {len(procurements)} selected procurement or tender signal(s)."
                if procurements
                else "INSUFFICIENT EVIDENCE: No selected procurement or tender signal is available."
            ),
            "FACT" if procurements else "INFERENCE",
            [item.evidence_id for item in procurements[:3]],
            vendor.vendor_id,
            "The statement is derived from Public Procurement and Tender Announcement records.",
        ),
        _claim(
            f"The selected Evidence suggests that {vendor.vendor_name}'s observed strength is breadth across "
            f"{min(len(category_names), 6)} visible Healthcare IT solution areas.",
            "INFERENCE",
            [item.evidence_id for item in basis],
            vendor.vendor_id,
            "This is an analytical inference from category breadth and source authority, not a market ranking.",
        ),
        _claim(
            f"The current messaging evidence positions {vendor.vendor_name} around integrated Healthcare IT delivery and operational use cases.",
            "INFERENCE",
            [item.evidence_id for item in messaging_basis],
            vendor.vendor_id,
            "This inference is based on the cited source titles, summaries, and cleaned text.",
        ),
        _claim(
            (
                "The selected source mix provides observable target-customer signals for: "
                + ", ".join(dict.fromkeys(observed_customer_signals))
                + "."
                if observed_customer_signals
                else "INSUFFICIENT EVIDENCE: No institutional or procurement source supports a target-customer signal."
            ),
            "INFERENCE",
            [item.evidence_id for item in customer_signal_evidence[:4]],
            vendor.vendor_id,
            "Target-customer signals are inferred only from selected Hospital Case Study, Public Procurement, and Tender Evidence.",
        ),
        _claim(
            f"Marketing and sales teams should prioritise claims that can cite {vendor.vendor_name}'s validated institutional, procurement, and solution Evidence.",
            "RECOMMENDATION",
            [item.evidence_id for item in basis],
            vendor.vendor_id,
            "Recommendation based on the preceding Evidence-backed coverage and signal Claims.",
        ),
        _claim(
            "INSUFFICIENT EVIDENCE: Market share, revenue, customer totals, and industry ranking cannot be determined from this Evidence Pack.",
            "INFERENCE",
            [],
            vendor.vendor_id,
            "The system explicitly preserves an unsupported scenario rather than inventing metrics.",
        ),
    ]
    return {
        "executive_summary": (
            f"Evidence-grounded Vendor intelligence for {vendor.vendor_name}, generated from "
            f"{len(evidence)} selected record(s). Facts, inferences, and recommendations are separated below."
        ),
        "sections": {
            "Company / Vendor Overview": [0],
            "Vendor Overview": [0],
            "Vendor Snapshot": [0],
            "Observed Solution Areas": [0],
            "Target Customer Types": [5],
            "Solution Portfolio": [0],
            "Solution Coverage": [0],
            "Key Evidence": [0, 1, 2],
            "Institutional / Hospital Signals": [1],
            "Procurement Signals": [2],
            "Competitive Strengths": [3],
            "Competitive Weaknesses": [7],
            "Market Positioning": [4],
            "Positioning Analysis": [4],
            "Messaging Themes": [4],
            "Messaging Comparison": [4],
            "Competitive Risks": [7],
            "Opportunity Areas": [6],
            "Potential Market Gaps": [7],
            "Suggested Positioning": [6],
            "Recommended Marketing Actions": [6],
            "Sales Enablement Notes": [6],
            "Evidence Coverage": [0, 1, 2, 5],
        },
        "claims": claims,
    }


def build_comparison_demo_output(
    vendors: list[Vendor],
    evidence: list[Evidence],
) -> dict[str, Any]:
    by_vendor: dict[str, list[Evidence]] = defaultdict(list)
    for item in evidence:
        by_vendor[item.vendor_id].append(item)

    claims: list[dict[str, Any]] = []
    vendor_fact_indexes: list[int] = []
    solution_indexes: list[int] = []
    customer_signal_indexes: list[int] = []
    messaging_indexes: list[int] = []
    vendor_categories: dict[str, set[str]] = {}
    for vendor in vendors:
        items = by_vendor[vendor.vendor_id]
        categories = {
            category
            for item in items
            for category in item.solution_categories
        }
        vendor_categories[vendor.vendor_id] = categories
        citations = [item.evidence_id for item in items[:3]]
        coverage_index = len(claims)
        vendor_fact_indexes.append(coverage_index)
        claims.append(
            _claim(
                f"{vendor.vendor_name} has {len(items)} selected Evidence record(s), including "
                f"{sum(item.source_authority == 'High' for item in items)} High-authority record(s).",
                "FACT" if citations else "INFERENCE",
                citations,
                vendor.vendor_id,
                "Evidence count and authority distribution are computed from this Comparison Evidence Pack.",
            )
        )
        solution_indexes.append(len(claims))
        claims.append(
            _claim(
                f"{vendor.vendor_name}'s selected Evidence covers these observed solution areas: "
                + (", ".join(sorted(categories)[:8]) if categories else "INSUFFICIENT EVIDENCE"),
                "FACT" if citations and categories else "INFERENCE",
                citations if categories else [],
                vendor.vendor_id,
                "Observed capabilities are limited to solution-category metadata on selected Evidence.",
            )
        )
        signal_items = [
            item
            for item in items
            if item.source_type
            in {"Hospital Case Study", "Public Procurement", "Tender Announcement"}
        ]
        signal_types = sorted({item.source_type for item in signal_items})
        customer_signal_indexes.append(len(claims))
        claims.append(
            _claim(
                (
                    f"{vendor.vendor_name} has observable institutional or customer signals through: "
                    + ", ".join(signal_types)
                    + "."
                    if signal_items
                    else f"INSUFFICIENT EVIDENCE: {vendor.vendor_name} has no selected case or procurement customer signal."
                ),
                "INFERENCE",
                [item.evidence_id for item in signal_items[:4]],
                vendor.vendor_id,
                "Target-customer and institutional signals are inferred only from case, procurement, and tender source types.",
            )
        )
        messaging_indexes.append(len(claims))
        claims.append(
            _claim(
                f"{vendor.vendor_name}'s observable positioning and messaging themes must be interpreted from its selected source titles, summaries, and solution categories.",
                "INFERENCE",
                [item.evidence_id for item in items[:3]],
                vendor.vendor_id,
                "This is a labelled interpretation of the selected Evidence, not a claim about unobserved market position.",
            )
        )

    common_categories = set.intersection(*vendor_categories.values()) if vendor_categories else set()
    all_basis = [item.evidence_id for item in evidence[: min(6, len(evidence))]]
    claims.append(
        _claim(
            (
                "The compared Vendors share observed Evidence in: "
                + ", ".join(sorted(common_categories)[:6])
                + "."
                if common_categories
                else "INSUFFICIENT EVIDENCE: No common solution area is visible across all selected Vendors."
            ),
            "INFERENCE",
            all_basis if common_categories else [],
            "",
            "Similarity is inferred from overlapping Evidence taxonomy categories.",
        )
    )
    claims.append(
        _claim(
            "Differences in selected source coverage and solution-category breadth indicate distinct observable positioning patterns across the Vendors.",
            "INFERENCE",
            all_basis,
            "",
            "Difference is inferred from per-Vendor Evidence coverage, not unobserved product capability.",
        )
    )
    claims.append(
        _claim(
            "Position marketing and sales messages around Evidence-backed solution and institutional strengths while explicitly labelling areas with insufficient coverage.",
            "RECOMMENDATION",
            all_basis,
            "",
            "Recommendation based on the comparison Facts and category/source coverage Inferences.",
        )
    )
    claims.append(
        _claim(
            "INSUFFICIENT EVIDENCE: Comparative revenue, market share, customer totals, and implementation scale cannot be ranked from this Evidence Pack.",
            "INFERENCE",
            [],
            "",
            "The system preserves unsupported comparative metrics rather than inventing them.",
        )
    )

    similarity_index = len(claims) - 4
    difference_index = similarity_index + 1
    recommendation_index = difference_index + 1
    unsupported_index = recommendation_index + 1
    return {
        "executive_summary": (
            f"Evidence-grounded comparison of {len(vendors)} Vendors using {len(evidence)} selected record(s). "
            "The first layer is factual coverage; the second layer contains labelled analysis and recommendations."
        ),
        "sections": {
            "Evidence-backed Comparison": vendor_fact_indexes + solution_indexes,
            "Solution Categories": solution_indexes,
            "Target Customer Types": customer_signal_indexes,
            "Case and Procurement Evidence": customer_signal_indexes,
            "Source Coverage": vendor_fact_indexes,
            "Observed Capabilities": solution_indexes,
            "Positioning": messaging_indexes + [difference_index],
            "Messaging Themes": messaging_indexes,
            "Messaging Comparison": messaging_indexes + [difference_index],
            "Evidence Strength": vendor_fact_indexes,
            "Key Similarities": [similarity_index],
            "Key Differences": [difference_index],
            "Competitive Strengths": [difference_index],
            "Competitive Risks": [unsupported_index],
            "Potential Positioning Gaps": [difference_index, unsupported_index],
            "Recommended Marketing Actions": [recommendation_index],
            "Sales Enablement Notes": [recommendation_index],
        },
        "claims": claims,
    }
