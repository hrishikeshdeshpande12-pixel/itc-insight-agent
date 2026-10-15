from pydantic import BaseModel, Field, EmailStr
from typing import Optional

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The user query regarding ITC")
    session_id: Optional[str] = Field(None, description="Optional conversation session ID")
    user_id: Optional[str] = Field(None, description="Optional user ID for conversation persistence")

class RetrievePageRequest(BaseModel):
    document_name: str
    page_number: int

class RegisterRequest(BaseModel):
    email: str = Field(..., description="Corporate or user email address")
    password: str = Field(..., min_length=6, description="User password (minimum 6 characters)")
    display_name: Optional[str] = Field(None, description="User display name")
    full_name: Optional[str] = Field(None, description="Alias for user display name")

class LoginRequest(BaseModel):
    email: str = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")
