"""
Tests for longitudinal trend and historical comparison engine.
Verifies Section 14, 15 & 16: Chronological sorting, trend detection, zero LLM math.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from patient.correlation.longitudinal_analyzer import LongitudinalAnalyzer

class TestLongitudinalAnalyzer(unittest.TestCase):
    def test_improving_trend(self):
        # ALT from 82 HIGH on Jan 1 to 55 NORMAL on Apr 1
        history = [
            {"report_id": "R1", "report_date": "2025-01-01", "normalized_value": 82.0, "status": "HIGH", "reference_low": 7.0, "reference_high": 56.0, "normalized_unit": "U/L"},
            {"report_id": "R2", "report_date": "2025-04-01", "normalized_value": 55.0, "status": "NORMAL", "reference_low": 7.0, "reference_high": 56.0, "normalized_unit": "U/L"}
        ]
        result = LongitudinalAnalyzer.analyze_test_series("ALT", history)
        self.assertEqual(result["trend"], "improving")
        self.assertEqual(result["persistence"], "previously_abnormal_now_normal")
        self.assertEqual(result["absolute_change"], -27.0)
        self.assertEqual(result["percentage_change"], -32.9)
        self.assertIn("decreased from 82.0", result["deterministic_statement"])

    def test_worsening_trend(self):
        # Fasting Glucose from 92 NORMAL on Jan 1 to 140 HIGH on Apr 1
        history = [
            {"report_id": "R1", "report_date": "2025-01-01", "normalized_value": 92.0, "status": "NORMAL", "reference_low": 70.0, "reference_high": 100.0, "normalized_unit": "mg/dL"},
            {"report_id": "R2", "report_date": "2025-04-01", "normalized_value": 140.0, "status": "HIGH", "reference_low": 70.0, "reference_high": 100.0, "normalized_unit": "mg/dL"}
        ]
        result = LongitudinalAnalyzer.analyze_test_series("Fasting Glucose", history)
        self.assertEqual(result["trend"], "worsening")
        self.assertEqual(result["persistence"], "newly_abnormal")
        self.assertEqual(result["absolute_change"], 48.0)
        self.assertIn("increased from 92.0", result["deterministic_statement"])

    def test_persistently_abnormal(self):
        # Creatinine 1.8 HIGH on Jan 1 to 1.9 HIGH on Apr 1
        history = [
            {"report_id": "R1", "report_date": "2025-01-01", "normalized_value": 1.8, "status": "HIGH", "reference_low": 0.6, "reference_high": 1.2, "normalized_unit": "mg/dL"},
            {"report_id": "R2", "report_date": "2025-04-01", "normalized_value": 1.9, "status": "HIGH", "reference_low": 0.6, "reference_high": 1.2, "normalized_unit": "mg/dL"}
        ]
        result = LongitudinalAnalyzer.analyze_test_series("Creatinine", history)
        self.assertEqual(result["persistence"], "persistently_abnormal")
        self.assertEqual(result["trend"], "worsening")

    def test_stable_normal(self):
        history = [
            {"report_id": "R1", "report_date": "2025-01-01", "normalized_value": 14.5, "status": "NORMAL", "reference_low": 12.0, "reference_high": 17.0, "normalized_unit": "g/dL"},
            {"report_id": "R2", "report_date": "2025-04-01", "normalized_value": 14.6, "status": "NORMAL", "reference_low": 12.0, "reference_high": 17.0, "normalized_unit": "g/dL"}
        ]
        result = LongitudinalAnalyzer.analyze_test_series("Hemoglobin", history)
        self.assertEqual(result["trend"], "stable")
        self.assertEqual(result["persistence"], "stable_normal")

if __name__ == "__main__":
    unittest.main()

