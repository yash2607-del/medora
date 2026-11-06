"""
AI Patient Report Generator.
Grounds all generated report narratives strictly in deterministic Python calculations.
Uses Groq LLM API with full fallback resilience.
"""

import os
import json
from typing import Dict, Any, List
from groq import Groq
from ..prompts.patient_prompts import PATIENT_REPORT_SYSTEM_PROMPT

DISCLAIMER_TEXT = (
    "Disclaimer: This report summary is generated for educational and informational purposes only. "
    "It is not a clinical diagnosis or medical treatment plan. "
    "Please consult your physician or qualified healthcare provider to interpret these results in the context of your overall health."
)

class PatientReportGenerator:
    def __init__(self, model_name: str = None):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model_name = model_name or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self.client = None
        if self.api_key and self.api_key.strip():
            try:
                self.client = Groq(api_key=self.api_key)
            except Exception as e:
                print(f"[PatientReportGenerator] Failed to initialize Groq client: {e}")

    def generate_report(
        self,
        patient_profile: Dict[str, Any],
        report_meta: Dict[str, Any],
        current_results: List[Dict[str, Any]],
        longitudinal_trends: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generates structured AI patient report backed by evidence.
        """
        # Group current results deterministically
        abnormals = [r for r in current_results if r.get("status") in ["HIGH", "LOW"]]
        normals = [r for r in current_results if r.get("status") == "NORMAL"]

        # Group trends deterministically
        improving = [t for t in longitudinal_trends if t.get("trend") == "improving"]
        worsening = [t for t in longitudinal_trends if t.get("trend") == "worsening"]
        persistent = [t for t in longitudinal_trends if t.get("persistence") == "persistently_abnormal"]
        new_abnormal = [t for t in longitudinal_trends if t.get("persistence") == "newly_abnormal"]

        # Build structured evidence payload
        evidence_payload = {
            "patient": {
                "name": patient_profile.get("name"),
                "age": patient_profile.get("age"),
                "gender": patient_profile.get("gender")
            },
            "report": {
                "id": report_meta.get("report_id"),
                "date": report_meta.get("report_date"),
                "laboratory": report_meta.get("laboratory", "Lords Pathology"),
                "category": report_meta.get("report_category")
            },
            "current_abnormal_tests": [
                {
                    "test": r.get("test_name_normalized"),
                    "value": r.get("normalized_value"),
                    "unit": r.get("normalized_unit"),
                    "reference": r.get("reference_text"),
                    "status": r.get("status")
                }
                for r in abnormals
            ],
            "current_normal_tests": [
                {
                    "test": r.get("test_name_normalized"),
                    "value": r.get("normalized_value"),
                    "unit": r.get("normalized_unit"),
                    "reference": r.get("reference_text")
                }
                for r in normals
            ],
            "longitudinal_patterns": {
                "improving": [t.get("deterministic_statement") for t in improving],
                "worsening": [t.get("deterministic_statement") for t in worsening],
                "persistent_abnormalities": [t.get("deterministic_statement") for t in persistent],
                "newly_abnormal": [t.get("deterministic_statement") for t in new_abnormal]
            }
        }

        # Attempt LLM generation
        report_text = None
        if self.client:
            try:
                user_content = (
                    f"Please generate a patient explanation for the following verified lab report data:\n\n"
                    f"{json.dumps(evidence_payload, indent=2)}"
                )

                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": PATIENT_REPORT_SYSTEM_PROMPT},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=0.2,
                    max_tokens=900
                )
                report_text = response.choices[0].message.content
            except Exception as e:
                print(f"[PatientReportGenerator] Groq error, using deterministic generator: {e}")

        # Fallback deterministic report if LLM unavailable
        if not report_text:
            report_text = self._build_deterministic_report(evidence_payload)

        # Build summary and findings from generated content
        summary = (
            f"Report date: {report_meta.get('report_date')}. Total tests analyzed: {len(current_results)}. "
            f"Abnormal findings: {len(abnormals)}, Normal findings: {len(normals)}."
        )

        return {
            "summary": summary,
            "findings": report_text,
            "evidence": evidence_payload,
            "disclaimer": DISCLAIMER_TEXT,
            "prompt_version": "patient_report_v1"
        }

    @staticmethod
    def _build_deterministic_report(evidence: Dict[str, Any]) -> str:
        """Deterministic fallback report without calling external LLM."""
        abnormals = evidence["current_abnormal_tests"]
        normals = evidence["current_normal_tests"]
        patterns = evidence["longitudinal_patterns"]

        lines = [
            "### 1. Report Summary",
            f"This laboratory evaluation conducted at {evidence['report']['laboratory']} on {evidence['report']['date']} includes {len(abnormals) + len(normals)} diagnostic parameters.",
            "",
            "### 2. Key Findings",
            f"The assessment identified {len(abnormals)} parameter(s) requiring attention outside reference intervals.",
            "",
            "### 3. Abnormal Results (High / Low)"
        ]

        if abnormals:
            for a in abnormals:
                lines.append(f"- **{a['test']}**: {a['value']} {a['unit']} ({a['status']}) [Reference: {a['reference']}]")
        else:
            lines.append("- All evaluated parameters are currently within normal reference intervals.")

        lines.extend([
            "",
            "### 4. Normal Results",
            f"{len(normals)} test parameter(s) were within standard reference limits, including: " +
            ", ".join([n["test"] for n in normals[:6]]) + ("..." if len(normals) > 6 else "."),
            "",
            "### 5. Compared With Previous Reports"
        ])

        # Improving
        lines.append("- **Improving:**")
        if patterns["improving"]:
            for stmt in patterns["improving"]:
                lines.append(f"  * {stmt}")
        else:
            lines.append("  * No significant improving trends detected in this interval.")

        # Worsening
        lines.append("- **Worsening:**")
        if patterns["worsening"]:
            for stmt in patterns["worsening"]:
                lines.append(f"  * {stmt}")
        else:
            lines.append("  * No worsening test trends detected.")

        # Persistent
        lines.append("- **Persistent Findings:**")
        if patterns["persistent_abnormalities"]:
            for stmt in patterns["persistent_abnormalities"]:
                lines.append(f"  * {stmt}")
        else:
            lines.append("  * No persistent abnormalities noted across multiple reports.")

        # New
        lines.append("- **New Findings:**")
        if patterns["newly_abnormal"]:
            for stmt in patterns["newly_abnormal"]:
                lines.append(f"  * {stmt}")
        else:
            lines.append("  * No new abnormalities observed compared to prior baseline.")

        lines.extend([
            "",
            "### 6. General Explanation & Educational Context",
            "Laboratory values reflect physiological activity at the time of sample collection. Variations can occur due to lifestyle, hydration, nutrition, and existing clinical conditions.",
            "",
            "### 7. Recommended Physician Follow-Up",
            "Please present these findings to your consulting doctor for comprehensive correlation with your personal clinical history.",
            "",
            "### 8. Medical Disclaimer",
            DISCLAIMER_TEXT
        ])

        return "\n".join(lines)

