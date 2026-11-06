"""
Patient-Specific Conversational Q&A Service.
Answers patient questions strictly grounded in their personal lab records and longitudinal trends.
Does NOT use company RAG.
"""

import os
import json
from typing import Dict, Any, List, Optional
from groq import Groq
from ..prompts.patient_prompts import PATIENT_CHAT_SYSTEM_PROMPT
from ..generation.patient_report_generator import DISCLAIMER_TEXT

class PatientChatService:
    def __init__(self, model_name: str = None):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model_name = model_name or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self.client = None
        if self.api_key and self.api_key.strip():
            try:
                self.client = Groq(api_key=self.api_key)
            except Exception as e:
                print(f"[PatientChatService] Failed to initialize Groq: {e}")

    def answer_question(
        self,
        patient_profile: Dict[str, Any],
        query: str,
        recent_results: List[Dict[str, Any]],
        patient_trends: List[Dict[str, Any]],
        report_meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Retrieves relevant patient data points based on the user question,
        assembles structured evidence, and generates grounded answer.
        """
        q_lower = query.lower()

        # Deterministic filtering of relevant evidence
        relevant_results = []
        relevant_trends = []

        # Check for specific test inquiries
        for res in recent_results:
            t_orig = (res.get("test_name_original") or "").lower()
            t_norm = (res.get("test_name_normalized") or "").lower()
            if t_norm in q_lower or t_orig in q_lower or any(word in q_lower for word in t_norm.split()):
                relevant_results.append(res)

        for trend in patient_trends:
            t_name = (trend.get("test_name") or "").lower()
            if t_name in q_lower or any(word in q_lower for word in t_name.split()):
                relevant_trends.append(trend)

        # If general question about abnormal or changes, include abnormal & changing tests
        if any(w in q_lower for w in ["abnormal", "high", "low", "out of range"]):
            relevant_results = [r for r in recent_results if r.get("status") in ["HIGH", "LOW"]]
        elif any(w in q_lower for w in ["change", "trend", "improve", "worse", "better", "previous", "difference"]):
            relevant_trends = [t for t in patient_trends if t.get("readings_count", 1) > 1]
        elif not relevant_results and not relevant_trends:
            # Fallback to recent abnormal results and key trends
            relevant_results = recent_results[:10]
            relevant_trends = patient_trends[:6]

        # Assemble Evidence Payload
        evidence_items = []
        for r in relevant_results:
            evidence_items.append({
                "test_name": r.get("test_name_normalized"),
                "current_value": r.get("normalized_value"),
                "unit": r.get("normalized_unit"),
                "reference_range": r.get("reference_text"),
                "status": r.get("status"),
                "source_page": r.get("source_page", 1),
                "source_text": r.get("source_text")
            })

        evidence_context = {
            "patient_name": patient_profile.get("name"),
            "patient_id": patient_profile.get("patient_id"),
            "report_date": report_meta.get("report_date") if report_meta else "Latest Available",
            "relevant_tests": evidence_items,
            "longitudinal_trends": [
                {
                    "test": t.get("test_name"),
                    "statement": t.get("deterministic_statement") or t.get("evidence"),
                    "trend": t.get("trend"),
                    "persistence": t.get("persistence")
                }
                for t in relevant_trends
            ]
        }

        # Query LLM
        answer_text = None
        if self.client:
            try:
                user_msg = (
                    f"Patient Question: {query}\n\n"
                    f"Verified Patient Lab Evidence:\n{json.dumps(evidence_context, indent=2)}\n\n"
                    f"Please provide an accurate, empathetic response strictly referencing this evidence."
                )

                resp = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": PATIENT_CHAT_SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg}
                    ],
                    temperature=0.2,
                    max_tokens=500
                )
                answer_text = resp.choices[0].message.content
            except Exception as e:
                print(f"[PatientChatService] Groq query error: {e}")

        # Deterministic fallback answer if LLM offline
        if not answer_text:
            answer_text = self._build_deterministic_answer(query, evidence_context)

        return {
            "answer": answer_text,
            "patient_id": patient_profile.get("patient_id"),
            "evidence": evidence_items,
            "disclaimer": DISCLAIMER_TEXT
        }

    @staticmethod
    def _build_deterministic_answer(query: str, context: Dict[str, Any]) -> str:
        q_lower = query.lower()
        tests = context.get("relevant_tests", [])
        trends = context.get("longitudinal_trends", [])

        if any(w in q_lower for w in ["abnormal", "high", "low"]):
            abnormals = [t for t in tests if t.get("status") in ["HIGH", "LOW"]]
            if abnormals:
                items = [f"- **{t['test_name']}**: {t['current_value']} {t['unit']} ({t['status']})" for t in abnormals]
                return f"In your latest report, the following parameters were outside standard reference intervals:\n" + "\n".join(items)
            return "All reviewed parameters in your latest report are within standard reference ranges."

        if any(w in q_lower for w in ["change", "trend", "improve", "worsen"]):
            if trends:
                items = [f"- {t['statement']}" for t in trends[:5]]
                return "Here are the observed changes across your reports:\n" + "\n".join(items)
            return "No previous reports were found to compare changes against."

        if tests:
            items = [f"- **{t['test_name']}**: {t['current_value']} {t['unit']} ({t['status']})" for t in tests[:5]]
            return f"Here are the test results related to your question:\n" + "\n".join(items)

        return "I have reviewed your records. Please check the 'Latest Report' or 'Trends' tab for detailed parameters, and consult your doctor for personalized advice."

