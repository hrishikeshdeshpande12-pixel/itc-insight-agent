import argparse
import sys
import time
from pathlib import Path
from typing import List, Dict

from app.config import settings
from app.rag.loader import DocumentLoader, PageData, compute_file_checksum
from app.rag.visual_processor import VisualProcessor
from app.rag.chunker import PageAwareChunker, DocumentChunk
from app.rag.embeddings import GeminiEmbedder
from app.rag.vector_store import FaissVectorStore
from app.utils.gcs_sync import sync_documents_to_gcs
from app.utils.logging import get_logger

logger = get_logger("rag.ingest")

def run_ingestion(force: bool = False, skip_gcs: bool = False):
    start_time = time.time()
    logger.info("=== Starting ITC Knowledge Ingestion Pipeline ===")

    loader = DocumentLoader()
    pdf_files = loader.discover_documents()

    if not pdf_files:
        logger.error(f"No PDF files discovered in {settings.DATA_SOURCE_DIR}")
        return False

    # Sync to GCS backup if not skipped
    if not skip_gcs:
        logger.info("Synchronizing source documents with GCS backup bucket...")
        sync_documents_to_gcs(pdf_files)

    # Compute checksums
    checksum_map: Dict[str, str] = {}
    for pdf in pdf_files:
        checksum = compute_file_checksum(pdf)
        checksum_map[pdf.name] = checksum
        logger.info(f"Verified: {pdf.name} (SHA-256: {checksum[:12]}...)")

    vector_store = FaissVectorStore()

    # Idempotency check
    if not force and vector_store.is_idempotent_match(checksum_map):
        logger.info("Index is already up to date with matching document checksums. Ingestion skipped.")
        logger.info("Use --force to rebuild the index if needed.")
        return True

    visual_processor = VisualProcessor()
    chunker = PageAwareChunker()
    all_chunks: List[DocumentChunk] = []

    # Process each PDF document
    for pdf_path in pdf_files:
        logger.info(f"\nProcessing '{pdf_path.name}'...")
        pages_data: List[PageData] = loader.load_document(pdf_path, render_images=True)

        for p_idx, page in enumerate(pages_data, 1):
            visual_analysis = ""
            if visual_processor.should_analyze_visually(page):
                visual_analysis = visual_processor.analyze_page_image(page)

            enriched_text = visual_processor.create_enriched_representation(page, visual_analysis)
            chunks = chunker.chunk_page(page, enriched_text, visual_analysis)
            all_chunks.extend(chunks)

            if p_idx % 50 == 0 or p_idx == len(pages_data):
                logger.info(f"[{pdf_path.name}] Processed {p_idx}/{len(pages_data)} pages, accumulated {len(all_chunks)} chunks total")

    logger.info(f"\nExtraction complete. Total chunks generated across all documents: {len(all_chunks)}")

    # Extract texts for embedding
    texts_to_embed = [c.chunk_text for c in all_chunks]

    logger.info(f"Generating embeddings using {settings.EMBEDDING_MODEL} (dim={settings.EMBEDDING_DIMENSION})...")
    embedder = GeminiEmbedder()
    embeddings = embedder.embed_documents(texts_to_embed)

    logger.info(f"Generated {len(embeddings)} embeddings. Building FAISS vector store...")
    vector_store.build_index(
        chunks=all_chunks,
        embeddings=embeddings,
        source_doc_checksums=checksum_map
    )

    elapsed = time.time() - start_time
    logger.info(f"=== ITC Ingestion Pipeline Finished Successfully in {elapsed:.1f}s ===")
    logger.info(f"Total chunks indexed: {len(all_chunks)}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ITC Knowledge Ingestion Pipeline")
    parser.add_argument("--force", action="store_true", help="Force re-indexing even if checksums match")
    parser.add_argument("--skip-gcs", action="store_true", help="Skip synchronizing documents to GCS")
    args = parser.parse_args()

    success = run_ingestion(force=args.force, skip_gcs=args.skip_gcs)
    sys.exit(0 if success else 1)

