"""
Longitudinal Trend and Historical Comparison Engine.
Calculates all mathematical deltas, percentage changes, status shifts,
and directional patterns deterministically in Python. Zero LLM math.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

class LongitudinalAnalyzer:
    @staticmethod
    def _is_favorable_direction(
        test_name: str,
        prev_val: float,
        curr_val: float,
        prev_status: str,
        curr_status: str,
        ref_low: Optional[float],
        ref_high: Optional[float]
    ) -> str:
        """
        Determines if movement between two readings is 'improving', 'worsening', or 'stable'.
        """
        # If status moved from abnormal to normal -> improving
        if prev_status in ["HIGH", "LOW"] and curr_status == "NORMAL":
            return "improving"
        
        # If status moved from normal to abnormal -> worsening
        if prev_status == "NORMAL" and curr_status in ["HIGH", "LOW"]:
            return "worsening"

        # If both are normal
        if prev_status == "NORMAL" and curr_status == "NORMAL":
            return "stable"

        # If both are HIGH:
        # A decrease is improving (moving closer to normal range), an increase is worsening
        if prev_status == "HIGH" and curr_status == "HIGH":
            if curr_val < prev_val:
                return "improving"
            elif curr_val > prev_val:
                return "worsening"
            return "stable"

        # If both are LOW:
        # An increase is improving (moving closer to normal range), a decrease is worsening
        if prev_status == "LOW" and curr_status == "LOW":
            if curr_val > prev_val:
                return "improving"
            elif curr_val < prev_val:
                return "worsening"
            return "stable"

        return "fluctuating"

    @classmethod
    def analyze_test_series(
        cls,
        test_name: str,
        historical_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Takes chronologically sorted historical records for a single normalized test:
        [ {report_id, report_date, value, unit, status, ref_low, ref_high, source_page, source_text}, ... ]
        Calculates all longitudinal metrics deterministically.
        """
        if not historical_records:
            return {}

        # Ensure sorted by date
        sorted_records = sorted(
            historical_records,
            key=lambda x: str(x.get("report_date", ""))
        )

        earliest = sorted_records[0]
        latest = sorted_records[-1]
        previous = sorted_records[-2] if len(sorted_records) >= 2 else None

        earliest_val = earliest.get("normalized_value")
        latest_val = latest.get("normalized_value")
        prev_val = previous.get("normalized_value") if previous else None

        prev_status = previous.get("status") if previous else None
        curr_status = latest.get("status", "NORMAL")

        abs_change = None
        pct_change = None
        trend = "stable"
        persistence = "stable_normal"

        if prev_val is not None and latest_val is not None:
            abs_change = round(latest_val - prev_val, 2)
            if prev_val != 0:
                pct_change = round(((latest_val - prev_val) / abs(prev_val)) * 100.0, 1)
            else:
                pct_change = 0.0

            trend = cls._is_favorable_direction(
                test_name=test_name,
                prev_val=prev_val,
                curr_val=latest_val,
                prev_status=prev_status or "NORMAL",
                curr_status=curr_status,
                ref_low=latest.get("reference_low"),
                ref_high=latest.get("reference_high")
            )

            # Determine persistence
            if prev_status in ["HIGH", "LOW"] and curr_status in ["HIGH", "LOW"]:
                persistence = "persistently_abnormal"
            elif prev_status == "NORMAL" and curr_status in ["HIGH", "LOW"]:
                persistence = "newly_abnormal"
            elif prev_status in ["HIGH", "LOW"] and curr_status == "NORMAL":
                persistence = "previously_abnormal_now_normal"
            else:
                persistence = "stable_normal"
        else:
            if curr_status in ["HIGH", "LOW"]:
                persistence = "abnormal_single_reading"
            else:
                persistence = "normal_single_reading"

        # Count total abnormal results across all history for this test
        abnormal_count = sum(1 for r in sorted_records if r.get("status") in ["HIGH", "LOW"])

        # Create structured human-readable deterministic observation
        unit = latest.get("normalized_unit") or ""
        if previous and prev_val is not None and latest_val is not None:
            direction_word = "increased" if abs_change > 0 else ("decreased" if abs_change < 0 else "remained steady")
            pct_text = f" ({abs(pct_change)}%)" if pct_change is not None and abs(pct_change) > 0 else ""
            status_summary = f"and is now {curr_status}"
            deterministic_statement = (
                f"{test_name} {direction_word} from {prev_val} {unit} on {previous.get('report_date')} "
                f"to {latest_val} {unit} on {latest.get('report_date')}{pct_text}, {status_summary}."
            )
        else:
            deterministic_statement = f"{test_name} current value is {latest_val} {unit} ({curr_status})."

        return {
            "test_name": test_name,
            "unit": unit,
            "readings_count": len(sorted_records),
            "earliest_value": earliest_val,
            "earliest_date": earliest.get("report_date"),
            "previous_value": prev_val,
            "previous_date": previous.get("report_date") if previous else None,
            "latest_value": latest_val,
            "latest_date": latest.get("report_date"),
            "reference_low": latest.get("reference_low"),
            "reference_high": latest.get("reference_high"),
            "reference_text": latest.get("reference_text"),
            "absolute_change": abs_change,
            "percentage_change": pct_change,
            "previous_status": prev_status,
            "current_status": curr_status,
            "trend": trend,
            "persistence": persistence,
            "abnormal_count": abnormal_count,
            "deterministic_statement": deterministic_statement,
            "history_points": [
                {
                    "report_id": r.get("report_id"),
                    "date": r.get("report_date"),
                    "value": r.get("normalized_value"),
                    "status": r.get("status")
                }
                for r in sorted_records
            ]
        }

    @classmethod
    def compute_all_patient_trends(
        cls,
        patient_id: str,
        all_patient_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Groups test results by normalized test name, orders chronologically,
        and computes longitudinal trend observations for each test.
        """
        # Group by normalized test name
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for res in all_patient_results:
            name = res.get("test_name_normalized") or res.get("test_name_original")
            if name:
                grouped.setdefault(name, []).append(res)

        trends = []
        for test_name, records in grouped.items():
            analysis = cls.analyze_test_series(test_name, records)
            analysis["patient_id"] = patient_id
            trends.append(analysis)

        return trends

