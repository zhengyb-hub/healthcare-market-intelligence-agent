"""Strict structured-output validation for Phase 3 LLM responses."""

from __future__ import annotations

import json
from typing import Any

from .enums import CLAIM_TYPES, SUPPORT_LEVELS


TOP_LEVEL_FIELDS = {"executive_summary", "sections", "claims"}
CLAIM_FIELDS = {
    "claim_text",
    "claim_type",
    "evidence_ids",
    "support_level",
    "explanation",
    "vendor_id",
}


def parse_json_object(output_text: str) -> dict[str, Any]:
    text = output_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:] if lines else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM response was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("LLM response must be a JSON object")
    return payload


def validate_structured_intelligence(
    payload: dict[str, Any],
    allowed_evidence_ids: set[str],
    allowed_vendor_ids: set[str],
) -> dict[str, Any]:
    unknown_top = set(payload) - TOP_LEVEL_FIELDS
    missing_top = TOP_LEVEL_FIELDS - set(payload)
    if unknown_top:
        raise ValueError("Unknown top-level fields: " + ", ".join(sorted(unknown_top)))
    if missing_top:
        raise ValueError("Missing top-level fields: " + ", ".join(sorted(missing_top)))
    if not isinstance(payload["executive_summary"], str):
        raise ValueError("executive_summary must be a string")
    if not isinstance(payload["sections"], dict):
        raise ValueError("sections must be an object")
    if not isinstance(payload["claims"], list):
        raise ValueError("claims must be a list")

    normalized_claims: list[dict[str, Any]] = []
    for index, claim in enumerate(payload["claims"]):
        if not isinstance(claim, dict):
            raise ValueError(f"Claim {index} must be an object")
        unknown_fields = set(claim) - CLAIM_FIELDS
        missing_fields = CLAIM_FIELDS - set(claim)
        if unknown_fields:
            raise ValueError(
                f"Claim {index} has unknown fields: " + ", ".join(sorted(unknown_fields))
            )
        if missing_fields:
            raise ValueError(
                f"Claim {index} is missing fields: " + ", ".join(sorted(missing_fields))
            )
        claim_text = claim["claim_text"]
        claim_type = str(claim["claim_type"]).upper()
        evidence_ids = claim["evidence_ids"]
        support_level = str(claim["support_level"]).upper()
        vendor_id = str(claim["vendor_id"] or "")
        if not isinstance(claim_text, str) or not claim_text.strip():
            raise ValueError(f"Claim {index} has no claim_text")
        if claim_type not in CLAIM_TYPES:
            raise ValueError(f"Claim {index} has invalid claim_type")
        if support_level not in SUPPORT_LEVELS:
            raise ValueError(f"Claim {index} has invalid support_level")
        if not isinstance(evidence_ids, list) or not all(
            isinstance(item, str) for item in evidence_ids
        ):
            raise ValueError(f"Claim {index} evidence_ids must be a list of strings")
        invalid_ids = sorted(set(evidence_ids) - allowed_evidence_ids)
        if invalid_ids:
            raise ValueError(
                f"Claim {index} cites Evidence outside the Pack: " + ", ".join(invalid_ids)
            )
        if claim_type == "FACT" and not evidence_ids:
            raise ValueError(f"Claim {index} is a FACT without Evidence")
        if vendor_id and vendor_id not in allowed_vendor_ids:
            raise ValueError(f"Claim {index} cites a Vendor outside the Pack")
        normalized_claims.append(
            {
                "claim_text": claim_text.strip(),
                "claim_type": claim_type,
                "evidence_ids": list(dict.fromkeys(evidence_ids)),
                "support_level": support_level,
                "explanation": str(claim["explanation"] or "").strip(),
                "vendor_id": vendor_id,
            }
        )

    normalized_sections: dict[str, list[int]] = {}
    for section_name, indexes in payload["sections"].items():
        if not isinstance(section_name, str) or not isinstance(indexes, list):
            raise ValueError("Section names must be strings and values must be index lists")
        if not all(isinstance(index, int) for index in indexes):
            raise ValueError(f"Section {section_name} contains a non-integer Claim index")
        if any(index < 0 or index >= len(normalized_claims) for index in indexes):
            raise ValueError(f"Section {section_name} contains an invalid Claim index")
        normalized_sections[section_name] = list(dict.fromkeys(indexes))

    return {
        "executive_summary": payload["executive_summary"].strip(),
        "sections": normalized_sections,
        "claims": normalized_claims,
    }
