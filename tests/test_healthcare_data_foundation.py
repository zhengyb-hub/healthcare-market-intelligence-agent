import json
from pathlib import Path
import unittest
from uuid import uuid4

from src.healthcare.bootstrap import (
    DEFAULT_TAXONOMY_PATH,
    bootstrap_data_foundation,
    build_data_foundation,
)
from src.healthcare.database import Database
from src.healthcare.demo_data import load_taxonomy
from src.healthcare.integrity import run_integrity_checks
from src.healthcare.repositories import SolutionCategoryRepository


TEST_DATA_ROOT = Path(__file__).resolve().parents[1] / "data"


def vendor_values(vendor_id="vendor_test_alpha", name="Test Alpha Health"):
    return {
        "vendor_id": vendor_id,
        "vendor_name": name,
        "vendor_type": "Healthcare IT Vendor",
        "primary_market": "Test hospitals",
        "company_summary": "Test-only healthcare vendor.",
        "headquarters": "Test City",
        "website": "https://example.test/vendor",
        "target_customer_types": ["Hospital"],
        "is_synthetic": True,
    }


def evidence_values(vendor_id="vendor_test_alpha", evidence_id=None):
    values = {
        "vendor_id": vendor_id,
        "source_type": "Vendor Website",
        "source_title": "Test HIS solution page",
        "source_url": "https://example.test/evidence/his",
        "publication_date": "2026-01-15",
        "collected_at": "2026-08-09",
        "raw_text": "A test-only description of an integrated hospital information system.",
        "solution_categories": ["his"],
        "source_authority": "High",
        "is_synthetic": True,
    }
    if evidence_id:
        values["evidence_id"] = evidence_id
    return values


