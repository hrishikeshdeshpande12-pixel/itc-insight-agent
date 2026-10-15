import time
from typing import List, Optional
from google import genai
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("rag.embeddings")

class GeminiEmbedder:
    def __init__(
        self,
        model_name: str = settings.EMBEDDING_MODEL,
        dimension: int = settings.EMBEDDING_DIMENSION,
        batch_size: int = 50
    ):
        self.model_name = model_name
        self.dimension = dimension
        self.batch_size = batch_size
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(
                vertexai=True,
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.GOOGLE_CLOUD_LOCATION
            )
        return self._client

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for document chunks using RETRIEVAL_DOCUMENT task type."""
        if not texts:
            return []

        client = self._get_client()
        all_embeddings: List[List[float]] = []
        total = len(texts)

        for i in range(0, total, self.batch_size):
            batch = texts[i:i + self.batch_size]
            retries = 3
            backoff = 2.0

            while retries > 0:
                try:
                    resp = client.models.embed_content(
                        model=self.model_name,
                        contents=batch,
                        config={
                            "output_dimensionality": self.dimension,
                            "task_type": "RETRIEVAL_DOCUMENT"
                        }
                    )
                    batch_vecs = [e.values for e in resp.embeddings]
                    all_embeddings.extend(batch_vecs)
                    logger.info(f"Embedded {len(all_embeddings)}/{total} chunks")
                    time.sleep(0.3)  # Gentle pacing
                    break
                except Exception as e:
                    retries -= 1
                    logger.warning(f"Embedding batch notice: {e}. Retrying in {backoff}s...")
                    time.sleep(backoff)
                    backoff *= 2.0
                    if retries == 0:
                        raise e

        return all_embeddings

    def embed_query(self, query: str) -> List[float]:
        """Generates embedding for a user query using RETRIEVAL_QUERY task type."""
        client = self._get_client()
        retries = 3
        backoff = 1.5

        while retries > 0:
            try:
                resp = client.models.embed_content(
                    model=self.model_name,
                    contents=query,
                    config={
                        "output_dimensionality": self.dimension,
                        "task_type": "RETRIEVAL_QUERY"
                    }
                )
                return resp.embeddings[0].values
            except Exception as e:
                retries -= 1
                logger.warning(f"Embedding query notice: {e}. Retrying in {backoff}s...")
                time.sleep(backoff)
                backoff *= 2.0
                if retries == 0:
                    raise e
