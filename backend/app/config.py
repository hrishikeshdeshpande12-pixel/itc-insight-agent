import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = BACKEND_DIR.parent

# Load .env
env_path = BACKEND_DIR / ".env"
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    # GCP & Vertex AI
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "itc-fmcg-agent")
    GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-east1")
    GOOGLE_GENAI_USE_VERTEXAI: bool = True

    # GCS Bucket
    GCS_BUCKET: str = os.getenv("GCS_BUCKET", "itc-fmcg-agent-documents")
    GCS_SOURCE_PREFIX: str = os.getenv("GCS_SOURCE_PREFIX", "itc/source-documents/")

    # Embeddings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "768"))

    # LLM Generation Model
    GENERATION_MODEL: str = os.getenv("GENERATION_MODEL", "gemini-2.5-flash")

    # Retrieval
    TOP_K: int = int(os.getenv("TOP_K", "5"))
    RELEVANCE_THRESHOLD: float = float(os.getenv("RELEVANCE_THRESHOLD", "0.30"))

    # Chunking
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150"))

    # Paths
    BASE_DIR: Path = BACKEND_DIR
    PROJECT_ROOT: Path = WORKSPACE_ROOT
    DATA_SOURCE_DIR: Path = WORKSPACE_ROOT / "data" / "itc-source-documents"
    VECTOR_STORE_DIR: Path = BACKEND_DIR / "data" / "vector_store"
    PAGE_IMAGES_DIR: Path = BACKEND_DIR / "data" / "page_images"
    CHUNKS_DIR: Path = BACKEND_DIR / "data" / "chunks"

    @field_validator("DATA_SOURCE_DIR", "VECTOR_STORE_DIR", "PAGE_IMAGES_DIR", "CHUNKS_DIR", mode="before")
    @classmethod
    def resolve_paths(cls, v):
        if isinstance(v, Path):
            return v.resolve()
        path = Path(v)
        if not path.is_absolute():
            # Check relative to WORKSPACE_ROOT first, then BACKEND_DIR
            ws_path = (WORKSPACE_ROOT / path).resolve()
            if ws_path.exists():
                return ws_path
            bk_path = (BACKEND_DIR / path).resolve()
            return bk_path
        return path.resolve()

    # Cloud Firestore & GCS
    FIRESTORE_KNOWLEDGE_COLLECTION: str = os.getenv("FIRESTORE_KNOWLEDGE_COLLECTION", "itc_knowledge")

    # Administration & Approval Notifications
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "hrishikeshdeshpande23@gmail.com")
    APP_URL: str = os.getenv("APP_URL", "http://localhost:5173")

    # Email Service (SMTP)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")

    class Config:
        extra = "allow"

settings = Settings()

