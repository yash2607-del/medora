import re
from typing import Optional, Tuple, Dict, Any
from .dictionary import CANONICAL_TEST_MAPPINGS, STANDARD_UNITS
from .reference_ranges import resolve_reference_range, calculate_status

class TestNormalizer:
    @staticmethod
    def normalize_test_name(original_name: str) -> str:
        """
        Normalize test name to standard clinical canonical form.
        If unknown, returns cleaned title-cased original name.
        """
        if not original_name:
            return "Unknown Test"
        cleaned = re.sub(r'[^a-zA-Z0-9\s\-_/]', '', original_name).strip().lower()
        # Direct dictionary match
        if cleaned in CANONICAL_TEST_MAPPINGS:
            return CANONICAL_TEST_MAPPINGS[cleaned]
        # Partial match heuristics
        for key, canonical in CANONICAL_TEST_MAPPINGS.items():
            if key == cleaned:
                return canonical
        # Fallback to original cleaned name
        return original_name.strip()

    @staticmethod
    def parse_numeric_value(raw_value: Any) -> Tuple[Optional[float], str]:
        """
        Extract float value and clean raw string representation.
        Handles things like '< 0.05', '> 200', '14.2 g/dL', 'Trace'.
        """
        if raw_value is None:
            return None, ""
        raw_str = str(raw_value).strip()
        # Find numeric component
        match = re.search(r'[-+]?\d*\.?\d+', raw_str)
        if match:
            try:
                num_val = float(match.group())
                return num_val, raw_str
            except ValueError:
                pass
        return None, raw_str

    @staticmethod
    def normalize_unit(test_name_normalized: str, original_unit: Optional[str]) -> str:
        """
        Provide standardized clinical unit or preserve original.
        """
        if original_unit and original_unit.strip():
            cleaned_unit = original_unit.strip()
            # Clean common encoding issues like /AL -> /uL
            cleaned_unit = cleaned_unit.replace("/AL", "/uL").replace("Âµ", "u").replace("µ", "u")
            return cleaned_unit
        return STANDARD_UNITS.get(test_name_normalized, "")

    @classmethod
    def process_test_entry(
        cls,
        test_name_original: str,
        raw_value: Any,
        raw_unit: Optional[str] = None,
        printed_ref_low: Optional[float] = None,
        printed_ref_high: Optional[float] = None,
        printed_ref_text: Optional[str] = None,
        laboratory: Optional[str] = "Lords Pathology"
    ) -> Dict[str, Any]:
        """
        Full deterministic pipeline for a single test:
        Name -> Normalized Name
        Value -> Parsed Float + Raw
        Unit -> Normalized Unit
        Reference Range -> Resolved (Priority)
        Status -> Deterministic Python calculation (LOW / NORMAL / HIGH)
        """
        norm_name = cls.normalize_test_name(test_name_original)
        num_val, orig_val_str = cls.parse_numeric_value(raw_value)
        norm_unit = cls.normalize_unit(norm_name, raw_unit)
        
        ref_low, ref_high, ref_text = resolve_reference_range(
            test_name_normalized=norm_name,
            printed_low=printed_ref_low,
            printed_high=printed_ref_high,
            printed_text=printed_ref_text,
            laboratory=laboratory
        )

        status = calculate_status(
            value=num_val,
            reference_low=ref_low,
            reference_high=ref_high,
            original_value_str=orig_val_str
        )

        return {
            "test_name_original": test_name_original,
            "test_name_normalized": norm_name,
            "original_value": orig_val_str,
            "original_unit": raw_unit or "",
            "normalized_value": num_val,
            "normalized_unit": norm_unit,
            "reference_low": ref_low,
            "reference_high": ref_high,
            "reference_text": ref_text,
            "status": status
        }

