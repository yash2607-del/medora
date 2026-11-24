"""
Module C Evaluation: Patient Intelligence Layer Benchmark
Evaluates longitudinal biomarker trend calculation accuracy, mathematical consistency,
directional movement validity, and 100% evidence provenance traceability across the patient database.
"""

import os
import sys
import json
import sqlite3
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVER_DIR = os.path.join(BASE_DIR, "Server")
sys.path.insert(0, SERVER_DIR)

from patient.correlation.longitudinal_analyzer import LongitudinalAnalyzer

def run_evaluation():
    print("=" * 70)
    print("Running Module C Evaluation: Patient Intelligence Layer")
    print("=" * 70)

    db_path = os.path.join(SERVER_DIR, "data", "patient", "patient_records.db")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    results = {}

    # 1. Longitudinal Trend Observations Evaluation
    # Pull all trend observations from the database
    trend_df = pd.read_sql_query("SELECT * FROM trend_observations", conn)
    total_trends = len(trend_df)
    print(f"Loaded {total_trends} longitudinal trend observations from SQLite.")

    # Mathematical consistency checks
    math_delta_errors = 0
    math_pct_errors = 0
    trend_direction_counts = {}
    persistence_counts = {}

    for _, row in trend_df.iterrows():
        first_val = row["first_value"]
        latest_val = row["latest_value"]
        db_abs = row["absolute_change"]
        db_pct = row["percentage_change"]
        direction = row["trend"]
        persistence = row["persistence"]

        trend_direction_counts[direction] = trend_direction_counts.get(direction, 0) + 1
        persistence_counts[persistence] = persistence_counts.get(persistence, 0) + 1

        if first_val is not None and latest_val is not None:
            expected_abs = round(latest_val - first_val, 2)
            if db_abs is not None and abs(db_abs - expected_abs) > 0.05:
                math_delta_errors += 1

            if first_val != 0:
                expected_pct = round(((latest_val - first_val) / abs(first_val)) * 100.0, 1)
                if db_pct is not None and abs(db_pct - expected_pct) > 0.5:
                    math_pct_errors += 1

    delta_accuracy = 1.0 - (math_delta_errors / max(total_trends, 1))
    pct_accuracy = 1.0 - (math_pct_errors / max(total_trends, 1))

    # Evaluate dynamic execution of LongitudinalAnalyzer._is_favorable_direction
    # Test suite covering all 6 clinical direction conditions
    direction_test_cases = [
        # (test_name, prev_val, curr_val, prev_status, curr_status, ref_low, ref_high, expected)
        ("TSH", 8.5, 3.2, "HIGH", "NORMAL", 0.4, 4.5, "improving"), # High -> Normal
        ("TSH", 3.2, 7.8, "NORMAL", "HIGH", 0.4, 4.5, "worsening"), # Normal -> High
        ("TSH", 2.5, 2.7, "NORMAL", "NORMAL", 0.4, 4.5, "stable"),   # Normal -> Normal
        ("TSH", 9.0, 6.5, "HIGH", "HIGH", 0.4, 4.5, "improving"),   # Both High, decreasing towards normal
        ("TSH", 6.5, 9.2, "HIGH", "HIGH", 0.4, 4.5, "worsening"),   # Both High, increasing away from normal
        ("Hemoglobin", 9.0, 11.5, "LOW", "LOW", 12.0, 15.0, "improving"), # Both Low, increasing towards normal
        ("Hemoglobin", 11.0, 9.5, "LOW", "LOW", 12.0, 15.0, "worsening"), # Both Low, decreasing away from normal
    ]

    dir_passes = 0
    for tc in direction_test_cases:
        actual_dir = LongitudinalAnalyzer._is_favorable_direction(
            test_name=tc[0],
            prev_val=tc[1],
            curr_val=tc[2],
            prev_status=tc[3],
            curr_status=tc[4],
            ref_low=tc[5],
            ref_high=tc[6]
        )
        if actual_dir == tc[7]:
            dir_passes += 1

    dir_logic_acc = dir_passes / len(direction_test_cases)

    results["longitudinal_evaluation"] = {
        "total_trends_evaluated": total_trends,
        "delta_math_accuracy": round(delta_accuracy, 4),
        "percentage_change_math_accuracy": round(pct_accuracy, 4),
        "directional_logic_test_accuracy": round(dir_logic_acc, 4),
        "trend_direction_distribution": trend_direction_counts,
        "persistence_distribution": persistence_counts
    }

    # 2. Evidence Traceability & Provenance Verification
    test_results_df = pd.read_sql_query("SELECT * FROM test_results", conn)
    total_test_results = len(test_results_df)

    has_source_page = test_results_df["source_page"].notna().sum()
    has_source_text = test_results_df["source_text"].notna().sum()
    has_report_id = test_results_df["report_id"].notna().sum()
    has_patient_id = test_results_df["patient_id"].notna().sum()

    traceability_rate = (
        (has_source_page + has_source_text + has_report_id + has_patient_id) / (4.0 * max(total_test_results, 1))
    )

    results["provenance_audit"] = {
        "total_test_results": total_test_results,
        "records_with_patient_id": int(has_patient_id),
        "records_with_report_id": int(has_report_id),
        "records_with_source_page": int(has_source_page),
        "records_with_source_text": int(has_source_text),
        "overall_traceability_rate": round(float(traceability_rate), 4)
    }

    conn.close()

    print(f"Longitudinal Math Delta Accuracy: {delta_accuracy*100:.2f}%")
    print(f"Overall Evidence Traceability Rate: {traceability_rate*100:.2f}%")

    out_file = os.path.join(os.path.dirname(__file__), "results_patient_intel.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Saved Module C results to {out_file}")
    return results

if __name__ == "__main__":
    run_evaluation()
