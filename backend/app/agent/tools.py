from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types

from app.config import settings
from app.rag.retriever import ITCRetriever
from app.models.response import Citation
from app.utils.logging import get_logger

logger = get_logger("agent.tools")

class ITCAgentTools:
    def __init__(self, retriever: Optional[ITCRetriever] = None):
        self.retriever = retriever or ITCRetriever()
        self._genai_client: Optional[genai.Client] = None

    def _get_genai_client(self) -> genai.Client:
        if self._genai_client is None:
            self._genai_client = genai.Client(
                vertexai=True,
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.GOOGLE_CLOUD_LOCATION
            )
        return self._genai_client

    def search_itc_knowledge(self, question: str, top_k: int = settings.TOP_K) -> Dict[str, Any]:
        """Tool 1: Primary search of the ITC Cloud Knowledge Base (Google Cloud Firestore)."""
        logger.info(f"Tool search_itc_knowledge invoked for: '{question}'")
        evidence_list = self.retriever.retrieve(question, top_k=top_k)

        formatted_evidence = []
        citations: List[Citation] = []
        visual_images = []

        for ev in evidence_list:
            formatted_evidence.append({
                "document": ev.document_name,
                "page": ev.page_number,
                "content": ev.enriched_content,
                "score": ev.score,
                "visual_available": ev.visual_available,
                "image_path": ev.image_path
            })

            # Cloud-backed page image endpoint served from Google Cloud Storage
            img_rel_url = f"/api/documents/page-image?document={ev.document_name}&page={ev.page_number}"
            if ev.visual_available:
                visual_images.append({
                    "document": ev.document_name,
                    "page": ev.page_number
                })

            has_visual_element = bool(
                ev.visual_available
                or "presentation" in ev.document_name.lower()
                or "theme-feature" in ev.document_name.lower()
            )

            snippet = ev.content[:280].replace("\n", " ").strip() + "..."
            citations.append(Citation(
                source_type="document",
                title=ev.document_name,
                page_number=ev.page_number,
                snippet=snippet,
                full_content=ev.enriched_content or ev.content,
                image_url=img_rel_url,
                score=round(float(ev.score), 3),
                has_visual=has_visual_element
            ))

        # Pre-fetch cited page PNGs from Google Cloud Storage in parallel while Gemini synthesizes text
        try:
            from app.services.gcs_storage_service import gcs_storage_service
            prefetch_specs = [{"document": c.title, "page": c.page_number} for c in citations[:4]]
            gcs_storage_service.prefetch_images_async(prefetch_specs)
        except Exception:
            pass

        return {
            "evidence": formatted_evidence,
            "citations": citations,
            "visual_images": visual_images,
            "count": len(formatted_evidence)
        }

    def retrieve_itc_page(self, document_name: str, page_number: int) -> Dict[str, Any]:
        """Tool 2: Inspect a specific ITC document page in full detail from Google Cloud Storage."""
        logger.info(f"Tool retrieve_itc_page invoked for {document_name} page {page_number}")
        img_url = f"/api/documents/page-image?document={document_name}&page={page_number}"

        return {
            "document_name": document_name,
            "page_number": page_number,
            "image_available": True,
            "image_url": img_url,
            "image_path": None
        }

    def search_web_if_needed(self, question: str) -> Dict[str, Any]:
        """Tool 3: Controlled Fallback Web Search via Google Search Grounding on Vertex AI."""
        logger.info(f"Tool search_web_if_needed invoked for: '{question}'")
        client = self._get_genai_client()

        prompt = f"""Search Google for up-to-date and reliable information regarding this query about ITC Limited:
Question: {question}

Provide an accurate, factual summary. Only use authoritative sources (official ITC statements, BSE/NSE filings, established business news)."""

        try:
            response = client.models.generate_content(
                model=settings.GENERATION_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )

            citations: List[Citation] = []
            candidates = response.candidates
            if candidates and candidates[0].grounding_metadata:
                gm = candidates[0].grounding_metadata
                chunks = getattr(gm, "grounding_chunks", [])
                for chunk in chunks:
                    web = getattr(chunk, "web", None)
                    if web:
                        title = getattr(web, "title", "Web Source")
                        uri = getattr(web, "uri", None)
                        citations.append(Citation(
                            source_type="web",
                            title=title or "Official Web Intelligence",
                            url=uri,
                            snippet="Current external market & news intelligence"
                        ))

            unique_citations = []
            seen_urls = set()
            for c in citations:
                key = c.url or c.title
                if key not in seen_urls:
                    seen_urls.add(key)
                    unique_citations.append(c)

            return {
                "text": response.text if response.text else "",
                "citations": unique_citations[:5]
            }

        except Exception as e:
            logger.error(f"Google search grounding failed: {e}")
            return {
                "text": "Unable to retrieve current web information due to a search service error.",
                "citations": []
            }
