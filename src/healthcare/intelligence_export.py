"""Structured Markdown, JSON, and Claim CSV exports."""

from __future__ import annotations

import csv
from dataclasses import asdict
import io
import json

from .intelligence_models import CompetitorBrief
from .intelligence_repositories import EvidencePackRepository
from .repositories import EvidenceRepository, VendorRepository


class IntelligenceExportService:
    def __init__(
        self,
        pack_repository: EvidencePackRepository,
        evidence_repository: EvidenceRepository,
        vendor_repository: VendorRepository,
    ) -> None:
        self.pack_repository = pack_repository
        self.evidence_repository = evidence_repository
        self.vendor_repository = vendor_repository

    def markdown(self, brief: CompetitorBrief) -> str:
        claim_by_id = {claim.claim_id: claim for claim in brief.claims}
        parts = [
            f"# {brief.title}",
            (
                f"> Brief ID: `{brief.brief_id}` · Type: `{brief.brief_type}` · "
                f"Model: `{brief.model}` · Prompt: `{brief.prompt_version}` · "
                f"Demo: `{str(brief.is_demo).lower()}`"
            ),
            "## Executive Summary\n\n" + brief.executive_summary,
        ]
        for section_name, claim_ids in brief.sections.items():
            lines: list[str] = []
            for claim_id in claim_ids:
                claim = claim_by_id.get(claim_id)
                if claim is None:
                    continue
                if claim.review_status == "REJECTED":
                    continue
                if claim.claim_type == "FACT" and claim.support_level == "UNSUPPORTED":
                    continue
                citations = (
                    " [" + ", ".join(claim.evidence_ids) + "]"
                    if claim.evidence_ids
                    else ""
                )
                lines.append(
                    f"- **{claim.claim_type} · {claim.support_level}** — "
                    f"{claim.claim_text}{citations}"
                )
            if lines:
                parts.append(f"## {section_name}\n\n" + "\n".join(lines))

        pack = self.pack_repository.get(brief.evidence_pack_id)
        source_lines: list[str] = []
        if pack:
            for evidence_id in pack.evidence_ids:
                evidence = self.evidence_repository.get(evidence_id)
                if evidence is None:
                    continue
                vendor = self.vendor_repository.get(evidence.vendor_id)
                source_lines.append(
                    f"- `{evidence.evidence_id}` — {evidence.source_title}; "
                    f"Vendor: {vendor.vendor_name if vendor else evidence.vendor_id}; "
                    f"Source: {evidence.source_type}; Date: {evidence.publication_date}; "
                    f"URL: {evidence.source_url or 'not supplied'}; "
                    f"Synthetic: {str(evidence.is_synthetic).lower()}"
                )
        parts.append("## Sources\n\n" + ("\n".join(source_lines) or "- No Evidence selected."))
        return "\n\n".join(parts)

    def json(self, brief: CompetitorBrief) -> str:
        pack = self.pack_repository.get(brief.evidence_pack_id)
        evidence = []
        if pack:
            for evidence_id in pack.evidence_ids:
                item = self.evidence_repository.get(evidence_id)
                if item is not None:
                    evidence.append(asdict(item))
        payload = {
            "brief": asdict(brief),
            "evidence_pack": asdict(pack) if pack else None,
            "evidence": evidence,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def claims_csv(self, brief: CompetitorBrief) -> str:
        output = io.StringIO()
        fieldnames = [
            "claim_id",
            "brief_id",
            "vendor_id",
            "claim_text",
            "claim_type",
            "support_level",
            "evidence_ids",
            "review_status",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for claim in brief.claims:
            writer.writerow(
                {
                    "claim_id": claim.claim_id,
                    "brief_id": claim.brief_id,
                    "vendor_id": claim.vendor_id,
                    "claim_text": claim.claim_text,
                    "claim_type": claim.claim_type,
                    "support_level": claim.support_level,
                    "evidence_ids": ";".join(claim.evidence_ids),
                    "review_status": claim.review_status,
                }
            )
        return output.getvalue()
