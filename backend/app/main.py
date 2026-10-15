from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import health, chat, documents, auth, sessions, admin
from app.utils.logging import get_logger

logger = get_logger("app.main")

app = FastAPI(
    title="ITC Insight API",
    description="Enterprise Market Intelligence, Strategy & Governance Assistant for ITC Limited (100% Google Cloud Native)",
    version="1.0.0"
)

# CORS configuration for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health.router, tags=["Health"])
app.include_router(chat.router, tags=["Chat"])
app.include_router(documents.router, tags=["Documents"])
app.include_router(auth.router, tags=["Authentication"])
app.include_router(sessions.router, tags=["Sessions"])
app.include_router(admin.router, tags=["Admin"])

@app.on_event("startup")
def startup_event():
    import threading
    from app.services.gcs_storage_service import gcs_storage_service
    threading.Thread(target=lambda: getattr(gcs_storage_service, "bucket", None), daemon=True).start()
    logger.info(
        f"ITC Insight API initialized (100% Cloud-Native: Firestore='{settings.FIRESTORE_KNOWLEDGE_COLLECTION}', "
        f"GCS='gs://{settings.GCS_BUCKET}')"
    )

# Static File & SPA Serving for Unified Deployment
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

dist_candidates = [
    Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
    Path("/app/frontend/dist"),
    Path(__file__).resolve().parent.parent / "dist"
]

frontend_dist = None
for candidate in dist_candidates:
    if candidate.exists() and (candidate / "index.html").exists():
        frontend_dist = candidate
        break

if frontend_dist:
    logger.info(f"Serving built frontend from: {frontend_dist}")
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Don't intercept API routes
        if full_path.startswith("api/") or full_path == "api" or full_path.startswith("health") or full_path.startswith("chat"):
            return None
        file_path = frontend_dist / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")

