"""Phase 3 tests for Evidence Packs, Claims, intelligence, and traceability."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import unittest
from uuid import uuid4

from src.healthcare.ai_service import AIService
from src.healthcare.bootstrap import bootstrap_market_intelligence
from src.healthcare.demo_intelligence import build_vendor_demo_output
from src.healthcare.structured_output import validate_structured_intelligence


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class _Response:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text


class _Responses:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _Response(self.output_text)


class _Client:
    def __init__(self, output_text: str) -> None:
        self.responses = _Responses(output_text)


class Phase3MarketIntelligenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.database_path = PROJECT_ROOT / "data" / f"test_phase3_{uuid4().hex}.db"
        cls.foundation, cls.intelligence = bootstrap_market_intelligence(
            cls.database_path,
            seed_demo=True,
        )
        cls.vendors = cls.foundation.vendor_service.list_vendors()

    @classmethod
    def tearDownClass(cls) -> None:
        for suffix in ("", "-wal", "-shm"):
            path = Path(str(cls.database_path) + suffix)
            if path.exists():
                path.unlink()

    def setUp(self) -> None:
        database = self.foundation.category_repository.database
        with database.connect() as connection:
            connection.execute("DELETE FROM generation_logs")
            connection.execute("DELETE FROM vendor_intelligence_profiles")
            connection.execute("DELETE FROM claims")
            connection.execute("DELETE FROM competitor_briefs")
            connection.execute("DELETE FROM evidence_packs")

    def _vendor_evidence(self, vendor_id: str):
        return self.foundation.evidence_service.list_evidence(
            vendor_id=vendor_id,
            include_archived=True,
        )

    def _generate_vendor(self, index: int = 0):
        return self.intelligence.vendor_intelligence_service.generate(
            self.vendors[index].vendor_id,
            api_key="",
        )

    def test_evidence_pack_default_filters_invalid_warning_and_duplicates(self) -> None:
        vendor_ids = [vendor.vendor_id for vendor in self.vendors]
        pack = self.intelligence.evidence_pack_service.create_pack(vendor_ids)
        selected = self.intelligence.evidence_pack_service.evidence_for_pack(pack)

        self.assertTrue(selected)
        self.assertTrue(all(item.validation_status == "Valid" for item in selected))
        self.assertTrue(all(item.evidence_status == "Validated" for item in selected))
        self.assertTrue(all(not item.duplicate_of_evidence_id for item in selected))
        all_rows = [item for vendor_id in vendor_ids for item in self._vendor_evidence(vendor_id)]
        excluded_ids = {
            item.evidence_id
            for item in all_rows
            if item.validation_status == "Invalid" or item.duplicate_of_evidence_id
        }
        self.assertTrue(excluded_ids)
        self.assertTrue(excluded_ids.isdisjoint(pack.evidence_ids))
        self.assertEqual(pack.selection_criteria["validation_rule"], "Validated Evidence only")

    def test_warning_evidence_is_opt_in_and_transparently_recorded(self) -> None:
        vendor = self.vendors[0]
        warning_ids = {
            item.evidence_id
            for item in self._vendor_evidence(vendor.vendor_id)
            if item.validation_status == "Warning"
            and not item.duplicate_of_evidence_id
        }
        self.assertTrue(warning_ids)
        default_pack = self.intelligence.evidence_pack_service.create_pack([vendor.vendor_id])
        warning_pack = self.intelligence.evidence_pack_service.create_pack(
            [vendor.vendor_id],
            include_warning=True,
        )
        self.assertTrue(warning_ids.isdisjoint(default_pack.evidence_ids))
        self.assertTrue(warning_ids.intersection(warning_pack.evidence_ids))
        self.assertTrue(warning_pack.selection_criteria["warning_evidence_included"])

    def test_llm_payload_preserves_real_evidence_identity(self) -> None:
        vendor = self.vendors[0]
        pack = self.intelligence.evidence_pack_service.create_pack([vendor.vendor_id])
        payload = self.intelligence.evidence_pack_service.build_llm_payload(pack)
        self.assertEqual([item["evidence_id"] for item in payload], pack.evidence_ids)
        for item in payload:
            self.assertIsNotNone(
                self.foundation.evidence_service.get_evidence(item["evidence_id"])
            )
            self.assertEqual(item["vendor_id"], vendor.vendor_id)

    def test_claim_creation_support_levels_and_review(self) -> None:
        _, brief, _ = self._generate_vendor()
        pack = self.intelligence.evidence_pack_service.get_pack(brief.evidence_pack_id)
        self.assertIsNotNone(pack)
        evidence_id = pack.evidence_ids[0]
        service = self.intelligence.claim_service

        fact = service.create_claim(
            {
                "brief_id": brief.brief_id,
                "vendor_id": brief.vendor_ids[0],
                "claim_text": "A directly evidenced fact.",
                "claim_type": "FACT",
                "evidence_ids": [evidence_id],
            }
        )
        inference = service.create_claim(
            {
                "brief_id": brief.brief_id,
                "vendor_id": brief.vendor_ids[0],
                "claim_text": "An interpretation grounded in evidence.",
                "claim_type": "INFERENCE",
                "evidence_ids": [evidence_id],
            }
        )
        recommendation = service.create_claim(
            {
                "brief_id": brief.brief_id,
                "vendor_id": brief.vendor_ids[0],
                "claim_text": "A recommendation grounded in evidence.",
                "claim_type": "RECOMMENDATION",
                "evidence_ids": [evidence_id],
            }
        )
        unsupported = service.create_claim(
            {
                "brief_id": brief.brief_id,
                "vendor_id": brief.vendor_ids[0],
                "claim_text": "INSUFFICIENT EVIDENCE.",
                "claim_type": "INFERENCE",
                "evidence_ids": [],
            }
        )

        self.assertEqual(fact.support_level, "SUPPORTED")
        self.assertEqual(inference.support_level, "PARTIALLY_SUPPORTED")
        self.assertEqual(recommendation.support_level, "PARTIALLY_SUPPORTED")
        self.assertEqual(unsupported.support_level, "UNSUPPORTED")
        approved = service.review_claim(fact.claim_id, "approve")
        self.assertEqual(approved.review_status, "APPROVED")
        human_unsupported = service.review_claim(inference.claim_id, "mark unsupported")
        self.assertEqual(human_unsupported.support_level, "UNSUPPORTED")
        self.intelligence.traceability_service.validate_brief(brief.brief_id)
        persisted = self.intelligence.claim_repository.get(inference.claim_id)
        self.assertEqual(persisted.review_status, "UNSUPPORTED")
        self.assertEqual(persisted.support_level, "UNSUPPORTED")
        with self.assertRaises(ValueError):
            service.review_claim(unsupported.claim_id, "approve")

    def test_invalid_or_missing_fact_citation_is_unsupported_and_fails_validation(self) -> None:
        _, brief, _ = self._generate_vendor()
        invalid = self.intelligence.claim_service.create_claim(
            {
                "brief_id": brief.brief_id,
                "vendor_id": brief.vendor_ids[0],
                "claim_text": "This FACT uses a fabricated Evidence ID.",
                "claim_type": "FACT",
                "evidence_ids": ["evidence_does_not_exist"],
            }
        )
        missing = self.intelligence.claim_service.create_claim(
            {
                "brief_id": brief.brief_id,
                "vendor_id": brief.vendor_ids[0],
                "claim_text": "This FACT has no Evidence ID.",
                "claim_type": "FACT",
                "evidence_ids": [],
            }
        )
        report = self.intelligence.traceability_service.validate_brief(brief.brief_id)

        self.assertEqual(invalid.support_level, "UNSUPPORTED")
        self.assertEqual(missing.support_level, "UNSUPPORTED")
        self.assertEqual(report["result"], "FAIL")
        self.assertEqual(report["invalid_citations_detected"], 1)
        self.assertIn(invalid.claim_id, report["unsupported_fact_claim_ids"])
        self.assertIn(missing.claim_id, report["unsupported_fact_claim_ids"])

    def test_structured_output_rejects_unknown_fields_invalid_ids_and_fact_without_evidence(self) -> None:
        base = {
            "executive_summary": "Summary",
            "sections": {"Overview": [0]},
            "claims": [
                {
                    "claim_text": "Fact",
                    "claim_type": "FACT",
                    "evidence_ids": ["evidence_real"],
                    "support_level": "SUPPORTED",
                    "explanation": "Direct source",
                    "vendor_id": "vendor_real",
                }
            ],
        }
        valid = validate_structured_intelligence(
            base,
            {"evidence_real"},
            {"vendor_real"},
        )
        self.assertEqual(valid["claims"][0]["evidence_ids"], ["evidence_real"])

        invalid_id = json.loads(json.dumps(base))
        invalid_id["claims"][0]["evidence_ids"] = ["fabricated"]
        with self.assertRaises(ValueError):
            validate_structured_intelligence(invalid_id, {"evidence_real"}, {"vendor_real"})
        no_evidence = json.loads(json.dumps(base))
        no_evidence["claims"][0]["evidence_ids"] = []
        with self.assertRaises(ValueError):
            validate_structured_intelligence(no_evidence, {"evidence_real"}, {"vendor_real"})
        unknown = json.loads(json.dumps(base))
        unknown["unexpected"] = True
        with self.assertRaises(ValueError):
            validate_structured_intelligence(unknown, {"evidence_real"}, {"vendor_real"})

    def test_missing_api_key_and_malformed_model_output_use_explicit_demo_fallback(self) -> None:
        vendor = self.vendors[0]
        pack = self.intelligence.evidence_pack_service.create_pack([vendor.vendor_id])
        evidence = self.intelligence.evidence_pack_service.evidence_for_pack(pack)
        evidence_payload = self.intelligence.evidence_pack_service.build_llm_payload(pack)
        vendor_context = [
            self.intelligence.vendor_intelligence_service._vendor_context(vendor)
        ]
        fallback = lambda: build_vendor_demo_output(vendor, evidence)

        missing_key = AIService().generate(
            "VENDOR_INTELLIGENCE",
            vendor_context,
            evidence_payload,
            fallback,
            api_key="",
        )
        malformed = AIService().generate(
            "VENDOR_INTELLIGENCE",
            vendor_context,
            evidence_payload,
            fallback,
            api_key="test-key",
            client=_Client("not-json"),
        )

        self.assertTrue(missing_key.is_demo)
        self.assertIn("not configured", missing_key.fallback_reason)
        self.assertTrue(malformed.is_demo)
        self.assertIn("fallback used", malformed.fallback_reason)
        self.assertEqual(malformed.model, "deterministic-demo-v1")

    def test_ai_request_contains_the_exact_evidence_ids(self) -> None:
        vendor = self.vendors[0]
        pack = self.intelligence.evidence_pack_service.create_pack([vendor.vendor_id])
        evidence_payload = self.intelligence.evidence_pack_service.build_llm_payload(pack)
        first_id = pack.evidence_ids[0]
        output = {
            "executive_summary": "Grounded result",
            "sections": {"Overview": [0]},
            "claims": [
                {
                    "claim_text": "Grounded fact",
                    "claim_type": "FACT",
                    "evidence_ids": [first_id],
                    "support_level": "SUPPORTED",
                    "explanation": "Direct evidence",
                    "vendor_id": vendor.vendor_id,
                }
            ],
        }
        client = _Client(json.dumps(output))
        result = AIService().generate(
            "VENDOR_INTELLIGENCE",
            [self.intelligence.vendor_intelligence_service._vendor_context(vendor)],
            evidence_payload,
            lambda: output,
            api_key="test-key",
            client=client,
        )
        request_text = client.responses.calls[0]["input"]

        self.assertFalse(result.is_demo)
        self.assertIn(first_id, request_text)
        self.assertTrue(all(evidence_id in request_text for evidence_id in pack.evidence_ids))

    def test_vendor_intelligence_end_to_end_review_and_exports(self) -> None:
        profile, brief, report = self._generate_vendor()
        pack = self.intelligence.evidence_pack_service.get_pack(brief.evidence_pack_id)

        self.assertEqual(profile.brief_id, brief.brief_id)
        self.assertEqual(report["result"], "PASS")
        self.assertTrue(brief.sections)
        self.assertTrue(
            {
                "Company / Vendor Overview",
                "Observed Solution Areas",
                "Target Customer Types",
                "Institutional / Hospital Signals",
                "Procurement Signals",
                "Competitive Strengths",
                "Competitive Weaknesses",
                "Market Positioning",
                "Messaging Themes",
                "Evidence Coverage",
                "Sales Enablement Notes",
            }.issubset(brief.sections)
        )
        self.assertTrue(brief.claims)
        self.assertTrue(brief.is_demo)
        self.assertTrue(all(
            claim.claim_type != "FACT" or claim.evidence_ids
            for claim in brief.claims
        ))
        self.assertTrue(all(
            evidence_id in pack.evidence_ids
            for claim in brief.claims
            for evidence_id in claim.evidence_ids
        ))
        supported = next(claim for claim in brief.claims if claim.support_level == "SUPPORTED")
        reviewed = self.intelligence.claim_service.review_claim(supported.claim_id, "approve")
        self.assertEqual(reviewed.review_status, "APPROVED")

        refreshed = self.intelligence.brief_repository.get(brief.brief_id)
        markdown = self.intelligence.export_service.markdown(refreshed)
        json_payload = json.loads(self.intelligence.export_service.json(refreshed))
        csv_rows = list(csv.DictReader(io.StringIO(
            self.intelligence.export_service.claims_csv(refreshed)
        )))
        self.assertIn("## Sources", markdown)
        self.assertIn(pack.evidence_ids[0], markdown)
        self.assertEqual(json_payload["brief"]["brief_id"], brief.brief_id)
        self.assertEqual(len(csv_rows), len(brief.claims))
        self.assertEqual(
            set(csv_rows[0]),
            {
                "claim_id", "brief_id", "vendor_id", "claim_text",
                "claim_type", "support_level", "evidence_ids", "review_status",
            },
        )

    def test_comparison_end_to_end_is_structured_and_traceable(self) -> None:
        vendor_ids = [vendor.vendor_id for vendor in self.vendors[:3]]
        brief, report = self.intelligence.comparison_service.generate(
            vendor_ids,
            api_key="",
        )
        pack = self.intelligence.evidence_pack_service.get_pack(brief.evidence_pack_id)
        claim_ids = {claim.claim_id for claim in brief.claims}

        self.assertEqual(brief.brief_type, "COMPARISON")
        self.assertEqual(brief.vendor_ids, vendor_ids)
        self.assertEqual(report["result"], "PASS")
        self.assertTrue(
            {
                "Solution Categories",
                "Target Customer Types",
                "Case and Procurement Evidence",
                "Source Coverage",
                "Observed Capabilities",
                "Positioning",
                "Messaging Themes",
                "Evidence Strength",
                "Key Similarities",
                "Key Differences",
                "Competitive Risks",
            }.issubset(brief.sections)
        )
        self.assertTrue(all(
            claim_id in claim_ids
            for section_claim_ids in brief.sections.values()
            for claim_id in section_claim_ids
        ))
        self.assertTrue(all(
            evidence_id in pack.evidence_ids
            for claim in brief.claims
            for evidence_id in claim.evidence_ids
        ))
        self.assertEqual(self.intelligence.generation_log_repository.count(), 1)

    def test_comparison_requires_two_to_five_unique_vendors(self) -> None:
        with self.assertRaises(ValueError):
            self.intelligence.comparison_service.generate([self.vendors[0].vendor_id])
        with self.assertRaises(ValueError):
            self.intelligence.comparison_service.generate(
                [vendor.vendor_id for vendor in self.vendors[:6]]
            )


if __name__ == "__main__":
    unittest.main()
