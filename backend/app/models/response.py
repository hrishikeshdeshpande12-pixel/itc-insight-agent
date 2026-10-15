from pydantic import BaseModel, Field
from typing import Optional, List

class Citation(BaseModel):
    source_type: str = Field(..., description="'document' or 'web'")
    title: str = Field(..., description="Document name or Web source title")
    page_number: Optional[int] = Field(None, description="Page number for document citations")
    url: Optional[str] = Field(None, description="External URL for web citations")
    snippet: Optional[str] = Field(None, description="Supporting excerpt from the source")
    full_content: Optional[str] = Field(None, description="Complete extracted text and data from this source chunk/page")
    image_url: Optional[str] = Field(None, description="URL path to rendered page image preview if available")
    score: Optional[float] = Field(None, description="Retrieval similarity score")
    has_visual: Optional[bool] = Field(False, description="Whether this citation contains a visual diagram or chart")

class ChatResponse(BaseModel):
    answer: str = Field(..., description="Synthesized response in assistant's own words")
    citations: List[Citation] = Field(default_factory=list, description="Structured citations")
    source_type: str = Field("document", description="'document', 'web', 'hybrid', or 'none'")
    visual_context_used: bool = Field(False, description="Whether visual diagram/chart context was utilized")
    related_images: List[dict] = Field(default_factory=list, description="Relevant diagram or flowchart images from official documents")
    session_id: Optional[str] = Field(None, description="Session ID for multi-turn continuity")

class HealthResponse(BaseModel):
    status: str
    project_id: str
    region: str
    vector_store_ready: bool
    documents_indexed: int
    total_chunks: int

