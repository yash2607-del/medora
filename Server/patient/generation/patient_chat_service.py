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
        assembles structured evidence across single or multiple reports,
        and generates grounded answer.
        """
        q_lower = query.lower()
        report_meta = report_meta or {}
        scope = report_meta.get("scope", "all_reports" if not report_meta.get("report_id") else "single_report")
        available_reports = report_meta.get("available_reports", [])

        # Deterministic filtering of relevant evidence
        relevant_results = []
        relevant_trends = []

        # Check if query mentions a specific date or report ID from available reports
        mentioned_report_ids = set()
        for r in available_reports:
            r_d = (r.get("report_date") or "").lower()
            r_i = (r.get("report_id") or "").lower()
            if (r_d and r_d in q_lower) or (r_i and r_i in q_lower):
                mentioned_report_ids.add(r.get("report_id"))

        # Check for specific test inquiries
        for res in recent_results:
            t_orig = (res.get("test_name_original") or "").lower()
            t_norm = (res.get("test_name_normalized") or "").lower()
            test_matched = (
                t_norm in q_lower
                or t_orig in q_lower
                or any(word in q_lower for word in t_norm.split() if len(word) > 2)
            )

            # If user asked about a specific report date, prioritize matching that report
            if mentioned_report_ids:
                if res.get("report_id") in mentioned_report_ids:
                    if test_matched or not any(word in q_lower for word in ["cholesterol", "glucose", "hemoglobin", "wbc", "creatinine", "platelet", "hba1c", "ldl", "hdl"]):
                        relevant_results.append(res)
            elif test_matched:
                relevant_results.append(res)

        for trend in patient_trends:
            t_name = (trend.get("test_name") or "").lower()
            if t_name in q_lower or any(word in q_lower for word in t_name.split() if len(word) > 2):
                relevant_trends.append(trend)

        # If general question about abnormal or changes, include abnormal & changing tests
        if any(w in q_lower for w in ["abnormal", "high", "low", "out of range"]):
            abnormals = [r for r in recent_results if r.get("status") in ["HIGH", "LOW"]]
            relevant_results = abnormals if abnormals else relevant_results
        elif any(w in q_lower for w in ["change", "trend", "improve", "worse", "better", "previous", "difference", "earlier", "compare", "history"]):
            relevant_trends = [t for t in patient_trends if t.get("readings_count", 1) > 1]
        elif not relevant_results and not relevant_trends:
            # Fallback to abnormal results or top test results and key trends
            abnormals = [r for r in recent_results if r.get("status") in ["HIGH", "LOW"]]
            relevant_results = abnormals[:10] if abnormals else recent_results[:12]
            relevant_trends = patient_trends[:6]

        # Assemble Evidence Payload with full report metadata
        evidence_items = []
        for r in relevant_results:
            evidence_items.append({
                "test_name": r.get("test_name_normalized"),
                "current_value": r.get("normalized_value"),
                "unit": r.get("normalized_unit"),
                "reference_range": r.get("reference_text"),
                "status": r.get("status"),
                "report_id": r.get("report_id"),
                "report_date": r.get("report_date"),
                "laboratory": r.get("laboratory"),
                "source_page": r.get("source_page", 1),
                "source_text": r.get("source_text")
            })

        evidence_context = {
            "patient_name": patient_profile.get("name"),
            "patient_id": patient_profile.get("patient_id"),
            "conversation_scope": scope,
            "selected_report_id": report_meta.get("report_id"),
            "active_report_date": report_meta.get("report_date") if report_meta else "All Reports",
            "available_reports": available_reports,
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
                    f"Instructions: Respond to the patient following your system instructions. "
                    f"If the question is conversational (e.g. greeting or thanks), reply warmly and conversationally. "
                    f"If the question asks for general medical/health education, explain clearly and objectively while referencing their personal results where appropriate. "
                    f"If the question is about specific tests, ground your answer strictly in the evidence provided."
                )

                resp = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": PATIENT_CHAT_SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg}
                    ],
                    temperature=0.3,
                    max_tokens=650
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
        q_lower = query.lower().strip()
        tests = context.get("relevant_tests", [])
        trends = context.get("longitudinal_trends", [])
        scope = context.get("conversation_scope", "all_reports")
        report_date = context.get("active_report_date", "All Reports")
        avail_reports = context.get("available_reports", [])
        patient_name = context.get("patient_name") or "there"

        # 1. Greetings & Pleasantries
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "howdy", "greetings"]
        if any(q_lower == g or q_lower.startswith(f"{g} ") or q_lower.endswith(f" {g}") for g in greetings):
            rep_count = len(avail_reports)
            scope_desc = "all your historical reports" if scope == "all_reports" else f"your report from {report_date}"
            return (
                f"Hello {patient_name}! I am your personal clinical report assistant.\n\n"
                f"I currently have access to {rep_count} diagnostic report{'s' if rep_count != 1 else ''} on file, "
                f"and we are currently focused on **{scope_desc}**.\n\n"
                f"You can ask me questions about specific test parameters, compare results across dates, check abnormal findings, "
                f"or ask what different lab tests mean. How can I help you today?"
            )

        # 2. Gratitude / Appreciation
        if any(w in q_lower for w in ["thank you", "thanks", "appreciate", "great help"]):
            return (
                "You're very welcome! If you have any further questions about your test results or reports, "
                "feel free to ask anytime. Always remember to discuss your health with your physician."
            )

        # 3. Identity / Capabilities
        if any(w in q_lower for w in ["who are you", "what can you do", "help", "what do you do"]):
            return (
                "I am your personal laboratory report assistant at Lord's Pathology. Here is how I can assist you:\n"
                "- **Explain Test Results:** Understand numbers, units, and standard reference intervals for tests like Hemoglobin, Cholesterol, Glucose, and more.\n"
                "- **Track Longitudinal Trends:** Review whether a parameter has improved, worsened, or remained stable across your reports.\n"
                "- **Identify Abnormal Values:** Quickly highlight parameters that fell outside standard reference limits.\n"
                "- **General Lab Education:** Learn why tests are ordered and what they measure in the body.\n\n"
                "You can also use the **Report Focus** selector at the top of the chat to switch between individual reports or review your entire history."
            )

        # 4. Report List Inquiries
        if any(w in q_lower for w in ["which report", "what report", "how many report", "list report"]):
            if avail_reports:
                items = [
                    f"- **{r.get('report_date', 'Unknown Date')}** ({r.get('laboratory', 'Diagnostic Lab')}, ID: `{r.get('report_id')}`)"
                    for r in avail_reports
                ]
                return (
                    f"You have {len(avail_reports)} reports on file:\n"
                    + "\n".join(items)
                    + "\n\nYou can ask about any specific report, compare them, or select one from the scope dropdown above."
                )
            return "No laboratory reports are currently on file."

        # 5. Abnormal parameter inquiries
        if any(w in q_lower for w in ["abnormal", "high", "low", "out of range"]):
            abnormals = [t for t in tests if t.get("status") in ["HIGH", "LOW"]]
            if abnormals:
                items = [
                    f"- **{t['test_name']}** ({t.get('report_date') or 'Report'}): {t['current_value']} {t.get('unit') or ''} ({t['status']})"
                    for t in abnormals
                ]
                scope_prefix = (
                    f"In your report dated **{report_date}**"
                    if scope == "single_report" and report_date
                    else "Across your laboratory reports"
                )
                return f"{scope_prefix}, the following parameters were outside standard reference intervals:\n" + "\n".join(items)
            return f"All reviewed parameters in {'this report' if scope == 'single_report' else 'your records'} are within standard reference ranges."

        # 6. Trends and changes inquiries
        if any(w in q_lower for w in ["change", "trend", "improve", "worsen", "compare", "difference"]):
            if trends:
                items = [f"- {t['statement']}" for t in trends[:5]]
                return "Here are the observed changes across your reports:\n" + "\n".join(items)
            return "No previous reports were found to compare changes against."

        # 7. Specific matching tests
        if tests:
            items = [
                f"- **{t['test_name']}** ({t.get('report_date') or 'Report'}): {t['current_value']} {t.get('unit') or ''} ({t['status']})"
                for t in tests[:8]
            ]
            return f"Here are the test results related to your question:\n" + "\n".join(items)

        # 8. General Health / Educational Explanations (when test result not in records)
        educational_glossary = {
            "ldl": "LDL (Low-Density Lipoprotein) is commonly known as 'bad cholesterol' because high levels can cause plaque buildup in arterial walls. Standard target ranges are typically below 100 mg/dL.",
            "hdl": "HDL (High-Density Lipoprotein) is 'good cholesterol' that carries excess cholesterol from arterial tissues back to the liver for clearance. Target levels are generally above 40–50 mg/dL.",
            "cholesterol": "Cholesterol is a lipid substance essential for building cells and hormone synthesis. A full lipid panel includes Total Cholesterol, LDL, HDL, and Triglycerides.",
            "hemoglobin": "Hemoglobin is an iron-containing protein in red blood cells that transports oxygen from the lungs to bodily tissues. Lower values may indicate anemia.",
            "glucose": "Blood glucose reflects the concentration of sugar circulating in the blood. Fasting glucose tests help monitor metabolic function and insulin response.",
            "creatinine": "Creatinine is a byproduct of muscle breakdown that healthy kidneys filter out. It is a key indicator of kidney filtration efficiency (eGFR).",
            "platelet": "Platelets (thrombocytes) are vital cellular fragments responsible for clotting blood to prevent excessive bleeding during vascular injuries.",
            "crp": "C-Reactive Protein (CRP) is a sensitive biomarker synthesized by the liver in response to bodily inflammation or tissue stress.",
        }

        for keyword, explanation in educational_glossary.items():
            if keyword in q_lower:
                return (
                    f"**General Health Context:**\n{explanation}\n\n"
                    f"I did not find a recent reading for this exact test in your currently focused reports, "
                    f"or it may be named slightly differently. Please check your uploaded reports or consult your physician."
                )

        # 9. General helpful fallback
        return (
            "I couldn't locate specific test data in your uploaded records for this query. "
            "You can ask about your personal lab values (e.g., Hemoglobin, Glucose, Cholesterol), "
            "ask which reports are on file, or select a different report from the **Report Focus** dropdown above. "
            "For medical diagnosis or personal health advice, please consult your doctor."
        )

