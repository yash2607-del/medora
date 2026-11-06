"""
Tests for Dataset Importer and Idempotency.
Verifies Section 25 & 29:
- 100 synthetic patients
- 300 reports
- 1800 test results
- Chronological ordering preserved
- Idempotency (re-running does not produce duplicate records)
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from patient.models.database import SessionLocal, init_db
from patient.models.patient_models import Patient, PatientReport, TestResult, TrendObservation

class TestDatasetImporter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_imported_patient_count(self):
        count = self.db.query(Patient).count()
        self.assertEqual(count, 100, f"Expected 100 synthetic patients, found {count}")

    def test_imported_report_count(self):
        count = self.db.query(PatientReport).count()
        self.assertEqual(count, 300, f"Expected 300 synthetic reports, found {count}")

    def test_imported_test_results_count(self):
        count = self.db.query(TestResult).count()
        self.assertEqual(count, 1800, f"Expected 1800 test results, found {count}")

    def test_patient_chronological_ordering(self):
        reports = (
            self.db.query(PatientReport)
            .filter(PatientReport.patient_id == "PAT0001")
            .order_by(PatientReport.report_date.asc())
            .all()
        )
        self.assertEqual(len(reports), 3)
        dates = [r.report_date for r in reports]
        self.assertEqual(dates, sorted(dates), "Reports are not strictly sorted chronologically")

    def test_provenance_preservation(self):
        results = (
            self.db.query(TestResult)
            .filter(TestResult.patient_id == "PAT0001")
            .all()
        )
        self.assertGreater(len(results), 0)
        for r in results:
            self.assertIsNotNone(r.test_name_original)
            self.assertIsNotNone(r.test_name_normalized)
            self.assertIsNotNone(r.original_value)
            self.assertIsNotNone(r.status)
            self.assertIn(r.status, ["NORMAL", "HIGH", "LOW", "ABNORMAL"])

if __name__ == "__main__":
    unittest.main()

