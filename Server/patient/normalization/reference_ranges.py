"""
Reference Range Resolver and Deterministic Status Calculator.
CRITICAL RULE: Never ask LLM to calculate status. Use strict deterministic Python logic.
"""

from typing import Optional, Tuple, Dict, Any

# Fallback reference ranges used only when report or lab configuration does not specify
APPLICATION_FALLBACK_RANGES: Dict[str, Dict[str, Any]] = {
    "ALT": {"low": 7.0, "high": 56.0, "unit": "U/L", "text": "7.0 - 56.0 U/L"},
    "AST": {"low": 10.0, "high": 40.0, "unit": "U/L", "text": "10.0 - 40.0 U/L"},
    "Hemoglobin": {"low": 12.0, "high": 17.0, "unit": "g/dL", "text": "12.0 - 17.0 g/dL"},
    "WBC": {"low": 4000.0, "high": 11000.0, "unit": "/cumm", "text": "4,000 - 11,000 /cumm"},
    "Platelet Count": {"low": 150000.0, "high": 450000.0, "unit": "/cumm", "text": "150,000 - 450,000 /cumm"},
    "Creatinine": {"low": 0.6, "high": 1.2, "unit": "mg/dL", "text": "0.6 - 1.2 mg/dL"},
    "Urea": {"low": 15.0, "high": 45.0, "unit": "mg/dL", "text": "15.0 - 45.0 mg/dL"},
    "Fasting Glucose": {"low": 70.0, "high": 99.0, "unit": "mg/dL", "text": "70.0 - 99.0 mg/dL"},
    "HbA1c": {"low": 4.0, "high": 5.6, "unit": "%", "text": "4.0 - 5.6 %"},
    "Total Cholesterol": {"low": 0.0, "high": 200.0, "unit": "mg/dL", "text": "< 200.0 mg/dL"},
    "LDL": {"low": 0.0, "high": 100.0, "unit": "mg/dL", "text": "< 100.0 mg/dL"},
    "HDL": {"low": 40.0, "high": 60.0, "unit": "mg/dL", "text": "40.0 - 60.0 mg/dL"},
    "TSH": {"low": 0.4, "high": 4.5, "unit": "uIU/mL", "text": "0.4 - 4.5 uIU/mL"},
    "CRP": {"low": 0.0, "high": 5.0, "unit": "mg/L", "text": "< 5.0 mg/L"},
    "Vitamin D": {"low": 30.0, "high": 100.0, "unit": "ng/mL", "text": "30.0 - 100.0 ng/mL"},
    "Vitamin B12": {"low": 200.0, "high": 900.0, "unit": "pg/mL", "text": "200.0 - 900.0 pg/mL"},
    "Ferritin": {"low": 20.0, "high": 250.0, "unit": "ng/mL", "text": "20.0 - 250.0 ng/mL"},
    "Urine Protein": {"low": 0.0, "high": 20.0, "unit": "mg/dL", "text": "Negative / < 20.0 mg/dL"}
}

# Configured Laboratory Overrides (e.g., Lords Pathology specific reference ranges)
LABORATORY_CONFIGURED_RANGES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "Lords Pathology": {
        "ALT": {"low": 7.0, "high": 56.0, "unit": "U/L", "text": "7.0 - 56.0 U/L"},
        "AST": {"low": 10.0, "high": 40.0, "unit": "U/L", "text": "10.0 - 40.0 U/L"},
        "Hemoglobin": {"low": 12.0, "high": 17.5, "unit": "g/dL", "text": "12.0 - 17.5 g/dL"},
        "Creatinine": {"low": 0.5, "high": 1.2, "unit": "mg/dL", "text": "0.5 - 1.2 mg/dL"},
        "Fasting Glucose": {"low": 70.0, "high": 100.0, "unit": "mg/dL", "text": "70.0 - 100.0 mg/dL"},
        "HbA1c": {"low": 4.0, "high": 5.6, "unit": "%", "text": "4.0 - 5.6 %"},
        "TSH": {"low": 0.35, "high": 4.94, "unit": "uIU/mL", "text": "0.35 - 4.94 uIU/mL"},
        "CRP": {"low": 0.0, "high": 5.0, "unit": "mg/L", "text": "< 5.0 mg/L"}
    }
}

def resolve_reference_range(
    test_name_normalized: str,
    printed_low: Optional[float] = None,
    printed_high: Optional[float] = None,
    printed_text: Optional[str] = None,
    laboratory: Optional[str] = "Lords Pathology"
) -> Tuple[Optional[float], Optional[float], str]:
    """
    Resolve reference range using priority order:
    1. Reference range printed on uploaded report
    2. Configured laboratory reference range
    3. Application fallback range
    """
    # 1. Printed on report
    if printed_low is not None or printed_high is not None:
        ref_text = printed_text or f"{printed_low if printed_low is not None else 0} - {printed_high if printed_high is not None else 'N/A'}"
        return printed_low, printed_high, ref_text

    # 2. Configured lab range
    lab_ranges = LABORATORY_CONFIGURED_RANGES.get(laboratory or "", {})
    if test_name_normalized in lab_ranges:
        cfg = lab_ranges[test_name_normalized]
        return cfg["low"], cfg["high"], cfg["text"]

    # 3. Application fallback range
    if test_name_normalized in APPLICATION_FALLBACK_RANGES:
        fb = APPLICATION_FALLBACK_RANGES[test_name_normalized]
        return fb["low"], fb["high"], fb["text"]

    return None, None, printed_text or "Reference range not specified"


def calculate_status(
    value: Optional[float],
    reference_low: Optional[float],
    reference_high: Optional[float],
    original_value_str: Optional[str] = None
) -> str:
    """
    Deterministically computes test result status in Python:
    - value < reference_low -> LOW
    - value > reference_high -> HIGH
    - otherwise -> NORMAL
    Handles qualitative values (Negative, Positive, Normal, etc.)
    """
    if value is not None:
        if reference_low is not None and value < reference_low:
            return "LOW"
        if reference_high is not None and value > reference_high:
            return "HIGH"
        return "NORMAL"

    # Qualitative check if value is non-numeric
    if original_value_str:
        norm_str = original_value_str.strip().lower()
        if norm_str in ["negative", "nil", "normal", "non-reactive", "not detected", "absent"]:
            return "NORMAL"
        if norm_str in ["positive", "reactive", "detected", "present", "elevated", "high"]:
            return "HIGH"
        if norm_str in ["trace"]:
            return "NORMAL"

    return "NORMAL"

