"""Core data validation and AI brief-generation logic.

The functions in this module are deliberately independent from Streamlit so they
can be tested and reused by another interface later.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = [
    "competitor",
    "date",
    "source",
    "title",
    "content",
    "category",
]

OPTIONAL_COLUMNS = [
    "source_url",
    "collected_at",
    "item_id",
]

REPORT_SECTIONS = [
    "Executive Summary",
    "Competitor Activity Overview",
    "Content Strategy Analysis",
    "Audience and Positioning",
    "Key Marketing Insights",
    "Recommendations",
    "Limitations",
]


def validate_competitor_data(data: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize an uploaded competitor-observation dataset."""
    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in data.columns
    ]
    if missing_columns:
        raise ValueError(
            "CSV is missing required columns: " + ", ".join(missing_columns)
        )

    selected_columns = REQUIRED_COLUMNS + [
        column for column in OPTIONAL_COLUMNS if column in data.columns
    ]
    normalized = data[selected_columns].copy()
    for column in selected_columns:
        normalized[column] = normalized[column].fillna("").astype(str).str.strip()

    normalized = normalized[
        normalized["competitor"].ne("")
        & normalized["title"].ne("")
        & normalized["content"].ne("")
    ].copy()
    if normalized.empty:
        raise ValueError(
            "CSV has no usable rows after removing records without competitor, "
            "title, or content."
        )

    parsed_dates = pd.to_datetime(normalized["date"], errors="coerce")
    invalid_dates = int(parsed_dates.isna().sum())
    if invalid_dates:
        raise ValueError(
            f"CSV contains {invalid_dates} invalid date value(s). "
            "Use YYYY-MM-DD format."
        )

    normalized["date"] = parsed_dates.dt.strftime("%Y-%m-%d")
    return normalized.sort_values(
        ["date", "competitor", "category"], ascending=[False, True, True]
    ).reset_index(drop=True)


def build_evidence_payload(data: pd.DataFrame, row_limit: int = 60) -> list[dict[str, str]]:
    """Create a compact, deterministic evidence payload for the model."""
    columns = ["competitor", "date", "source", "title", "content", "category"]
    sample = data[columns].head(row_limit).copy()

    for column in columns:
        sample[column] = sample[column].astype(str).str.slice(0, 600)

    return sample.to_dict(orient="records")


def build_ai_prompt(
    data: pd.DataFrame,
    brand_name: str,
    industry: str,
    output_language: str,
) -> str:
    """Build a grounded prompt whose output can be parsed deterministically."""
    evidence = build_evidence_payload(data)
    language_instruction = (
        "Write the section content in Simplified Chinese."
        if output_language == "Chinese"
        else "Write the section content in professional, concise English."
    )

    return f"""
Create an executive-ready competitor marketing brief for the target brand.

Target brand: {brand_name}
Industry: {industry}
{language_instruction}

Use only the supplied evidence. Do not invent metrics, campaigns, dates, market
facts, or competitor behavior. Distinguish observations from recommendations.
Mention that the input may be portfolio/sample data when the source field says so.
Recommendations must be specific, prioritized, and connected to the evidence.

Return one valid JSON object and nothing else. Use exactly these keys:
{json.dumps(REPORT_SECTIONS, ensure_ascii=False)}

Each value must be a Markdown string. Prefer short paragraphs and bullet lists.
Include material dataset limitations in the "Limitations" section.

Evidence:
{json.dumps(evidence, ensure_ascii=False, indent=2)}
""".strip()


def _parse_model_json(output_text: str) -> dict[str, str]:
    """Parse and validate the JSON object returned by the model."""
    text = output_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("The AI response was not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ValueError("The AI response must be a JSON object.")

    missing_sections = [section for section in REPORT_SECTIONS if section not in payload]
    if missing_sections:
        raise ValueError(
            "The AI response is missing sections: " + ", ".join(missing_sections)
        )

    sections: dict[str, str] = {}
    for section in REPORT_SECTIONS:
        value = payload[section]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"The AI response contains an empty {section} section.")
        sections[section] = value.strip()
    return sections


def generate_ai_brief_sections(
    data: pd.DataFrame,
    brand_name: str,
    industry: str,
    output_language: str,
    api_key: str,
    model: str = "gpt-5.6",
    client: Any | None = None,
) -> dict[str, str]:
    """Generate report sections with the OpenAI Responses API.

    ``client`` is injectable so the workflow can be tested without a network call.
    """
    if not api_key.strip() and client is None:
        raise ValueError("OPENAI_API_KEY is required for AI-powered generation.")

    if client is None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "The openai package is not installed. Run "
                "`pip install -r requirements.txt`."
            ) from exc
        client = OpenAI(api_key=api_key)

    prompt = build_ai_prompt(
        data=data,
        brand_name=brand_name,
        industry=industry,
        output_language=output_language,
    )
    response = client.responses.create(
        model=model,
        instructions=(
            "You are a senior marketing intelligence analyst. Produce grounded, "
            "decision-useful work and follow the requested JSON contract exactly."
        ),
        input=prompt,
    )
    output_text = getattr(response, "output_text", "")
    if not output_text:
        raise ValueError("The AI response did not contain output text.")
    return _parse_model_json(output_text)
