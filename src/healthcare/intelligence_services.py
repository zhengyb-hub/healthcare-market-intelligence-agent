"""Vendor Intelligence, Comparison, Brief, and audit-log orchestration."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from time import perf_counter
from typing import Any
from uuid import uuid4

from .ai_service import AIService
from .claim_service import ClaimService
from .demo_intelligence import build_comparison_demo_output, build_vendor_demo_output
from .evidence_pack_service import EvidencePackService
from .intelligence_models import (
    CompetitorBrief,
    GenerationLog,
    VendorIntelligenceProfile,
)
from .intelligence_export import IntelligenceExportService
from .intelligence_repositories import (
    BriefRepository,
    ClaimRepository,
    GenerationLogRepository,
    VendorProfileRepository,
)
from .models import Evidence, Vendor, utc_now
from .repositories import EvidenceRepository, VendorRepository
from .traceability_service import TraceabilityService


class BriefService:
    def __init__(
        self,
        repository: BriefRepository,
        claim_service: ClaimService,
    ) -> None:
        self.repository = repository
        self.claim_service = claim_service
        self.event_handler: Any | None = None

    def create_from_structured_output(
        self,
        title: str,
        vendor_ids: list[str],
        brief_type: str,
        evidence_pack_id: str,
        payload: dict[str, Any],
        model: str,
        prompt_version: str,
        is_demo: bool,
    ) -> CompetitorBrief:
        brief_id = f"brief_{uuid4().hex}"
        claim_ids = [f"claim_{uuid4().hex}" for _ in payload["claims"]]
        sections = {
            section_name: [claim_ids[index] for index in indexes]
            for section_name, indexes in payload["sections"].items()
        }
        brief = CompetitorBrief(
            brief_id=brief_id,
            title=title,
            vendor_ids=vendor_ids,
            brief_type=brief_type,
            evidence_pack_id=evidence_pack_id,
            claims=[],
            executive_summary=payload["executive_summary"],
            sections=sections,
            generated_at=utc_now(),
            status="DRAFT",
            model=model,
            prompt_version=prompt_version,
            is_demo=is_demo,
        )
        self.repository.create(brief)
        for claim_id, claim_values in zip(claim_ids, payload["claims"]):
            self.claim_service.create_claim(
                {
                    "claim_id": claim_id,
                    "brief_id": brief_id,
                    "vendor_id": claim_values["vendor_id"],
                    "claim_text": claim_values["claim_text"],
                    "claim_type": claim_values["claim_type"],
                    "evidence_ids": claim_values["evidence_ids"],
                    "explanation": claim_values["explanation"],
                }
            )
        result = self.repository.get(brief_id)
        if result is None:
            raise RuntimeError("Brief persistence failed")
        if self.event_handler is not None:
            self.event_handler.brief_generated(result)
        return result


@dataclass(slots=True)
class MarketIntelligenceServices:
    evidence_pack_service: EvidencePackService
    claim_service: ClaimService
    traceability_service: TraceabilityService
    brief_service: BriefService
    vendor_intelligence_service: "VendorIntelligenceService"
    comparison_service: "ComparisonService"
    brief_repository: BriefRepository
    claim_repository: ClaimRepository
    profile_repository: VendorProfileRepository
    generation_log_repository: GenerationLogRepository
    export_service: IntelligenceExportService

    def statistics(self) -> dict[str, Any]:
        support = self.claim_repository.counts_by_support()
        invalid_citations = 0
        validation_results: list[str] = []
        for brief in self.brief_repository.list_all():
            report = self.traceability_service.validate_brief(
                brief.brief_id,
                update_claims=False,
            )
            invalid_citations += report["invalid_citations_detected"]
            validation_results.append(report["result"])
        return {
            "evidence_packs_created": self.evidence_pack_service.repository.count(),
            "vendor_intelligence_profiles": self.profile_repository.count(),
            "comparisons_generated": self.brief_repository.count("COMPARISON"),
            "competitor_briefs": self.brief_repository.count(),
            "claims_generated": self.claim_repository.count(),
            "supported_claims": support.get("SUPPORTED", 0),
            "partially_supported_claims": support.get("PARTIALLY_SUPPORTED", 0),
            "unsupported_claims": support.get("UNSUPPORTED", 0),
            "invalid_citations": invalid_citations,
            "traceability_validation": (
                "PASS" if all(item == "PASS" for item in validation_results) else "FAIL"
            ),
            "generation_logs": self.generation_log_repository.count(),
        }


class VendorIntelligenceService:
    def __init__(
        self,
        vendor_repository: VendorRepository,
        evidence_repository: EvidenceRepository,
        pack_service: EvidencePackService,
        ai_service: AIService,
        brief_service: BriefService,
        profile_repository: VendorProfileRepository,
        log_repository: GenerationLogRepository,
        traceability_service: TraceabilityService,
    ) -> None:
        self.vendor_repository = vendor_repository
        self.evidence_repository = evidence_repository
        self.pack_service = pack_service
        self.ai_service = ai_service
        self.brief_service = brief_service
        self.profile_repository = profile_repository
        self.log_repository = log_repository
        self.traceability_service = traceability_service

    def generate(
        self,
        vendor_id: str,
        include_warning: bool = False,
        api_key: str = "",
        model: str = "gpt-5.6",
        client: Any | None = None,
        stage_times: dict[str, float] | None = None,
    ) -> tuple[VendorIntelligenceProfile, CompetitorBrief, dict[str, Any]]:
        vendor = self.vendor_repository.get(vendor_id)
        if vendor is None:
            raise ValueError(f"Unknown vendor_id: {vendor_id}")
        started = perf_counter()
        pack = self.pack_service.create_pack(
            [vendor_id],
            include_warning=include_warning,
            max_evidence_per_vendor=20,
        )
        if stage_times is not None:
            stage_times["ai_pack_minutes"] = (perf_counter() - started) / 60
        evidence = self.pack_service.evidence_for_pack(pack)
        vendor_context = [self._vendor_context(vendor)]
        started = perf_counter()
        result = self.ai_service.generate(
            "VENDOR_INTELLIGENCE",
            vendor_context,
            self.pack_service.build_llm_payload(pack),
            fallback_factory=lambda: build_vendor_demo_output(vendor, evidence),
            api_key=api_key,
            model=model,
            client=client,
        )
        is_demo = result.is_demo or pack.contains_synthetic_data
        brief = self.brief_service.create_from_structured_output(
            title=f"Healthcare Vendor Intelligence — {vendor.vendor_name}",
            vendor_ids=[vendor_id],
            brief_type="VENDOR_INTELLIGENCE",
            evidence_pack_id=pack.evidence_pack_id,
            payload=result.payload,
            model=result.model,
            prompt_version=result.prompt_version,
            is_demo=is_demo,
        )
        if stage_times is not None:
            stage_times["ai_generation_minutes"] = (perf_counter() - started) / 60
        coverage = self._coverage(evidence)
        profile = VendorIntelligenceProfile(
            profile_id=f"profile_{uuid4().hex}",
            vendor_id=vendor_id,
            brief_id=brief.brief_id,
            company_overview=vendor.company_summary,
            sections=brief.sections,
            evidence_coverage=coverage,
            last_intelligence_update=utc_now(),
            is_demo=is_demo,
        )
        self.profile_repository.create(profile)
        self.log_repository.create(
            GenerationLog(
                generation_id=f"generation_{uuid4().hex}",
                task_type="VENDOR_INTELLIGENCE",
                vendor_ids=[vendor_id],
                evidence_pack_id=pack.evidence_pack_id,
                evidence_ids=pack.evidence_ids,
                model=result.model,
                prompt_version=result.prompt_version,
                generated_at=utc_now(),
                success=True,
                error=result.fallback_reason,
                is_demo=is_demo,
            )
        )
        started = perf_counter()
        traceability = self.traceability_service.validate_brief(brief.brief_id)
        if stage_times is not None:
            stage_times["ai_validation_minutes"] = (perf_counter() - started) / 60
        return profile, self.brief_service.repository.get(brief.brief_id), traceability

    @staticmethod
    def _vendor_context(vendor: Vendor) -> dict[str, Any]:
        return {
            "vendor_id": vendor.vendor_id,
            "vendor_name": vendor.vendor_name,
            "vendor_type": vendor.vendor_type,
            "primary_market": vendor.primary_market,
            "company_summary": vendor.company_summary,
            "target_customer_types": vendor.target_customer_types,
            "is_synthetic": vendor.is_synthetic,
        }

    @staticmethod
    def _coverage(evidence: list[Evidence]) -> dict[str, Any]:
        return {
            "evidence_count": len(evidence),
            "source_types": dict(Counter(item.source_type for item in evidence)),
            "solution_categories": dict(
                Counter(category for item in evidence for category in item.solution_categories)
            ),
            "source_authority": dict(Counter(item.source_authority for item in evidence)),
            "latest_publication_date": max(
                (item.publication_date for item in evidence),
                default="",
            ),
        }


class ComparisonService:
    def __init__(
        self,
        vendor_repository: VendorRepository,
        pack_service: EvidencePackService,
        ai_service: AIService,
        brief_service: BriefService,
        log_repository: GenerationLogRepository,
        traceability_service: TraceabilityService,
    ) -> None:
        self.vendor_repository = vendor_repository
        self.pack_service = pack_service
        self.ai_service = ai_service
        self.brief_service = brief_service
        self.log_repository = log_repository
        self.traceability_service = traceability_service

    def generate(
        self,
        vendor_ids: list[str],
        include_warning: bool = False,
        api_key: str = "",
        model: str = "gpt-5.6",
        client: Any | None = None,
        stage_times: dict[str, float] | None = None,
    ) -> tuple[CompetitorBrief, dict[str, Any]]:
        unique_ids = list(dict.fromkeys(vendor_ids))
        if not 2 <= len(unique_ids) <= 5:
            raise ValueError("Comparison requires 2–5 unique Vendors")
        vendors: list[Vendor] = []
        for vendor_id in unique_ids:
            vendor = self.vendor_repository.get(vendor_id)
            if vendor is None:
                raise ValueError(f"Unknown vendor_id: {vendor_id}")
            vendors.append(vendor)
        started = perf_counter()
        pack = self.pack_service.create_pack(
            unique_ids,
            include_warning=include_warning,
            max_evidence_per_vendor=15,
        )
        if stage_times is not None:
            stage_times["ai_pack_minutes"] = (perf_counter() - started) / 60
        evidence = self.pack_service.evidence_for_pack(pack)
        started = perf_counter()
        result = self.ai_service.generate(
            "COMPARISON",
            [VendorIntelligenceService._vendor_context(vendor) for vendor in vendors],
            self.pack_service.build_llm_payload(pack),
            fallback_factory=lambda: build_comparison_demo_output(vendors, evidence),
            api_key=api_key,
            model=model,
            client=client,
        )
        is_demo = result.is_demo or pack.contains_synthetic_data
        brief = self.brief_service.create_from_structured_output(
            title="Healthcare Vendor Comparison — "
            + " vs ".join(vendor.vendor_name for vendor in vendors),
            vendor_ids=unique_ids,
            brief_type="COMPARISON",
            evidence_pack_id=pack.evidence_pack_id,
            payload=result.payload,
            model=result.model,
            prompt_version=result.prompt_version,
            is_demo=is_demo,
        )
        if stage_times is not None:
            stage_times["ai_generation_minutes"] = (perf_counter() - started) / 60
        self.log_repository.create(
            GenerationLog(
                generation_id=f"generation_{uuid4().hex}",
                task_type="COMPARISON",
                vendor_ids=unique_ids,
                evidence_pack_id=pack.evidence_pack_id,
                evidence_ids=pack.evidence_ids,
                model=result.model,
                prompt_version=result.prompt_version,
                generated_at=utc_now(),
                success=True,
                error=result.fallback_reason,
                is_demo=is_demo,
            )
        )
        started = perf_counter()
        traceability = self.traceability_service.validate_brief(brief.brief_id)
        if stage_times is not None:
            stage_times["ai_validation_minutes"] = (perf_counter() - started) / 60
        result_brief = self.brief_service.repository.get(brief.brief_id)
        if result_brief is None:
            raise RuntimeError("Comparison persistence failed")
        return result_brief, traceability
