from pathlib import Path
from typing import List
from google.cloud import storage
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("utils.gcs_sync")

def sync_documents_to_gcs(pdf_paths: List[Path]) -> None:
    """Syncs source PDFs to GCS bucket as required for source backup storage."""
    try:
        storage_client = storage.Client(project=settings.GOOGLE_CLOUD_PROJECT)
        bucket = storage_client.bucket(settings.GCS_BUCKET)
        prefix = settings.GCS_SOURCE_PREFIX.rstrip("/") + "/"

        for pdf_path in pdf_paths:
            blob_name = f"{prefix}{pdf_path.name}"
            blob = bucket.blob(blob_name)
            if not blob.exists():
                logger.info(f"Uploading {pdf_path.name} to gs://{settings.GCS_BUCKET}/{blob_name}...")
                blob.upload_from_filename(str(pdf_path))
                logger.info(f"Successfully uploaded {pdf_path.name} to GCS backup.")
            else:
                logger.info(f"GCS backup already contains {blob_name}")
    except Exception as e:
        logger.warning(f"GCS sync encountered a non-fatal error: {e}")

