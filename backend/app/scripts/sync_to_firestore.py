import json
import faiss
from pathlib import Path
from app.config import settings
from app.services.firestore_knowledge_service import FirestoreKnowledgeService
from app.utils.logging import get_logger

logger = get_logger("scripts.sync_firestore")

def sync_knowledge_to_firestore():
    meta_path = settings.VECTOR_STORE_DIR / "metadata.json"
    index_path = settings.VECTOR_STORE_DIR / "index.faiss"

    if not meta_path.exists() or not index_path.exists():
        logger.error(f"Local vector store not found at {settings.VECTOR_STORE_DIR}")
        return False

    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    logger.info(f"Loading local FAISS index from {index_path}...")
    index = faiss.read_index(str(index_path))
    total_vectors = index.ntotal
    logger.info(f"Loaded FAISS index with {total_vectors} vectors.")

    # Reconstruct vectors
    embeddings = []
    for i in range(total_vectors):
        vec = index.reconstruct(i).tolist()
        embeddings.append(vec)

    service = FirestoreKnowledgeService()
    synced = service.sync_local_chunks_to_firestore(metadata, embeddings)
    logger.info(f"Sync complete! {synced} chunks now stored in Firestore 'itc_knowledge' collection.")
    return True

if __name__ == "__main__":
    sync_knowledge_to_firestore()

