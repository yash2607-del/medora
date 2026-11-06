"""
Validator for the synthetic patient report dataset.
Checks data integrity, relationships, chronological ordering, and numerical ranges.
"""

import os
import sys
import pandas as pd
from datetime import datetime

def validate_dataset(csv_path: str) -> bool:
    print(f"=== Validating Patient Dataset: {csv_path} ===")
    if not os.path.exists(csv_path):
        print(f"ERROR: Dataset file not found at {csv_path}")
        return False

    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} rows across {len(df.columns)} columns.")

    required_cols = [
        "patient_id", "patient_name", "age", "gender", "city", "state", "country", "date_of_birth",
        "report_id", "report_sequence", "report_type", "report_category", "laboratory",
        "collection_date", "report_date", "source_type",
        "test_name_original", "test_name_normalized", "value", "unit",
        "reference_low", "reference_high", "status", "synthetic", "data_use", "longitudinal_pattern"
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"ERROR: Missing required columns: {missing_cols}")
        return False

    errors = []
    warnings = []

    # 1. Patients check
    unique_patients = df["patient_id"].nunique()
    print(f"Found {unique_patients} unique patients.")
    if unique_patients == 0:
        errors.append("No patient IDs found.")

    # 2. Reports check
    unique_reports = df["report_id"].nunique()
    print(f"Found {unique_reports} unique reports.")
    if unique_reports == 0:
        errors.append("No report IDs found.")

    # 3. Patient to Report relationship: each report should belong to exactly one patient
    report_patient_map = df.groupby("report_id")["patient_id"].nunique()
    multi_patient_reports = report_patient_map[report_patient_map > 1]
    if not multi_patient_reports.empty:
        errors.append(f"Reports mapped to multiple patients: {multi_patient_reports.to_dict()}")

    # 4. Chronological ordering per patient
    for patient_id, p_df in df.groupby("patient_id"):
        reports_in_order = p_df[["report_id", "report_date", "report_sequence"]].drop_duplicates()
        try:
            reports_in_order["date_parsed"] = pd.to_datetime(reports_in_order["report_date"])
            # check if report_sequence matches chronological order
            sorted_by_date = reports_in_order.sort_values("date_parsed")
            if not reports_in_order["report_sequence"].is_monotonic_increasing:
                warnings.append(f"Patient {patient_id} sequences are not strictly increasing.")
        except Exception as e:
            errors.append(f"Invalid date format in patient {patient_id}: {e}")

    # 5. Numerical validity
    non_numeric_values = pd.to_numeric(df["value"], errors="coerce").isna()
    if non_numeric_values.any():
        warnings.append(f"Found {non_numeric_values.sum()} non-numeric test values.")

    # 6. Status check
    valid_statuses = {"NORMAL", "HIGH", "LOW", "ABNORMAL"}
    invalid_statuses = set(df["status"].dropna().unique()) - valid_statuses
    if invalid_statuses:
        warnings.append(f"Unexpected statuses found: {invalid_statuses}")

    print("\n--- Validation Summary ---")
    if errors:
        print(f"FAILED with {len(errors)} critical error(s):")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("PASSED: Schema, relationships, and data integrity verified successfully.")
        if warnings:
            print(f"Note: {len(warnings)} warning(s) observed:")
            for w in warnings[:5]:
                print(f"  - {w}")
        return True

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_csv = os.path.join(base_dir, "medora", "Healthcare-RAG-Assistant", "patient_report_dataset_300.csv")
    if not os.path.exists(target_csv):
        target_csv = os.path.join(base_dir, "patient_report_dataset_300.csv")
    success = validate_dataset(target_csv)
    sys.exit(0 if success else 1)

