"""
ingestion.py — Main ingestion pipeline entry point.

Run this script once to populate your ChromaDB vector store from the Excel data and PDF centre data.

Usage (from the Server/ directory):
    python -m ingestion.ingestion

Or directly:
    python ingestion/ingestion.py
"""

import os
import sys

# Ensure the Server/ directory is in the path so sibling packages resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ingestion.excel_loader import ExcelLoader
from ingestion.pdf_loader import load_pdf_documents
from ingestion.chunker import DocumentChunker
from vectordb.chroma_client import ChromaClient


def run_ingestion(
    excel_path: str = None,
    pdf_path: str = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    batch_size: int = 500,
    collection_name: str = "lord_diagnostics",
):
    """
    Full ingestion pipeline:
      1. Load test rows from Excel as LangChain Documents
      2. Load centre details from PDF as LangChain Documents
      3. Embed and store all documents/chunks in ChromaDB
    """

    print("=" * 60)
    print("  Lord Diagnostics AI — Ingestion Pipeline")
    print("=" * 60)

    # ── Step 1: Load Excel Tests ──────────────────────────────────
    print("\n[Step 1/3] Loading Excel diagnostic test data...")
    loader = ExcelLoader(excel_path=excel_path)
    excel_docs = loader.load_documents()

    # ── Step 2: Load PDF Centre Information ───────────────────────
    print("\n[Step 2/3] Loading PDF pathology centre information...")
    pdf_docs = load_pdf_documents(pdf_path=pdf_path)

    all_docs = excel_docs + pdf_docs
    if not all_docs:
        print("ERROR: No documents were loaded. Check your Excel/PDF files.")
        return

    # ── Step 3: Embed & Ingest ────────────────────────────────────
    print(f"\n[Step 3/3] Embedding and ingesting {len(all_docs)} documents into ChromaDB...")
    print(f"  - {len(excel_docs)} diagnostic tests")
    print(f"  - {len(pdf_docs)} centre locations")

    client = ChromaClient(collection_name=collection_name)
    client.ingest_documents(all_docs, batch_size=batch_size)

    print("\n" + "=" * 60)
    print("  Ingestion complete!")
    print(f"  {len(all_docs)} documents stored in collection '{collection_name}'.")
    print("=" * 60)


if __name__ == "__main__":
    run_ingestion()
