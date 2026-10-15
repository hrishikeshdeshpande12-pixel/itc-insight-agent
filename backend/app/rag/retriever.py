from typing import List, Dict, Any, Optional
from app.config import settings
from app.rag.embeddings import GeminiEmbedder
from app.services.firestore_knowledge_service import firestore_knowledge_service
from app.utils.logging import get_logger

logger = get_logger("rag.retriever")

VISUAL_INTENT_KEYWORDS = {
    "diagram", "chart", "graph", "figure", "table", "visual",
    "model", "pillar", "pillars", "framework", "architecture",
    "structure", "flowchart", "trend", "comparison", "growth platform",
    "value creation", "itc next", "governance structure", "matrix"
}

class RetrievedEvidence:
    def __init__(
        self,
        document_name: str,
        page_number: int,
        chunk_id: str,
        content: str,
        enriched_content: str,
        score: float,
        visual_available: bool = False,
        image_path: Optional[str] = None,
        table_context: bool = False
    ):
        self.document_name = document_name
        self.page_number = page_number
        self.chunk_id = chunk_id
        self.content = content
        self.enriched_content = enriched_content
        self.score = score
        self.visual_available = visual_available
        self.image_path = image_path
        self.table_context = table_context

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_name": self.document_name,
            "page_number": self.page_number,
            "chunk_id": self.chunk_id,
            "content": self.content,
            "enriched_content": self.enriched_content,
            "score": self.score,
            "visual_available": self.visual_available,
            "image_path": self.image_path,
            "table_context": self.table_context,
        }

class ITCRetriever:
    """
    100% Cloud-Native Retriever powered exclusively by Google Cloud Firestore Vector Search.
    Zero local filesystem or local FAISS index dependency.
    """
    def __init__(self, embedder: Optional[GeminiEmbedder] = None):
        self.embedder = embedder or GeminiEmbedder()

    def is_visual_query(self, query: str) -> bool:
        """Determines if query likely requests or benefits from visual diagram/chart context."""
        q_lower = query.lower()
        return any(kw in q_lower for kw in VISUAL_INTENT_KEYWORDS)

    def retrieve(
        self,
        query: str,
        top_k: int = settings.TOP_K,
        relevance_threshold: float = settings.RELEVANCE_THRESHOLD
    ) -> List[RetrievedEvidence]:
        """Embeds query and retrieves top matching chunks directly from Google Cloud Firestore."""
        logger.info(f"Retrieving evidence from GCP Firestore for query: '{query[:80]}...' (top_k={top_k})")
        query_vector = self.embedder.embed_query(query)

        raw_results = firestore_knowledge_service.search_knowledge(
            query_vector=query_vector,
            top_k=top_k,
            relevance_threshold=relevance_threshold
        )

        logger.info(f"Retrieved {len(raw_results)} chunks directly from GCP Firestore.")

        evidence_list: List[RetrievedEvidence] = []
        is_visual = self.is_visual_query(query)

        for meta, score in raw_results:
            img_path = meta.get("image_path")
            has_visual = meta.get("visual_context_available", False)

            if is_visual and img_path:
                has_visual = True

            ev = RetrievedEvidence(
                document_name=meta.get("document_name", "Unknown Document"),
                page_number=meta.get("page_number", 1),
                chunk_id=meta.get("chunk_id", ""),
                content=meta.get("chunk_text", ""),
                enriched_content=meta.get("enriched_text", meta.get("chunk_text", "")),
                score=score,
                visual_available=has_visual,
                image_path=img_path,
                table_context=meta.get("table_context", False)
            )
            evidence_list.append(ev)

        logger.info(f"Retrieved {len(evidence_list)} evidence chunks (scores: {[round(e.score, 3) for e in evidence_list]})")
        return evidence_list
