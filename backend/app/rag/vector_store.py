import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import faiss
from app.config import settings
from app.rag.chunker import DocumentChunk
from app.utils.logging import get_logger

logger = get_logger("rag.vector_store")

class FaissVectorStore:
    def __init__(
        self,
        store_dir: Optional[Path] = None,
        dimension: int = settings.EMBEDDING_DIMENSION
    ):
        self.store_dir = store_dir or settings.VECTOR_STORE_DIR
        self.dimension = dimension
        self.index_file = self.store_dir / "index.faiss"
        self.metadata_file = self.store_dir / "metadata.json"
        self.manifest_file = self.store_dir / "manifest.json"
        
        self.index: Optional[faiss.Index] = None
        self.chunks_metadata: List[Dict[str, Any]] = []

    def is_index_ready(self) -> bool:
        """Checks if a valid index is loaded or exists on disk."""
        if self.index is not None and len(self.chunks_metadata) > 0:
            return True
        return self.index_file.exists() and self.metadata_file.exists() and self.manifest_file.exists()

    def is_idempotent_match(self, current_doc_checksums: Dict[str, str]) -> bool:
        """Checks if existing manifest matches the given documents and settings."""
        if not self.is_index_ready():
            return False

        try:
            with open(self.manifest_file, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            if manifest.get("embedding_dimension") != self.dimension:
                return False
            if manifest.get("embedding_model") != settings.EMBEDDING_MODEL:
                return False
            if manifest.get("chunk_size") != settings.CHUNK_SIZE:
                return False

            cached_docs = manifest.get("source_documents", {})
            if set(cached_docs.keys()) != set(current_doc_checksums.keys()):
                return False

            for doc_name, checksum in current_doc_checksums.items():
                if cached_docs.get(doc_name) != checksum:
                    return False

            return True
        except Exception as e:
            logger.warning(f"Failed to verify index manifest: {e}")
            return False

    def build_index(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
        source_doc_checksums: Dict[str, str]
    ):
        """Constructs and persists FAISS index with L2 normalization for cosine similarity."""
        if not chunks or not embeddings:
            raise ValueError("Chunks and embeddings cannot be empty")

        if len(chunks) != len(embeddings):
            raise ValueError(f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings")

        logger.info(f"Building FAISS IndexFlatIP for {len(chunks)} vectors of dim {self.dimension}...")
        
        # Convert to numpy array float32 and normalize
        vectors = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(vectors)

        # Create IndexFlatIP (inner product on normalized vectors = cosine similarity)
        index = faiss.IndexFlatIP(self.dimension)
        index.add(vectors)

        self.index = index
        self.chunks_metadata = [chunk.to_dict() for chunk in chunks]

        # Save to disk
        self.store_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_file))

        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.chunks_metadata, f, indent=2, ensure_ascii=False)

        manifest = {
            "index_version": "1.0",
            "embedding_model": settings.EMBEDDING_MODEL,
            "embedding_dimension": self.dimension,
            "chunk_size": settings.CHUNK_SIZE,
            "chunk_overlap": settings.CHUNK_OVERLAP,
            "source_documents": source_doc_checksums,
            "chunk_count": len(chunks),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        logger.info(f"FAISS index and metadata successfully persisted to {self.store_dir}")

    def load_index(self) -> bool:
        """Loads index and metadata from disk."""
        if not (self.index_file.exists() and self.metadata_file.exists()):
            logger.warning("FAISS index files not found on disk")
            return False

        try:
            logger.info(f"Loading FAISS index from {self.index_file}...")
            self.index = faiss.read_index(str(self.index_file))

            with open(self.metadata_file, "r", encoding="utf-8") as f:
                self.chunks_metadata = json.load(f)

            logger.info(f"Loaded index with {self.index.ntotal} vectors and {len(self.chunks_metadata)} metadata entries")
            return True
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            return False

    def search(
        self,
        query_vector: List[float],
        top_k: int = settings.TOP_K,
        relevance_threshold: float = settings.RELEVANCE_THRESHOLD
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Search top-k most similar chunks using cosine similarity."""
        if self.index is None:
            if not self.load_index():
                raise RuntimeError("Vector store index is not initialized or loaded")

        vec = np.array([query_vector], dtype=np.float32)
        faiss.normalize_L2(vec)

        scores, indices = self.index.search(vec, top_k * 2)  # retrieve slightly more for filtering/dedup

        results: List[Tuple[Dict[str, Any], float]] = []
        seen_pages = set()

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks_metadata):
                continue
            
            float_score = float(score)
            if float_score < relevance_threshold:
                continue

            meta = self.chunks_metadata[idx]
            # Page deduplication key to balance evidence across distinct pages if desirable
            page_key = f"{meta['document_name']}:{meta['page_number']}"
            
            results.append((meta, float_score))
            seen_pages.add(page_key)

            if len(results) >= top_k:
                break

        return results

