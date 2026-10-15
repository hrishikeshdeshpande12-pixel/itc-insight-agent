"""
Helper script to inspect document chunks and vector embeddings in Google Cloud Firestore.
Usage:
    python backend/app/scripts/inspect_firestore_embeddings.py
    python backend/app/scripts/inspect_firestore_embeddings.py --limit 3
    python backend/app/scripts/inspect_firestore_embeddings.py --chunk-id "ITC-R-and-A-2026-Theme-feature.pdf_p10_c0"
"""

import sys
import argparse
from pathlib import Path

# Set UTF-8 encoding for stdout on Windows console if needed
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.firestore_knowledge_service import FirestoreKnowledgeService
from app.config import settings

def main():
    parser = argparse.ArgumentParser(description="Inspect chunks and embeddings in Firestore 'itc_knowledge'.")
    parser.add_argument("--limit", type=int, default=1, help="Number of chunks to display (default: 1)")
    parser.add_argument("--chunk-id", type=str, default=None, help="Inspect a specific chunk by its ID")
    parser.add_argument("--dims", type=int, default=10, help="Number of vector dimensions to display (default: 10)")
    args = parser.parse_args()

    print(f"\n[+] Connecting to Google Cloud Firestore (Project: {settings.GOOGLE_CLOUD_PROJECT})...")
    service = FirestoreKnowledgeService()

    total_count = service.get_chunk_count()
    print(f"[+] Total document chunks in collection '{settings.FIRESTORE_KNOWLEDGE_COLLECTION}': {total_count:,}\n")

    if args.chunk_id:
        doc_ref = service.db.collection(settings.FIRESTORE_KNOWLEDGE_COLLECTION).document(args.chunk_id)
        doc = doc_ref.get()
        if not doc.exists:
            print(f"[-] Chunk '{args.chunk_id}' not found.")
            return
        docs = [doc]
    else:
        docs = list(service.db.collection(settings.FIRESTORE_KNOWLEDGE_COLLECTION).limit(args.limit).stream())

    for idx, doc in enumerate(docs, 1):
        data = doc.to_dict() or {}
        chunk_id = doc.id
        doc_name = data.get("document_name", "Unknown")
        page_no = data.get("page_number", 0)
        chunk_text = data.get("chunk_text", "")
        enriched_text = data.get("enriched_text", "")
        visual_avail = data.get("visual_context_available", False)
        embedding = data.get("embedding")

        print("=" * 80)
        print(f"Document Chunk #{idx}: {chunk_id}")
        print("=" * 80)
        print(f"  * Source Document:  {doc_name}")
        print(f"  * Page Number:      {page_no}")
        print(f"  * Visual Analyzed:  {visual_avail}")
        print(f"\n  * Text Excerpt (First 250 characters):")
        print(f"    {repr(chunk_text[:250])}...")

        if embedding is not None:
            try:
                raw_values = list(embedding)
            except Exception:
                raw_values = []
            
            print(f"\n  * Vector Embedding (Stored in Firestore):")
            print(f"    - Type:             {type(embedding).__name__}")
            print(f"    - Total Dimensions: {len(raw_values)} (gemini-embedding-001)")
            print(f"    - First {args.dims} dimensions:")
            formatted_dims = ", ".join(f"{v:.6f}" for v in raw_values[:args.dims])
            print(f"      [{formatted_dims}, ...]")
        else:
            print(f"\n  [!] No embedding field found in this document.")
        print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
