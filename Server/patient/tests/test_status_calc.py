"""
Tests for deterministic status calculation and reference range resolution.
Verifies Section 12 & 13: Deterministic Python logic without LLM math.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from patient.normalization.reference_ranges import calculate_status, resolve_reference_range
from patient.normalization.normalizer import TestNormalizer

class TestStatusCalculation(unittest.TestCase):
    def test_numeric_ranges(self):
        # ALT ref: 7 - 56
        self.assertEqual(calculate_status(5.0, 7.0, 56.0), "LOW")
        self.assertEqual(calculate_status(25.0, 7.0, 56.0), "NORMAL")
        self.assertEqual(calculate_status(72.0, 7.0, 56.0), "HIGH")

    def test_boundary_values(self):
        self.assertEqual(calculate_status(7.0, 7.0, 56.0), "NORMAL")
        self.assertEqual(calculate_status(56.0, 7.0, 56.0), "NORMAL")

    def test_one_sided_range(self):
        # Total Cholesterol < 200 (low=0, high=200)
        self.assertEqual(calculate_status(180.0, 0.0, 200.0), "NORMAL")
        self.assertEqual(calculate_status(240.0, 0.0, 200.0), "HIGH")

    def test_reference_priority(self):
        # 1. Printed on report overrides configured lab range
        low, high, text = resolve_reference_range("ALT", printed_low=10.0, printed_high=50.0)
        self.assertEqual(low, 10.0)
        self.assertEqual(high, 50.0)

        # 2. Configured lab range if printed is None
        low, high, text = resolve_reference_range("ALT", printed_low=None, printed_high=None, laboratory="Lords Pathology")
        self.assertEqual(low, 7.0)
        self.assertEqual(high, 56.0)

    def test_test_normalizer_pipeline(self):
        processed = TestNormalizer.process_test_entry(
            test_name_original="SGPT",
            raw_value="72 U/L",
            raw_unit="U/L",
            printed_ref_low=7.0,
            printed_ref_high=56.0
        )
        self.assertEqual(processed["test_name_normalized"], "ALT")
        self.assertEqual(processed["normalized_value"], 72.0)
        self.assertEqual(processed["status"], "HIGH")

if __name__ == "__main__":
    unittest.main()

