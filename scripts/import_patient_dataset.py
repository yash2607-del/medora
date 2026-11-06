"""
Idempotent Patient Dataset Importer.
Loads the synthetic 100-patient, 300-report dataset into the isolated SQLite database.
Preserves all dates, original names, normalized names, reference ranges, and provenance.
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Add Server directory to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_DIR = os.path.join(PROJECT_ROOT, "Server")
sys.path.insert(0, SERVER_DIR)

from patient.models.database import SessionLocal, init_db
from patient.models.patient_models import Patient, PatientReport, ReportPage, TestResult, TrendObservation
from patient.normalization.normalizer import TestNormalizer
from patient.correlation.longitudinal_analyzer import LongitudinalAnalyzer

def import_dataset(csv_path: str):
    print(f"=== Starting Patient Dataset Import from: {csv_path} ===")
    if not os.path.exists(csv_path):
        print(f"ERROR: Dataset not found: {csv_path}")
        return False

    # Initialize tables
    init_db()
    db = SessionLocal()

    try:
        df = pd.read_csv(csv_path)
        print(f"Loaded {len(df)} rows from CSV.")

        # 1. Upsert Patients
        patients_map = {}
        patient_records = df[[
            "patient_id", "patient_name", "age", "gender", "city", "state", "country", "date_of_birth", "synthetic"
        ]].drop_duplicates(subset=["patient_id"])

        for _, row in patient_records.iterrows():
            pid = str(row["patient_id"]).strip()
            existing = db.query(Patient).filter(Patient.patient_id == pid).first()
            if not existing:
                p = Patient(
                    patient_id=pid,
                    name=str(row["patient_name"]).strip(),
                    age=int(row["age"]) if pd.notna(row["age"]) else None,
                    gender=str(row["gender"]).strip() if pd.notna(row["gender"]) else None,
                    city=str(row["city"]).strip() if pd.notna(row["city"]) else None,
                    state=str(row["state"]).strip() if pd.notna(row["state"]) else None,
                    country=str(row["country"]).strip() if pd.notna(row["country"]) else "India",
                    date_of_birth=str(row["date_of_birth"]).strip() if pd.notna(row["date_of_birth"]) else None,
                    synthetic=bool(row["synthetic"])
                )
                db.add(p)
            else:
                existing.name = str(row["patient_name"]).strip()
                existing.age = int(row["age"]) if pd.notna(row["age"]) else None
                existing.gender = str(row["gender"]).strip() if pd.notna(row["gender"]) else None

        db.commit()
        print(f"Synced {len(patient_records)} patients.")

        # 2. Upsert Reports
        report_records = df[[
            "patient_id", "report_id", "report_sequence", "report_type", "report_category",
            "laboratory", "collection_date", "report_date", "source_type"
        ]].drop_duplicates(subset=["report_id"])

        for _, row in report_records.iterrows():
            rid = str(row["report_id"]).strip()
            pid = str(row["patient_id"]).strip()
            existing = db.query(PatientReport).filter(PatientReport.report_id == rid).first()
            if not existing:
                rep = PatientReport(
                    report_id=rid,
                    patient_id=pid,
                    report_sequence=int(row["report_sequence"]) if pd.notna(row["report_sequence"]) else 1,
                    report_type=str(row["report_type"]).strip() if pd.notna(row["report_type"]) else "Diagnostic Report",
                    report_category=str(row["report_category"]).strip() if pd.notna(row["report_category"]) else "General",
                    laboratory=str(row["laboratory"]).strip() if pd.notna(row["laboratory"]) else "Lords Pathology",
                    collection_date=str(row["collection_date"]).strip() if pd.notna(row["collection_date"]) else None,
                    report_date=str(row["report_date"]).strip() if pd.notna(row["report_date"]) else datetime.utcnow().strftime("%Y-%m-%d"),
                    source_type=str(row["source_type"]).strip() if pd.notna(row["source_type"]) else "dataset_import",
                    processing_status="REPORT_READY",
                    ocr_quality_score=0.98
                )
                db.add(rep)
            else:
                existing.report_category = str(row["report_category"]).strip() if pd.notna(row["report_category"]) else existing.report_category
                existing.report_date = str(row["report_date"]).strip() if pd.notna(row["report_date"]) else existing.report_date

        db.commit()
        print(f"Synced {len(report_records)} reports.")

        # 3. Upsert Test Results & Generate OCR Pages
        test_counts = 0
        grouped_by_report = df.groupby("report_id")

        for rid, rep_group in grouped_by_report:
            pid = str(rep_group.iloc[0]["patient_id"]).strip()
            rep_date = str(rep_group.iloc[0]["report_date"]).strip()
            lab_name = str(rep_group.iloc[0]["laboratory"]).strip()

            ocr_lines = [
                f"{lab_name} - Diagnostic Report",
                f"Report ID: {rid} | Patient ID: {pid} | Date: {rep_date}",
                "-" * 60,
                f"{'TEST NAME':<25} {'RESULT':<12} {'UNIT':<10} {'REFERENCE RANGE'}",
                "-" * 60
            ]

            for idx, row in rep_group.iterrows():
                test_counts += 1
                orig_name = str(row["test_name_original"]).strip()
                val = row["value"]
                unit = str(row["unit"]).strip() if pd.notna(row["unit"]) else ""
                ref_low = float(row["reference_low"]) if pd.notna(row["reference_low"]) else None
                ref_high = float(row["reference_high"]) if pd.notna(row["reference_high"]) else None

                # Process through normalizer
                processed = TestNormalizer.process_test_entry(
                    test_name_original=orig_name,
                    raw_value=val,
                    raw_unit=unit,
                    printed_ref_low=ref_low,
                    printed_ref_high=ref_high,
                    laboratory=lab_name
                )

                res_id = f"{rid}_T{idx}"
                source_line = f"{orig_name:<25} {processed['original_value']:<12} {processed['normalized_unit']:<10} {processed['reference_text']}"
                ocr_lines.append(source_line)

                existing_res = db.query(TestResult).filter(TestResult.result_id == res_id).first()
                if not existing_res:
                    tr = TestResult(
                        result_id=res_id,
                        patient_id=pid,
                        report_id=rid,
                        test_name_original=orig_name,
                        test_name_normalized=processed["test_name_normalized"],
                        original_value=processed["original_value"],
                        original_unit=processed["original_unit"],
                        normalized_value=processed["normalized_value"],
                        normalized_unit=processed["normalized_unit"],
                        reference_low=processed["reference_low"],
                        reference_high=processed["reference_high"],
                        reference_text=processed["reference_text"],
                        status=processed["status"],
                        extraction_confidence=0.98,
                        source_page=1,
                        source_text=source_line
                    )
                    db.add(tr)
                else:
                    existing_res.status = processed["status"]
                    existing_res.normalized_value = processed["normalized_value"]

            # Save OCR text for report
            existing_page = db.query(ReportPage).filter(ReportPage.report_id == rid, ReportPage.page_number == 1).first()
            full_ocr_text = "\n".join(ocr_lines)
            if not existing_page:
                db.add(ReportPage(
                    report_id=rid,
                    page_number=1,
                    ocr_text=full_ocr_text,
                    ocr_confidence=0.98
                ))
            else:
                existing_page.ocr_text = full_ocr_text

        db.commit()
        print(f"Synced {test_counts} test results and report pages.")

        # 4. Precompute Trend Observations per Patient
        print("Precomputing longitudinal trends per patient...")
        for pid in df["patient_id"].unique():
            pid = str(pid).strip()
            # Fetch all results for this patient
            p_results = (
                db.query(TestResult, PatientReport.report_date)
                .join(PatientReport, TestResult.report_id == PatientReport.report_id)
                .filter(TestResult.patient_id == pid)
                .order_by(PatientReport.report_date.asc())
                .all()
            )

            records_dict_list = [
                {
                    "report_id": tr.report_id,
                    "report_date": rep_date,
                    "test_name_original": tr.test_name_original,
                    "test_name_normalized": tr.test_name_normalized,
                    "normalized_value": tr.normalized_value,
                    "normalized_unit": tr.normalized_unit,
                    "reference_low": tr.reference_low,
                    "reference_high": tr.reference_high,
                    "reference_text": tr.reference_text,
                    "status": tr.status
                }
                for tr, rep_date in p_results
            ]

            trends = LongitudinalAnalyzer.compute_all_patient_trends(pid, records_dict_list)

            # Clear existing trends for this patient and re-insert
            db.query(TrendObservation).filter(TrendObservation.patient_id == pid).delete()
            for t in trends:
                db.add(TrendObservation(
                    patient_id=pid,
                    test_name=t["test_name"],
                    first_value=t["earliest_value"],
                    latest_value=t["latest_value"],
                    absolute_change=t["absolute_change"],
                    percentage_change=t["percentage_change"],
                    previous_status=t["previous_status"],
                    current_status=t["current_status"],
                    trend=t["trend"],
                    persistence=t["persistence"],
                    evidence=t["deterministic_statement"]
                ))

        db.commit()
        print("Precomputed all patient longitudinal trends successfully.")

        print("\n=== Dataset Import Completed Successfully! ===")
        return True

    except Exception as e:
        db.rollback()
        print(f"ERROR during import: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_csv = os.path.join(base_dir, "patient_report_dataset_300.csv")
    if not os.path.exists(target_csv):
        target_csv = os.path.join(base_dir, "Healthcare-RAG-Assistant", "patient_report_dataset_300.csv")
    success = import_dataset(target_csv)
    sys.exit(0 if success else 1)

