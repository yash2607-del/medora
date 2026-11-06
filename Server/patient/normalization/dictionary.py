"""
Patient Test Dictionary for standardizing clinical test names.
Always preserve original test name while providing standardized normalized form.
"""

# Mapping from case-insensitive variations to standard canonical names
CANONICAL_TEST_MAPPINGS = {
    # Liver
    "sgpt": "ALT",
    "alt": "ALT",
    "alanine aminotransferase": "ALT",
    "alanine transaminase": "ALT",
    "sgot": "AST",
    "ast": "AST",
    "aspartate aminotransferase": "AST",
    "aspartate transaminase": "AST",

    # Hematology
    "hb": "Hemoglobin",
    "hgb": "Hemoglobin",
    "hemoglobin": "Hemoglobin",
    "haemoglobin": "Hemoglobin",
    "wbc": "WBC",
    "total leukocyte count": "WBC",
    "total leucocyte count": "WBC",
    "tlc": "WBC",
    "white blood cells": "WBC",
    "plt": "Platelet Count",
    "platelet count": "Platelet Count",
    "platelets": "Platelet Count",

    # Kidney / Renal
    "creatinine": "Creatinine",
    "serum creatinine": "Creatinine",
    "creat": "Creatinine",
    "blood urea": "Urea",
    "urea": "Urea",
    "bun": "Urea",

    # Diabetes / Metabolic
    "fbs": "Fasting Glucose",
    "fasting glucose": "Fasting Glucose",
    "fasting blood sugar": "Fasting Glucose",
    "glucose fasting": "Fasting Glucose",
    "hba1c": "HbA1c",
    "glycated hemoglobin": "HbA1c",
    "glycated haemoglobin": "HbA1c",

    # Lipids
    "total cholesterol": "Total Cholesterol",
    "cholesterol total": "Total Cholesterol",
    "tc": "Total Cholesterol",
    "cholesterol": "Total Cholesterol",
    "ldl": "LDL",
    "ldl cholesterol": "LDL",
    "ldl-c": "LDL",
    "hdl": "HDL",
    "hdl cholesterol": "HDL",
    "hdl-c": "HDL",

    # Thyroid & Endocrine
    "tsh": "TSH",
    "thyroid stimulating hormone": "TSH",

    # Inflammation & Micronutrients
    "crp": "CRP",
    "c-reactive protein": "CRP",
    "vitamin d": "Vitamin D",
    "25-oh vitamin d": "Vitamin D",
    "25-hydroxy vitamin d": "Vitamin D",
    "vit d": "Vitamin D",
    "vitamin b12": "Vitamin B12",
    "b12": "Vitamin B12",
    "vit b12": "Vitamin B12",
    "ferritin": "Ferritin",
    "serum ferritin": "Ferritin",

    # Urinalysis
    "urine protein": "Urine Protein",
    "protein": "Urine Protein",
    "urinary protein": "Urine Protein"
}

# Standard test units
STANDARD_UNITS = {
    "ALT": "U/L",
    "AST": "U/L",
    "Hemoglobin": "g/dL",
    "WBC": "/cumm",
    "Platelet Count": "/cumm",
    "Creatinine": "mg/dL",
    "Urea": "mg/dL",
    "Fasting Glucose": "mg/dL",
    "HbA1c": "%",
    "Total Cholesterol": "mg/dL",
    "LDL": "mg/dL",
    "HDL": "mg/dL",
    "TSH": "uIU/mL",
    "CRP": "mg/L",
    "Vitamin D": "ng/mL",
    "Vitamin B12": "pg/mL",
    "Ferritin": "ng/mL",
    "Urine Protein": "mg/dL"
}

