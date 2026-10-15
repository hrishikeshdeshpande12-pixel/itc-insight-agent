import time
from typing import List, Dict, Any, Optional
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("service.firestore_knowledge")

class FirestoreKnowledgeService:
    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or settings.GOOGLE_CLOUD_PROJECT
        self._db: Optional[firestore.Client] = None

    @property
    def db(self) -> firestore.Client:
        if self._db is None:
            self._db = firestore.Client(project=self.project_id)
        return self._db

    def sync_local_chunks_to_firestore(self, chunks_metadata: List[Dict[str, Any]], embeddings: List[List[float]]) -> int:
        """
        Uploads document chunks and embedding vectors into Firestore collection 'itc_knowledge'
        using batch commits of 500 documents.
        """
        if not chunks_metadata or not embeddings or len(chunks_metadata) != len(embeddings):
            raise ValueError("Chunks metadata and embeddings must be non-empty and of equal length.")

        total = len(chunks_metadata)
        logger.info(f"Syncing {total} document chunks and embeddings to Firestore collection 'itc_knowledge'...")

        batch_size = 400
        synced_count = 0
        start_time = time.time()

        for i in range(0, total, batch_size):
            batch = self.db.batch()
            chunk_slice = chunks_metadata[i:i + batch_size]
            vec_slice = embeddings[i:i + batch_size]

            for meta, vec in zip(chunk_slice, vec_slice):
                chunk_id = meta.get("chunk_id") or f"chunk_{synced_count}"
                doc_ref = self.db.collection("itc_knowledge").document(chunk_id)

                doc_payload = {
                    "chunk_id": chunk_id,
                    "document_name": meta.get("document_name", ""),
                    "page_number": meta.get("page_number", 1),
                    "chunk_text": meta.get("chunk_text", ""),
                    "enriched_text": meta.get("enriched_text", meta.get("chunk_text", "")),
                    "visual_context_available": meta.get("visual_context_available", False),
                    "table_context": meta.get("table_context", False),
                    "embedding": Vector(vec)
                }
                batch.set(doc_ref, doc_payload)
                synced_count += 1

            batch.commit()
            logger.info(f"Committed batch: {synced_count}/{total} chunks to Firestore.")

        elapsed = time.time() - start_time
        logger.info(f"Successfully synced {synced_count} chunks to Firestore in {elapsed:.2f}s.")
        return synced_count

    def search_knowledge(
        self,
        query_vector: List[float],
        top_k: int = 5,
        relevance_threshold: float = 0.30
    ) -> List[tuple]:
        """
        Performs Vector Search over 'itc_knowledge' in Firestore using Cosine Distance.
        Returns list of (metadata_dict, similarity_score) tuples matching FAISS interface.
        """
        try:
            query = (
                self.db.collection("itc_knowledge")
                .find_nearest(
                    vector_field="embedding",
                    query_vector=Vector(query_vector),
                    distance_measure=DistanceMeasure.COSINE,
                    limit=top_k,
                    distance_result_field="vector_distance"
                )
            )
            docs = query.get()
            results = []
            for doc in docs:
                data = doc.to_dict() or {}
                # Cosine distance: 0 = identical, 1 = orthogonal, 2 = opposite
                # Cosine similarity: 1.0 - distance
                dist = data.pop("vector_distance", 0.5)
                # Remove raw vector from returned metadata to save memory and network
                data.pop("embedding", None)
                score = round(max(0.0, 1.0 - float(dist)), 4)
                if score >= relevance_threshold:
                    results.append((data, score))
            return results
        except Exception as e:
            logger.warning(f"Firestore vector search note: {e}. Falling back to in-memory store.")
            return []


    def get_chunk_count(self) -> int:
        """Returns total count of document chunks stored in itc_knowledge collection."""
        try:
            count_query = self.db.collection("itc_knowledge").count()
            results = count_query.get()
            return results[0][0].value
        except Exception as e:
            logger.error(f"Error counting documents in itc_knowledge: {e}")
            return 0

# Export default singleton instance
firestore_knowledge_service = FirestoreKnowledgeService()


