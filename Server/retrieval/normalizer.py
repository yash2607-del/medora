import re
from typing import Dict, List, Optional

class QueryNormalizer:
    """
    Robust query normalizer for Lord Diagnostics RAG Assistant.
    Provides single-pass regex substitution to prevent recursive cascading replacements:
    1. Typo correction (phonetic, missing letters, common misspellings)
    2. Medical acronym & short-form expansion (LFT, KFT, CBC, TSH, HbA1c, etc.)
    3. Layperson synonym expansion (sugar test -> glucose, cholesterol -> lipid, etc.)
    4. Location variations (bombay -> mumbai, nalasopara -> palghar, etc.)
    """

    TYPOS: Dict[str, str] = {
        "thyrod": "thyroid",
        "thyroide": "thyroid",
        "creatinin": "creatinine",
        "creatanine": "creatinine",
        "colestrol": "cholesterol",
        "cholestrol": "cholesterol",
        "cholesrol": "cholesterol",
        "haemoglobin": "hemoglobin",
        "hemoglobine": "hemoglobin",
        "platlet": "platelet",
        "platlets": "platelets",
        "diabetis": "diabetes",
        "diabeties": "diabetes",
        "protien": "protein",
        "electrolite": "electrolyte",
        "electrolites": "electrolytes",
        "bilirubine": "bilirubin",
        "triglicerides": "triglycerides",
        "sonograpy": "sonography",
        "sonogrophy": "sonography",
        "ultrasond": "ultrasound",
        "bombay": "mumbai",
    }

    EXPANSIONS: Dict[str, str] = {
        # High-priority multi-word phrases
        "blood sugar test": "Blood Sugar Glucose Fasting Postprandial HbA1c",
        "blood sugar": "Blood Sugar Glucose Fasting Postprandial HbA1c",
        "sugar test": "Blood Sugar Glucose Fasting Postprandial HbA1c",
        "diabetes test": "Blood Sugar Glucose Fasting Postprandial HbA1c",
        "diabetes": "Blood Sugar Glucose Fasting Postprandial HbA1c",
        "sugar": "Blood Sugar Glucose Fasting Postprandial",
        "fasting blood sugar": "Fasting Blood Sugar Glucose FBS",
        "post prandial blood sugar": "Postprandial Blood Sugar Glucose PPBS",
        "random blood sugar": "Random Blood Sugar Glucose RBS",
        
        "full body checkup": "Full Body Health Checkup Package",
        "full body check up": "Full Body Health Checkup Package",
        "body checkup": "Full Body Health Checkup Package",
        "health checkup": "Full Body Health Checkup Package",
        "health check up": "Full Body Health Checkup Package",
        "master checkup": "Full Body Health Checkup Package",

        "lipid profile": "Lipid Profile Cholesterol Triglycerides HDL LDL",
        "lipid test": "Lipid Profile Cholesterol Triglycerides HDL LDL",
        "lipid": "Lipid Profile Cholesterol Triglycerides HDL LDL",
        "cholesterol test": "Lipid Profile Cholesterol Triglycerides HDL LDL",
        "cholesterol": "Lipid Profile Cholesterol Triglycerides HDL LDL",

        "thyroid profile": "Thyroid Profile TSH T3 T4",
        "thyroid test": "Thyroid Profile TSH T3 T4",
        "thyroid": "Thyroid Profile TSH T3 T4",

        "liver function test": "Liver Function Tests LFT Bilirubin SGOT SGPT",
        "liver function": "Liver Function Tests LFT Bilirubin SGOT SGPT",
        "liver test": "Liver Function Tests LFT Bilirubin SGOT SGPT",
        "lft": "LFT Liver Function Tests Bilirubin SGOT SGPT",

        "kidney function test": "Kidney Function Test KFT Renal BUN Creatinine",
        "kidney function": "Kidney Function Test KFT Renal BUN Creatinine",
        "kidney test": "Kidney Function Test KFT Renal BUN Creatinine",
        "kft": "KFT Kidney Function Test Renal BUN Creatinine",
        "rft": "RFT Renal Function Test Kidney BUN Creatinine",

        "complete blood count": "CBC Complete Blood Count 26 parameters",
        "blood count": "CBC Complete Blood Count 26 parameters",
        "cbc": "CBC Complete Blood Count 26 parameters",

        "tsh": "TSH Thyroid Stimulating Hormone",
        "hba1c": "HbA1c Glycosylated Hemoglobin",
        "a1c": "HbA1c Glycosylated Hemoglobin",
        "fbs": "FBS Fasting Blood Sugar Glucose",
        "ppbs": "PPBS Postprandial Blood Sugar Glucose",
        "rbs": "RBS Random Blood Sugar Glucose",
        "esr": "ESR Erythrocyte Sedimentation Rate",
        "crp": "CRP C-Reactive Protein Quantitative",
        "sgpt": "SGPT ALT Alanine Aminotransferase",
        "sgot": "SGOT AST Aspartate Aminotransferase",
        "alt": "ALT SGPT Alanine Aminotransferase",
        "ast": "AST SGOT Aspartate Aminotransferase",
        "pt inr": "Prothrombin Time PT INR",
        "inr": "Prothrombin Time PT INR",
        "vdrl": "VDRL RPR Syphilis",
        "vit d3": "Vitamin D Total 25-Hydroxy",
        "vit d": "Vitamin D Total 25-Hydroxy",
        "vitamin d": "Vitamin D Total 25-Hydroxy",
        "vitamin d3": "Vitamin D Total 25-Hydroxy",
        "vit b12": "Vitamin B12",
        "vitamin b12": "Vitamin B12",
        "b12": "Vitamin B12",
        "ra factor": "RA Rheumatoid Factor Quantitative",
        "rf": "Rheumatoid Factor RA Factor",
        "hiv": "HIV 1 & 2 Antibody",
        "hbsag": "HBsAg Hepatitis B Surface Antigen",
        "hcv": "HCV Hepatitis C Antibody",
        "usg": "USG Ultrasound Sonography",
        "ecg": "ECG Electrocardiogram",

        "jaundice test": "Bilirubin Total Direct Liver Function Tests",
        "platelet count": "Platelet Count CBC Complete Blood Count",
        "platelets": "Platelet Count CBC Complete Blood Count",
        "platelet": "Platelet Count CBC Complete Blood Count",
        "hemoglobin": "Hemoglobin CBC Complete Blood Count",
        "creatinine test": "Creatinine Serum Kidney Function Test",
        "creatinine": "Creatinine Serum Kidney Function Test",
        "urine routine": "Urine Routine Examination Microscopic",
        "urine test": "Urine Routine Examination Microscopic",
        "stool test": "Stool Routine Examination Microscopic",
        "dengue test": "Dengue NS1 Antigen IgG IgM Platelet",
        "dengue": "Dengue NS1 Antigen IgG IgM Platelet",
        "malaria test": "Malaria Antigen Smear",
        "malaria": "Malaria Antigen Smear",
        "typhoid test": "Typhoid Widal Typhidot",
        "typhoid": "Typhoid Widal Typhidot",
        "widal test": "Widal Typhoid Typhidot",
        "widal": "Widal Typhoid Typhidot",
        "allergy test": "Allergy Panel Inhalation Food Specific IgE",
        "allergy panel": "Allergy Panel Inhalation Food Specific IgE",
        "allergy": "Allergy Panel Inhalation Food Specific IgE",

        # Location synonyms
        "nalasopara": "Nalasopara Palghar",
        "kalyan": "Kalyan West",
        "rabale": "Rabale Navi Mumbai",
    }

    def __init__(self):
        # Precompile regex patterns sorted by key length descending
        typo_keys = sorted(self.TYPOS.keys(), key=len, reverse=True)
        self._typo_pattern = re.compile(
            r"\b(" + "|".join(re.escape(k) for k in typo_keys) + r")\b",
            re.IGNORECASE,
        )

        expansion_keys = sorted(self.EXPANSIONS.keys(), key=len, reverse=True)
        self._expansion_pattern = re.compile(
            r"\b(" + "|".join(re.escape(k) for k in expansion_keys) + r")\b",
            re.IGNORECASE,
        )

    def normalize(self, query: str) -> str:
        """
        Normalizes typos and expands medical abbreviations/synonyms in a single pass.
        """
        if not query or not query.strip():
            return query

        text = query.strip()

        # Step 1: Typo substitution
        text = self._typo_pattern.sub(
            lambda m: self.TYPOS.get(m.group(0).lower(), m.group(0)),
            text,
        )

        # Step 2: Medical expansion (single-pass, non-recursive)
        text = self._expansion_pattern.sub(
            lambda m: self.EXPANSIONS.get(m.group(0).lower(), m.group(0)),
            text,
        )

        # Step 3: Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text
