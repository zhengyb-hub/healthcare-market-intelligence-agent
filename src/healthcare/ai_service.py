"""Optional OpenAI generation boundary with explicit deterministic fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .prompts import SYSTEM_PROMPT, build_task_prompt, prompt_version_for
from .structured_output import parse_json_object, validate_structured_intelligence


@dataclass(slots=True)
class IntelligenceGenerationResult:
    payload: dict[str, Any]
    model: str
    prompt_version: str
    is_demo: bool
    fallback_reason: str = ""


class AIService:
    def generate(
        self,
        task_type: str,
        vendor_context: list[dict[str, Any]],
        evidence_payload: list[dict[str, Any]],
        fallback_factory: Callable[[], dict[str, Any]],
        api_key: str = "",
        model: str = "gpt-5.6",
        client: Any | None = None,
    ) -> IntelligenceGenerationResult:
        allowed_evidence_ids = {
            str(item["evidence_id"]) for item in evidence_payload
        }
        allowed_vendor_ids = {str(item["vendor_id"]) for item in vendor_context}
        prompt_version = prompt_version_for(task_type)

        if not api_key.strip() and client is None:
            payload = validate_structured_intelligence(
                fallback_factory(),
                allowed_evidence_ids,
                allowed_vendor_ids,
            )
            return IntelligenceGenerationResult(
                payload=payload,
                model="deterministic-demo-v1",
                prompt_version=prompt_version,
                is_demo=True,
                fallback_reason="OPENAI_API_KEY is not configured",
            )

        try:
            if client is None:
                from openai import OpenAI

                client = OpenAI(api_key=api_key)
            response = client.responses.create(
                model=model,
                instructions=SYSTEM_PROMPT,
                input=build_task_prompt(task_type, vendor_context, evidence_payload),
            )
            output_text = getattr(response, "output_text", "")
            if not output_text:
                raise ValueError("LLM response did not contain output_text")
            parsed = parse_json_object(output_text)
            validated = validate_structured_intelligence(
                parsed,
                allowed_evidence_ids,
                allowed_vendor_ids,
            )
            return IntelligenceGenerationResult(
                payload=validated,
                model=model,
                prompt_version=prompt_version,
                is_demo=False,
            )
        except Exception as exc:
            fallback = validate_structured_intelligence(
                fallback_factory(),
                allowed_evidence_ids,
                allowed_vendor_ids,
            )
            return IntelligenceGenerationResult(
                payload=fallback,
                model="deterministic-demo-v1",
                prompt_version=prompt_version,
                is_demo=True,
                fallback_reason=f"LLM generation failed; deterministic fallback used: {exc}",
            )
