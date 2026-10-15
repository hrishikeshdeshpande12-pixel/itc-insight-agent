from fastapi import APIRouter, HTTPException, Query, Response
from app.services.gcs_storage_service import gcs_storage_service
from app.utils.logging import get_logger

logger = get_logger("api.documents")
router = APIRouter(prefix="/api/documents", tags=["Documents"])

@router.get("/page-image")
def get_page_image(
    document: str = Query(..., description="Document filename"),
    page: int = Query(..., ge=1, description="1-based page number")
):
    """
    Returns high-resolution PNG render of a specific PDF document page
    exclusively from Google Cloud Storage (gs://itc-fmcg-agent-documents) with RAM caching.
    Zero local filesystem dependency.
    """
    try:
        cloud_img_bytes = gcs_storage_service.get_page_image_bytes(document, page)
        if cloud_img_bytes and len(cloud_img_bytes) > 0:
            return Response(
                content=cloud_img_bytes,
                media_type="image/png",
                headers={"Cache-Control": "public, max-age=86400"}
            )
    except Exception as gcs_err:
        logger.error(f"GCS image fetch error for {document} p.{page}: {gcs_err}")

    raise HTTPException(
        status_code=404,
        detail=f"Page {page} of '{document}' could not be loaded from Google Cloud Storage."
    )

@router.get("/page-text")
def get_page_text(
    document: str = Query(..., description="Document filename"),
    page: int = Query(..., ge=1, description="1-based page number")
):
    """
    Extracts raw text and metadata directly from a document page hosted in Google Cloud Storage.
    Zero local filesystem dependency.
    """
    try:
        text, total_pages = gcs_storage_service.get_page_text_from_gcs(document, page)
        if text is not None:
            return {
                "document": document,
                "page": page,
                "total_pages": total_pages,
                "text": text,
                "character_count": len(text),
                "source": "Google Cloud Storage"
            }
    except Exception as gcs_err:
        logger.error(f"GCS text extraction error for {document} p.{page}: {gcs_err}")

    raise HTTPException(
        status_code=404,
        detail=f"Text for page {page} of '{document}' could not be loaded from Google Cloud Storage."
    )