class HealthcareDataFoundationTests(unittest.TestCase):
    def setUp(self):
        self.created_database_paths = []
        self.database_path = self.new_database_path("foundation")
        self.database = Database(self.database_path)
        self.database.initialise()
        category_repository = SolutionCategoryRepository(self.database)
        for category in load_taxonomy(DEFAULT_TAXONOMY_PATH):
            category_repository.upsert(category)
        self.foundation = build_data_foundation(self.database)

    def tearDown(self):
        for path in self.created_database_paths:
            for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
                candidate.unlink(missing_ok=True)

    def new_database_path(self, label):
        path = TEST_DATA_ROOT / f"test_{label}_{uuid4().hex}.db"
        self.created_database_paths.append(path)
        return path

    def create_vendor(self, **overrides):
        values = vendor_values()
        values.update(overrides)
        return self.foundation.vendor_service.create_vendor(values)

    def test_vendor_creation_uses_stable_id_not_name_as_key(self):
        first = self.create_vendor()
        second = self.create_vendor(
            vendor_id="vendor_test_beta",
            vendor_name=first.vendor_name,
        )
        self.assertNotEqual(first.vendor_id, second.vendor_id)
        self.assertEqual(first.vendor_name, second.vendor_name)
        self.assertEqual(len(self.foundation.vendor_service.list_vendors()), 2)

    def test_vendor_update(self):
        vendor = self.create_vendor()
        updated = self.foundation.vendor_service.update_vendor(
            vendor.vendor_id,
            {"company_summary": "Updated test summary.", "primary_market": "Updated market"},
        )
        self.assertEqual(updated.company_summary, "Updated test summary.")
        self.assertEqual(updated.primary_market, "Updated market")

    def test_vendor_archive_is_non_destructive(self):
        vendor = self.create_vendor()
        archived = self.foundation.vendor_service.archive_vendor(vendor.vendor_id)
        self.assertEqual(archived.status, "Archived")
        self.assertIsNotNone(self.foundation.vendor_service.get_vendor(vendor.vendor_id))
        self.assertEqual(len(self.foundation.vendor_service.list_vendors()), 0)

    def test_evidence_creation_and_persistence(self):
        vendor = self.create_vendor()
        evidence = self.foundation.evidence_service.create_evidence(
            evidence_values(vendor.vendor_id, "evidence_test_001")
        )
        loaded = self.foundation.evidence_service.get_evidence(evidence.evidence_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.vendor_id, vendor.vendor_id)
        self.assertEqual(loaded.validation_status, "Valid")
        self.assertTrue(loaded.content_hash)
        self.assertTrue(loaded.traceable)
        refreshed_vendor = self.foundation.vendor_service.get_vendor(vendor.vendor_id)
        self.assertEqual(refreshed_vendor.evidence_count, 1)
        self.assertEqual(refreshed_vendor.solution_categories, ["his"])

    def test_evidence_validation_marks_invalid_contract_value(self):
        vendor = self.create_vendor()
        values = evidence_values(vendor.vendor_id, "evidence_test_invalid")
        values.update(
            {
                "source_type": "Public Procurement",
                "contract_value": "not-a-number",
                "currency": "CNY",
            }
        )
        evidence = self.foundation.evidence_service.create_evidence(values)
        self.assertEqual(evidence.validation_status, "Invalid")
        self.assertEqual(evidence.evidence_status, "Rejected")
        self.assertTrue(any("contract_value" in item for item in evidence.validation_messages))

    def test_evidence_deduplication_marks_instead_of_deleting(self):
        vendor = self.create_vendor()
        first = self.foundation.evidence_service.create_evidence(
            evidence_values(vendor.vendor_id, "evidence_test_first")
        )
        duplicate_values = evidence_values(vendor.vendor_id, "evidence_test_duplicate")
        duplicate = self.foundation.evidence_service.create_evidence(duplicate_values)
        self.assertEqual(duplicate.duplicate_of_evidence_id, first.evidence_id)
        self.assertIn("Same URL", duplicate.duplicate_reasons)
        self.assertIn("Same Content Hash", duplicate.duplicate_reasons)
        self.assertEqual(duplicate.validation_status, "Warning")
        self.assertEqual(len(self.foundation.evidence_service.list_evidence()), 2)

    def test_csv_import(self):
        vendor = self.create_vendor()
        csv_content = (
            "evidence_id,vendor_id,source_title,publication_date,raw_text,solution_categories,is_synthetic\n"
            f"evidence_csv_001,{vendor.vendor_id},Imported CSV evidence,2026-02-01,CSV test content,his;emr_ehr,true\n"
        )
        result = self.foundation.evidence_service.import_csv(csv_content)
        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.rejected_count, 0)
        self.assertEqual(result.created[0].source_type, "CSV Import")

    def test_json_import(self):
        vendor = self.create_vendor()
        payload = {
            "evidence": [
                {
                    "evidence_id": "evidence_json_001",
                    "vendor_id": vendor.vendor_id,
                    "source_title": "Imported JSON evidence",
                    "publication_date": "2026-02-02",
                    "raw_text": "JSON test content",
                    "solution_categories": ["data_governance"],
                    "is_synthetic": True,
                }
            ]
        }
        result = self.foundation.evidence_service.import_json(json.dumps(payload))
        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.created[0].source_type, "JSON Import")

    def test_pasted_text_entry(self):
        vendor = self.create_vendor()
        evidence = self.foundation.evidence_service.add_pasted_text(
            vendor.vendor_id,
            "Pasted analyst note",
            "Pasted text for a synthetic healthcare data-platform observation.",
            "2026-02-03",
            ["healthcare_data_platform"],
            is_synthetic=True,
        )
        self.assertEqual(evidence.source_type, "Manual Entry")
        self.assertFalse(evidence.traceable)

    def test_invalid_vendor_reference_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Vendor reference"):
            self.foundation.evidence_service.create_evidence(
                evidence_values("vendor_missing", "evidence_orphan")
            )

    def test_invalid_solution_category_is_persisted_as_invalid(self):
        vendor = self.create_vendor()
        values = evidence_values(vendor.vendor_id, "evidence_bad_category")
        values["solution_categories"] = ["not_a_healthcare_category"]
        evidence = self.foundation.evidence_service.create_evidence(values)
        self.assertEqual(evidence.validation_status, "Invalid")
        self.assertTrue(any("solution category" in item for item in evidence.validation_messages))

    def test_repository_persists_across_service_instances(self):
        vendor = self.create_vendor()
        self.foundation.evidence_service.create_evidence(
            evidence_values(vendor.vendor_id, "evidence_persisted")
        )
        reopened = build_data_foundation(Database(self.database_path))
        self.assertIsNotNone(reopened.vendor_service.get_vendor(vendor.vendor_id))
        self.assertIsNotNone(reopened.evidence_service.get_evidence("evidence_persisted"))

    def test_demo_dataset_loading(self):
        demo_path = self.new_database_path("demo")
        demo = bootstrap_data_foundation(demo_path, seed_demo=True, reset_demo=True)
        stats = demo.statistics()
        self.assertEqual(stats["vendor_count"], 12)
        self.assertEqual(stats["evidence_count"], 180)
        self.assertEqual(stats["solution_category_count"], 15)
        self.assertEqual(stats["duplicate_count"], 6)
        self.assertEqual(stats["validation_statuses"], {"Valid": 168, "Warning": 9, "Invalid": 3})
        self.assertTrue(all(vendor.is_synthetic for vendor in demo.vendor_service.list_vendors()))

    def test_data_integrity_check_passes_for_demo_dataset(self):
        demo_path = self.new_database_path("integrity")
        bootstrap_data_foundation(demo_path, seed_demo=True, reset_demo=True)
        report = run_integrity_checks(Database(demo_path))
        self.assertEqual(report["status"], "PASS")
        self.assertFalse(any(report["issues"].values()))


if __name__ == "__main__":
    unittest.main()
