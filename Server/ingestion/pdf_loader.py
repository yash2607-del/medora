import os
import sys
from typing import List

# Ensure the Server directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
import re
from vectordb.chroma_client import ChromaClient


def load_pdf_documents(pdf_path: str = None) -> List[Document]:
    if pdf_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pdf_dir = os.path.join(base_dir, 'data', 'pdf')
        default_file = os.path.join(pdf_dir, "Lord's Pathology Centre Information Final.pdf")
        if os.path.exists(default_file):
            pdf_path = default_file
        else:
            files = [os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir) if f.endswith(".pdf")] if os.path.exists(pdf_dir) else []
            pdf_path = files[0] if files else default_file

    if not os.path.exists(pdf_path):
        print(f"PDF file not found locally at {pdf_path}. Attempting download from Supabase Storage...")
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        try:
            from patient.storage.supabase_storage import SupabaseStorage
            storage = SupabaseStorage()
            content = storage.download_file("rag/Lords_Pathology_Centre_Information.pdf")
            if content:
                with open(pdf_path, "wb") as f:
                    f.write(content)
                print(f"Successfully downloaded PDF file from Supabase Storage to {pdf_path}")
        except Exception as e:
            print(f"Could not download PDF from Supabase Storage: {e}")

    if not os.path.exists(pdf_path):
        print(f"Warning: PDF file not found at: {pdf_path}")
        return []

    print(f"Loading PDF file: {pdf_path}")
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    full_text = "\n".join([doc.page_content for doc in docs])

    clean_text = re.sub(r'\s+', ' ', full_text)
    centre_splits = re.split(r'(Centre ID:)', clean_text, flags=re.IGNORECASE)

    chunks = []
    for i in range(1, len(centre_splits), 2):
        if i + 1 < len(centre_splits):
            split_text = centre_splits[i] + centre_splits[i+1]
        else:
            split_text = centre_splits[i]

        split_text = split_text.strip()

        # Extract state
        state = "Unknown"
        state_match = re.search(r'State:\s*(.*?)\s*(?:City:|Service Type:|Trust Indicator:)', split_text, re.IGNORECASE)
        if state_match:
            state = state_match.group(1).strip()

        # Extract centre name
        centre_name = "Unknown Centre"
        centre_match = re.search(r'Centre Name:\s*(.*?)\s*State:', split_text, re.IGNORECASE)
        if centre_match:
            centre_name = centre_match.group(1).strip()

        doc = Document(
            page_content=split_text,
            metadata={
                "source": "centre_info",
                "state": state,
                "centre": centre_name
            }
        )
        chunks.append(doc)

    print(f"Chunked PDF into {len(chunks)} distinct centres.")
    return chunks


def ingest_pdf():
    chunks = load_pdf_documents()
    if chunks:
        print("Adding chunks to Vector DB...")
        chroma_client = ChromaClient()
        chroma_client.ingest_documents(chunks)
        print("Successfully ingested PDF with Custom Heading Chunking!")


if __name__ == "__main__":
    ingest_pdf()
