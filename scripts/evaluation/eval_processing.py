"""
Module A Evaluation: Medical Report Processing & Clinical Normalization Benchmark
Measures actual extraction accuracy, test normalization, status classification confusion matrix,
and PDF processing throughput/quality scoring on actual ground truth and sample PDFs.
"""

import os
import sys
import time
import json
import numpy as np
import pandas as pd

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVER_DIR = os.path.join(BASE_DIR, "Server")
sys.path.insert(0, SERVER_DIR)

from patient.normalization.normalizer import TestNormalizer
from patient.ocr.pdf_processor import PDFProcessor
from patient.ocr.ocr_service import BaseOCRService

def run_evaluation():
    print("=" * 70)
    print("Running Module A Evaluation: Medical Report Processing & Normalization")
    print("=" * 70)

    results = {}

    # 1. Dataset Evaluation: 1800 records from patient_report_dataset_300.csv
    csv_path = os.path.join(SERVER_DIR, "data", "csv", "patient_report_dataset_300.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at {csv_path}")

    df = pd.read_csv(csv_path)
    total_records = len(df)
    print(f"Loaded {total_records} ground truth test records.")

    # Tracking metrics
    name_norm_correct = 0
    status_correct = 0
    unit_norm_correct = 0
    value_parsed_correct = 0

    # Confusion matrix for statuses: NORMAL, LOW, HIGH
    classes = ["NORMAL", "LOW", "HIGH"]
    conf_matrix = {c_true: {c_pred: 0 for c_pred in classes} for c_true in classes}

    per_test_accuracy = {}

    for _, row in df.iterrows():
        orig_name = str(row["test_name_original"])
        gt_norm_name = str(row["test_name_normalized"]).strip().lower()
        orig_val = row["value"]
        orig_unit = str(row["unit"]) if pd.notna(row["unit"]) else None
        ref_low = float(row["reference_low"]) if pd.notna(row["reference_low"]) else None
        ref_high = float(row["reference_high"]) if pd.notna(row["reference_high"]) else None
        gt_status = str(row["status"]).strip().upper()

        # Run production normalization pipeline
        processed = TestNormalizer.process_test_entry(
            test_name_original=orig_name,
            raw_value=orig_val,
            raw_unit=orig_unit,
            printed_ref_low=ref_low,
            printed_ref_high=ref_high,
            laboratory=str(row.get("laboratory", "Lords Pathology"))
        )

        pred_norm_name = processed["test_name_normalized"].strip().lower()
        pred_status = processed["status"].strip().upper()
        pred_val = processed["normalized_value"]
        pred_unit = processed["normalized_unit"]

        # Check Name Normalization
        if pred_norm_name == gt_norm_name:
            name_norm_correct += 1
            per_test_accuracy[gt_norm_name] = per_test_accuracy.get(gt_norm_name, [0, 0])
            per_test_accuracy[gt_norm_name][0] += 1
            per_test_accuracy[gt_norm_name][1] += 1
        else:
            per_test_accuracy[gt_norm_name] = per_test_accuracy.get(gt_norm_name, [0, 0])
            per_test_accuracy[gt_norm_name][1] += 1

        # Check Value Parsing
        if pred_val is not None and abs(pred_val - float(orig_val)) < 1e-4:
            value_parsed_correct += 1

        # Check Unit Normalization
        if orig_unit and pred_unit:
            unit_norm_correct += 1

        # Check Status Classification
        if pred_status in classes and gt_status in classes:
            conf_matrix[gt_status][pred_status] += 1
            if pred_status == gt_status:
                status_correct += 1

    # Calculate overall metrics
    name_norm_acc = name_norm_correct / total_records
    val_parse_acc = value_parsed_correct / total_records
    status_acc = status_correct / total_records

    # Precision, Recall, F1 for each class
    class_metrics = {}
    for c in classes:
        tp = conf_matrix[c][c]
        fp = sum(conf_matrix[other][c] for other in classes if other != c)
        fn = sum(conf_matrix[c][other] for other in classes if other != c)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        class_metrics[c] = {
            "TP": tp, "FP": fp, "FN": fn,
            "support": tp + fn,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4)
        }

    macro_f1 = np.mean([class_metrics[c]["f1"] for c in classes])
    macro_prec = np.mean([class_metrics[c]["precision"] for c in classes])
    macro_rec = np.mean([class_metrics[c]["recall"] for c in classes])

    results["dataset_evaluation"] = {
        "total_evaluated_records": total_records,
        "name_normalization_accuracy": round(name_norm_acc, 4),
        "value_parsing_accuracy": round(val_parse_acc, 4),
        "status_classification_accuracy": round(status_acc, 4),
        "macro_precision": round(float(macro_prec), 4),
        "macro_recall": round(float(macro_rec), 4),
        "macro_f1": round(float(macro_f1), 4),
        "confusion_matrix": conf_matrix,
        "class_metrics": class_metrics
    }

    print(f"Name Normalization Accuracy: {name_norm_acc*100:.2f}%")
    print(f"Status Classification Accuracy: {status_acc*100:.2f}% (Macro-F1: {macro_f1:.4f})")

    # 2. PDF Processing & OCR Throughput Benchmark on real sample PDFs
    pdf_samples = [
        {
            "name": "Synthetic Lab Report (1 Page)",
            "path": os.path.join(SERVER_DIR, "data", "patient", "uploads", "PAT0001", "1d8ef864063b4929bbaf6850f64f8e75.pdf")
        },
        {
            "name": "Clinical Diagnostic Report (28 Pages)",
            "path": os.path.join(SERVER_DIR, "data", "patient", "uploads", "PAT0103", "23289462a4434e9da1012dd1f70b1671.pdf")
        },
        {
            "name": "Diagnostic Centre Directory (64 Pages)",
            "path": os.path.join(SERVER_DIR, "data", "pdf", "Lord's Pathology Centre Information Final.pdf")
        }
    ]

    pdf_processor = PDFProcessor()
    pdf_benchmarks = []

    for sample in pdf_samples:
        p = sample["path"]
        if not os.path.exists(p):
            print(f"Skipping {sample['name']} (not found)")
            continue

        file_size_kb = round(os.path.getsize(p) / 1024, 2)
        start_t = time.perf_counter()
        pages = pdf_processor.extract_text(p)
        elapsed_sec = time.perf_counter() - start_t

        num_pages = len(pages)
        total_chars = sum(len(pg["text"]) for pg in pages)
        avg_chars_per_page = round(total_chars / max(num_pages, 1), 1)
        ms_per_page = round((elapsed_sec / max(num_pages, 1)) * 1000, 2)

        quality_report = BaseOCRService.calculate_quality(pages)

        bench_item = {
            "document_name": sample["name"],
            "file_size_kb": file_size_kb,
            "page_count": num_pages,
            "total_extracted_characters": total_chars,
            "avg_chars_per_page": avg_chars_per_page,
            "total_processing_time_sec": round(elapsed_sec, 4),
            "throughput_ms_per_page": ms_per_page,
            "ocr_quality_score": quality_report["score"],
            "is_low_quality": quality_report["is_low_quality"]
        }
        pdf_benchmarks.append(bench_item)
        print(f"  Processed {sample['name']}: {num_pages} pages in {elapsed_sec:.2f}s ({ms_per_page} ms/page), Quality={quality_report['score']}")

    results["pdf_processing_benchmarks"] = pdf_benchmarks

    # Save output
    out_file = os.path.join(os.path.dirname(__file__), "results_processing.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved Module A benchmark results to {out_file}")
    return results

if __name__ == "__main__":
    run_evaluation()
