import os
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from google import genai
from google.genai import types
from app.config import settings
from app.rag.loader import PageData
from app.utils.logging import get_logger

logger = get_logger("rag.visual_processor")

VISUAL_ENRICHMENT_PROMPT = """You are an expert document intelligence model analyzing an official corporate report page from ITC Limited.
Analyze this page carefully. If there are diagrams, charts, graphs, flowcharts, business models, frameworks, visual tables, or icons that represent strategic relationships, extract their meaning factually.

Format your response strictly as:
FIGURES AND DIAGRAMS:
[Describe visible diagrams, flowcharts, pillars, frameworks, or charts. E.g., 'ITC Next Strategy architecture', 'Value Creation framework']

VISUAL INSIGHTS:
[Key takeaways, trends, or concepts visible from the visual layout/graphics]

KEY ENTITIES:
[Specific brands, businesses (Foods, Personal Care, Agri, Paperboards, Hotels, etc.), metrics, or initiatives mentioned visually]

IMPORTANT RELATIONSHIPS:
[Hierarchical, sequential, or comparative relationships depicted, e.g., 'Pillar A leads to Outcome B']

Rules:
- Be factual, concise, and professional.
- Do NOT hallucinate exact numeric values if unreadable or ambiguous. If numbers are unreadable, explicitly state 'exact value cannot be reliably determined from chart'.
- If the page has no significant diagrams, charts, or visual frameworks, respond with 'None'.
"""

# Strategic keywords that indicate high-value visual framework/diagram pages
STRATEGIC_FRAMEWORK_KEYWORDS = [
    "value creation", "itc next", "governance", "supervisory",
    "transformation", "triple bottom line", "growth platform",
    "digital accelerator", "core", "adjacent", "vectors of growth",
    "carbon positive", "water positive", "capital allocation"
]

class VisualProcessor:
    """
    100% Cloud-Native Visual Processor.
    Loads and persists visual framework analyses exclusively from Google Cloud Storage
    (gs://itc-fmcg-agent-documents/itc/metadata/visual_enrichment_cache.json).
    Zero local filesystem dependency.
    """
    def __init__(self):
        self._cache: Dict[str, str] = self._load_cache()
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(
                vertexai=True,
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.GOOGLE_CLOUD_LOCATION
            )
        return self._client

    def _load_cache(self) -> Dict[str, str]:
        """Loads visual enrichment cache directly from Google Cloud Storage."""
        try:
            from app.services.gcs_storage_service import gcs_storage_service
            blob = gcs_storage_service.bucket.blob("itc/metadata/visual_enrichment_cache.json")
            if blob.exists():
                data = json.loads(blob.download_as_text(encoding="utf-8"))
                logger.info(f"Loaded {len(data)} cached visual page analyses from GCS: gs://{gcs_storage_service.bucket_name}/itc/metadata/visual_enrichment_cache.json")
                return data
        except Exception as gcs_e:
            logger.warning(f"Notice: Could not load visual cache from GCS: {gcs_e}")
        return {}

    def _save_cache(self):
        """Persists visual enrichment cache directly to Google Cloud Storage."""
        try:
            from app.services.gcs_storage_service import gcs_storage_service
            blob = gcs_storage_service.bucket.blob("itc/metadata/visual_enrichment_cache.json")
            blob.upload_from_string(
                json.dumps(self._cache, indent=2, ensure_ascii=False),
                content_type="application/json"
            )
            logger.info("Persisted visual enrichment cache directly to Google Cloud Storage.")
        except Exception as gcs_e:
            logger.warning(f"Notice: Could not sync visual cache to GCS: {gcs_e}")

    def should_analyze_visually(self, page_data: PageData) -> bool:
        """Determines whether visual multimodal analysis adds value for this page."""
        cache_key = f"{page_data.document_name}:{page_data.page_number}:{page_data.page_checksum}"
        if cache_key in self._cache:
            return True

        text_lower = page_data.raw_text.lower()
        doc_lower = page_data.document_name.lower()

        # Prioritize key strategic framework pages with diagrams
        if any(kw in text_lower for kw in STRATEGIC_FRAMEWORK_KEYWORDS) and page_data.has_visuals:
            return True

        # Sparse pages with graphics in theme feature or presentations
        if ("theme-feature" in doc_lower or "presentation" in doc_lower) and len(page_data.raw_text) < 150:
            return True

        return False

    def analyze_page_image(self, page_data: PageData) -> str:
        """Analyze page image using Gemini multimodal via Google Cloud Storage."""
        cache_key = f"{page_data.document_name}:{page_data.page_number}:{page_data.page_checksum}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not self.should_analyze_visually(page_data):
            return ""

        from app.services.gcs_storage_service import gcs_storage_service
        img_bytes = gcs_storage_service.get_page_image_bytes(page_data.document_name, page_data.page_number)
        if not img_bytes:
            return ""

        retries = 2
        delay = 2.0
        while retries >= 0:
            try:
                logger.info(f"Triggering Gemini multimodal analysis from GCS image for {page_data.document_name} page {page_data.page_number}...")
                client = self._get_client()

                part = types.Part.from_bytes(data=img_bytes, mime_type="image/png")
                response = client.models.generate_content(
                    model=settings.GENERATION_MODEL,
                    contents=[part, VISUAL_ENRICHMENT_PROMPT]
                )

                result_text = response.text.strip() if response.text else ""
                if "None" in result_text and len(result_text) < 30:
                    result_text = ""

                self._cache[cache_key] = result_text
                self._save_cache()
                # Brief pacing delay to avoid hitting rate limits
                time.sleep(1.0)
                return result_text

            except Exception as e:
                retries -= 1
                logger.warning(f"Multimodal analysis notice for {page_data.document_name} page {page_data.page_number}: {e}")
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    time.sleep(delay)
                    delay *= 2.0
                else:
                    break

        return ""

    def create_enriched_representation(self, page_data: PageData, visual_analysis: str = "") -> str:
        """Combines page text, tables, visual diagrams, and metadata into a unified enriched representation."""
        sections = [
            f"=== DOCUMENT: {page_data.document_name} | PAGE: {page_data.page_number} ==="
        ]

        if page_data.raw_text:
            sections.append(f"PAGE TEXT:\n{page_data.raw_text}")

        if page_data.tables_text:
            sections.append(f"TABLES:\n{page_data.tables_text}")

        if visual_analysis:
            sections.append(f"VISUAL CONTEXT & DIAGRAMS:\n{visual_analysis}")

        sections.append(f"PAGE NUMBER: {page_data.page_number}")

        return "\n\n".join(sections)
