import threading
from pathlib import Path
from typing import Optional, Tuple, Dict
from google.cloud import storage
import fitz
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("service.gcs_storage")

class GCSStorageService:
    """
    100% Cloud-Native Google Cloud Storage service for ITC documents and page images.
    Zero local filesystem dependency — retrieves exclusively from gs://itc-fmcg-agent-documents
    with an in-memory RAM cache for sub-millisecond repeated access.
    """
    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or settings.GCS_BUCKET
        self._client: Optional[storage.Client] = None
        self._bucket = None
        # In-memory RAM caches (never touches local disk)
        self._image_memory_cache: Dict[str, bytes] = {}
        self._pdf_memory_cache: Dict[str, bytes] = {}
        self._lock = threading.RLock()

    @property
    def client(self) -> storage.Client:
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = storage.Client(project=settings.GOOGLE_CLOUD_PROJECT)
        return self._client

    @property
    def bucket(self):
        if self._bucket is None:
            with self._lock:
                if self._bucket is None:
                    self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket

    def _store_image_in_memory(self, key: str, data: bytes) -> None:
        with self._lock:
            if len(self._image_memory_cache) >= 150:
                oldest_key = next(iter(self._image_memory_cache))
                self._image_memory_cache.pop(oldest_key, None)
            self._image_memory_cache[key] = data

    def _upload_image_to_gcs_async(self, image_blob_name: str, img_bytes: bytes) -> None:
        """Uploads rendered PNG to Google Cloud Storage in a background thread."""
        def _worker():
            try:
                blob = self.bucket.blob(image_blob_name)
                blob.cache_control = "public, max-age=86400"
                blob.upload_from_string(img_bytes, content_type="image/png")
                logger.info(f"Synced rendered page to GCS: gs://{self.bucket_name}/{image_blob_name}")
            except Exception as e:
                logger.warning(f"Background GCS image upload notice: {e}")

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def prefetch_images_async(self, page_specs: list) -> None:
        """
        Pre-fetches cited page images from Google Cloud Storage in parallel while Gemini
        is generating the text response, so that when the UI renders the response,
        the images are served from RAM in < 0.1 ms.
        """
        def _prefetch_one(doc_name: str, page_num: int):
            try:
                self.get_page_image_bytes(doc_name, page_num)
            except Exception:
                pass

        for spec in page_specs[:4]:
            doc_name = spec.get("document")
            page_num = spec.get("page")
            if doc_name and page_num:
                threading.Thread(
                    target=_prefetch_one,
                    args=(doc_name, page_num),
                    daemon=True
                ).start()

    def get_page_image_bytes(self, document_name: str, page: int) -> Optional[bytes]:
        """
        Fetches a document page PNG exclusively from Google Cloud Storage (with RAM cache).
        Zero local disk reads or writes.
        """
        safe_stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in Path(document_name).stem)
        cache_key = f"{safe_stem}_page_{page}"
        image_blob_name = f"itc/page-images/{cache_key}.png"

        # 1. Check in-memory RAM cache (< 0.1 ms)
        if cache_key in self._image_memory_cache:
            return self._image_memory_cache[cache_key]

        # 2. Fetch pre-rendered PNG directly from Google Cloud Storage in a single HTTP call
        try:
            blob = self.bucket.blob(image_blob_name)
            img_bytes = blob.download_as_bytes()
            logger.info(f"Served page image from GCS: gs://{self.bucket_name}/{image_blob_name}")
            self._store_image_in_memory(cache_key, img_bytes)
            return img_bytes
        except Exception as e:
            logger.warning(f"GCS page image fetch notice for {image_blob_name}: {e}")

        # 3. Cloud PDF Fallback: Fetch source PDF from GCS, render page in memory, and save PNG back to GCS
        pdf_bytes = self.get_source_pdf_bytes(document_name)
        if not pdf_bytes:
            return None

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            if page < 1 or page > len(doc):
                doc.close()
                return None

            pdf_page = doc.load_page(page - 1)
            pix = pdf_page.get_pixmap(dpi=120)
            img_bytes = pix.tobytes(output="png")
            doc.close()

            self._store_image_in_memory(cache_key, img_bytes)
            self._upload_image_to_gcs_async(image_blob_name, img_bytes)
            return img_bytes
        except Exception as e:
            logger.error(f"Error rendering page {page} from GCS PDF: {e}")
            return None

    def get_source_pdf_bytes(self, document_name: str) -> Optional[bytes]:
        """Fetches the source PDF exclusively from Google Cloud Storage (with in-memory caching)."""
        if document_name in self._pdf_memory_cache:
            return self._pdf_memory_cache[document_name]

        blob_name = f"itc/source-documents/{document_name}"
        blob = self.bucket.blob(blob_name)
        if blob.exists():
            logger.info(f"Fetching source PDF from GCS: gs://{self.bucket_name}/{blob_name}")
            data = blob.download_as_bytes()
            with self._lock:
                if len(self._pdf_memory_cache) >= 4:
                    oldest = next(iter(self._pdf_memory_cache))
                    self._pdf_memory_cache.pop(oldest, None)
                self._pdf_memory_cache[document_name] = data
            return data

        blobs = list(self.bucket.list_blobs(prefix="itc/source-documents/"))
        target_stem = Path(document_name).stem.lower().replace("_", "-")
        for b in blobs:
            clean_stem = Path(b.name).stem.lower().replace("_", "-")
            if target_stem in clean_stem or clean_stem in target_stem:
                data = b.download_as_bytes()
                with self._lock:
                    self._pdf_memory_cache[document_name] = data
                return data

        return None

    def get_page_text_from_gcs(self, document_name: str, page: int) -> Tuple[Optional[str], int]:
        """Extracts text and total page count directly from Google Cloud Storage."""
        pdf_bytes = self.get_source_pdf_bytes(document_name)
        if not pdf_bytes:
            return None, 0

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(doc)
        if page < 1 or page > total_pages:
            doc.close()
            return None, total_pages

        pdf_page = doc.load_page(page - 1)
        text = pdf_page.get_text("text").strip()
        doc.close()
        return text, total_pages

gcs_storage_service = GCSStorageService()
