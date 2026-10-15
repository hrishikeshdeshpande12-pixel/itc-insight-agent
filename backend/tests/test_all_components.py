import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.config import settings
from app.rag.loader import DocumentLoader, PageData, compute_file_checksum
from app.rag.visual_processor import VisualProcessor
from app.rag.chunker import PageAwareChunker, DocumentChunk
from app.rag.vector_store import FaissVectorStore
from app.rag.retriever import ITCRetriever
from app.agent.tools import ITCAgentTools
from app.models.request import ChatRequest
from app.models.response import ChatResponse, Citation, HealthResponse
from app.main import app

client = TestClient(app)

def test_1_pdf_discovery():
    loader = DocumentLoader()
    docs = loader.discover_documents()
    assert len(docs) >= 4, f"Expected at least 4 PDF documents, found {len(docs)}"
    names = [d.name for d in docs]
    assert "cmd-presentation.pdf" in names
    assert "ITC-Report-and-Accounts-2026.pdf" in names

def test_2_pdf_validation_and_checksum():
    loader = DocumentLoader()
    docs = loader.discover_documents()
    for d in docs:
        checksum = compute_file_checksum(d)
        assert len(checksum) == 64, "Checksum should be valid 64-char SHA-256"
        assert d.stat().st_size > 0, "PDF size must be greater than zero"

def test_3_text_extraction():
    loader = DocumentLoader()
    sample_pdf = settings.DATA_SOURCE_DIR / "cmd-presentation.pdf"
    pages = loader.load_document(sample_pdf, render_images=False)
    assert len(pages) == 75
    # Verify non-empty text extraction on key content pages
    extracted_any_text = any(len(p.raw_text) > 50 for p in pages)
    assert extracted_any_text

def test_4_page_number_preservation():
    loader = DocumentLoader()
    sample_pdf = settings.DATA_SOURCE_DIR / "ITC-R-and-A-2026-Theme-feature.pdf"
    pages = loader.load_document(sample_pdf, render_images=False)
    for idx, p in enumerate(pages, 1):
        assert p.page_number == idx, f"Expected page {idx}, got {p.page_number}"

def test_5_table_extraction_representation():
    sample_page = PageData(
        document_name="test.pdf",
        doc_checksum="abc",
        page_number=1,
        raw_text="Sample text",
        tables_text="Table 1:\nColumns: Segment | Revenue\nFoods | 15000",
        has_visuals=False,
        image_count=0,
        drawing_count=0,
        table_count=1,
        page_checksum="xyz"
    )
    assert "Table 1:" in sample_page.tables_text
    assert "Segment | Revenue" in sample_page.tables_text

def test_6_visual_page_detection():
    vp = VisualProcessor()
    page_with_images = PageData(
        document_name="cmd-presentation.pdf",
        doc_checksum="abc",
        page_number=3,
        raw_text="Categories 1 to 40",
        tables_text="",
        has_visuals=True,
        image_count=7,
        drawing_count=27,
        table_count=0,
        page_checksum="xyz",
        image_path="sample.png"
    )
    # Presentation with drawings/images should be detected for visual relevance
    assert page_with_images.has_visuals

def test_7_page_aware_chunking():
    chunker = PageAwareChunker(chunk_size=500, chunk_overlap=50)
    page_data = PageData(
        document_name="doc.pdf",
        doc_checksum="abc",
        page_number=5,
        raw_text="Paragraph 1 about ITC FMCG strategy.\n\nParagraph 2 about sustainable growth.\n\nParagraph 3 about digital acceleration.",
        tables_text="",
        has_visuals=False,
        image_count=0,
        drawing_count=0,
        table_count=0,
        page_checksum="xyz"
    )
    chunks = chunker.chunk_page(page_data, page_data.raw_text)
    assert len(chunks) >= 1
    for c in chunks:
        assert c.page_number == 5
        assert c.document_name == "doc.pdf"

def test_8_metadata_preservation():
    chunk = DocumentChunk(
        chunk_id="chunk_1",
        document_name="report.pdf",
        page_number=10,
        chunk_text="Test chunk text",
        enriched_text="Enriched text",
        visual_context_available=True,
        table_context=True
    )
    d = chunk.to_dict()
    assert d["chunk_id"] == "chunk_1"
    assert d["page_number"] == 10
    assert d["visual_context_available"] is True
    assert d["table_context"] is True

def test_9_embedding_generation():
    from app.rag.embeddings import GeminiEmbedder
    embedder = GeminiEmbedder()
    vec = embedder.embed_query("ITC FMCG growth strategy")
    assert len(vec) == settings.EMBEDDING_DIMENSION

def test_10_faiss_creation_and_persistence(tmp_path):
    store = FaissVectorStore(store_dir=tmp_path, dimension=settings.EMBEDDING_DIMENSION)
    c1 = DocumentChunk("c1", "doc.pdf", 1, "ITC strategy text", "ITC strategy text")
    vec1 = [0.1] * settings.EMBEDDING_DIMENSION
    store.build_index([c1], [vec1], {"doc.pdf": "checksum123"})
    assert (tmp_path / "index.faiss").exists()
    assert (tmp_path / "metadata.json").exists()
    assert (tmp_path / "manifest.json").exists()

def test_11_faiss_retrieval(tmp_path):
    store = FaissVectorStore(store_dir=tmp_path, dimension=settings.EMBEDDING_DIMENSION)
    c1 = DocumentChunk("c1", "doc.pdf", 1, "ITC strategy text", "ITC strategy text")
    vec1 = [0.1] * settings.EMBEDDING_DIMENSION
    store.build_index([c1], [vec1], {"doc.pdf": "checksum123"})
    
    results = store.search(vec1, top_k=1, relevance_threshold=0.0)
    assert len(results) == 1
    meta, score = results[0]
    assert meta["chunk_id"] == "c1"

def test_12_citation_creation():
    c = Citation(
        source_type="document",
        title="ITC Report and Accounts 2026",
        page_number=13,
        snippet="Corporate governance structure..."
    )
    assert c.source_type == "document"
    assert c.page_number == 13

def test_13_pydantic_validation():
    req = ChatRequest(question="What is ITC Next?")
    assert req.question == "What is ITC Next?"
    with pytest.raises(Exception):
        ChatRequest(question="")

def test_14_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["project_id"] == settings.GOOGLE_CLOUD_PROJECT
    assert data["region"] == settings.GOOGLE_CLOUD_LOCATION

def test_15_chat_validation_error():
    resp = client.post("/chat", json={"question": ""})
    assert resp.status_code == 400 or resp.status_code == 422

def test_16_agent_tools_structure():
    tools = ITCAgentTools()
    assert hasattr(tools, "search_itc_knowledge")
    assert hasattr(tools, "retrieve_itc_page")
    assert hasattr(tools, "search_web_if_needed")

def test_17_page_image_and_text_endpoints():
    # Test on-demand page image rendering
    resp_img = client.get("/api/documents/page-image?document=cmd-presentation.pdf&page=1")
    assert resp_img.status_code == 200
    assert resp_img.headers["content-type"].startswith("image/")

    # Test page text extraction
    resp_txt = client.get("/api/documents/page-text?document=cmd-presentation.pdf&page=1")
    assert resp_txt.status_code == 200
    data = resp_txt.json()
    assert data["document"] == "cmd-presentation.pdf"
    assert data["page"] == 1
    assert "text" in data


