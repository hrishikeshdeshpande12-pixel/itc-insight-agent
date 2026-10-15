import hashlib
from typing import List, Dict, Any, Optional
from app.config import settings
from app.rag.loader import PageData
from app.utils.logging import get_logger

logger = get_logger("rag.chunker")

class DocumentChunk:
    def __init__(
        self,
        chunk_id: str,
        document_name: str,
        page_number: int,
        chunk_text: str,
        enriched_text: str,
        source_type: str = "document",
        source_path: str = "",
        visual_context_available: bool = False,
        image_path: Optional[str] = None,
        table_context: bool = False,
        checksum: str = ""
    ):
        self.chunk_id = chunk_id
        self.document_name = document_name
        self.page_number = page_number
        self.chunk_text = chunk_text
        self.enriched_text = enriched_text
        self.source_type = source_type
        self.source_path = source_path
        self.visual_context_available = visual_context_available
        self.image_path = image_path
        self.table_context = table_context
        self.checksum = checksum or hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_name": self.document_name,
            "page_number": self.page_number,
            "chunk_text": self.chunk_text,
            "enriched_text": self.enriched_text,
            "source_type": self.source_type,
            "source_path": self.source_path,
            "visual_context_available": self.visual_context_available,
            "image_path": self.image_path,
            "table_context": self.table_context,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentChunk":
        return cls(**data)


class PageAwareChunker:
    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_page(
        self,
        page_data: PageData,
        enriched_text: str,
        visual_analysis: str = ""
    ) -> List[DocumentChunk]:
        """Split enriched page representation into page-aware chunks."""
        chunks: List[DocumentChunk] = []
        doc_name = page_data.document_name
        page_num = page_data.page_number
        has_visual = page_data.has_visuals and bool(visual_analysis or page_data.image_path)
        has_table = bool(page_data.tables_text)

        # Context header attached to every chunk to anchor page and document provenance
        header = f"[Source: {doc_name} | Page {page_num}]\n"
        visual_addon = f"\n[Visual Context: {visual_analysis}]\n" if visual_analysis else ""

        full_content = enriched_text.strip()
        if not full_content:
            return []

        # If the whole enriched content fits in chunk_size, keep as single high-fidelity page chunk
        if len(full_content) <= self.chunk_size:
            chunk_id = f"{doc_name}_p{page_num}_c0"
            chunks.append(DocumentChunk(
                chunk_id=chunk_id,
                document_name=doc_name,
                page_number=page_num,
                chunk_text=full_content,
                enriched_text=full_content,
                source_path=page_data.document_name,
                visual_context_available=has_visual,
                image_path=page_data.image_path,
                table_context=has_table
            ))
            return chunks

        # Otherwise, split by paragraph/logical sections with overlap
        paragraphs = full_content.split("\n\n")
        current_chunk_paras: List[str] = []
        current_length = 0
        chunk_index = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_len = len(para)
            if current_length + para_len > self.chunk_size and current_chunk_paras:
                # Build chunk
                body = "\n\n".join(current_chunk_paras)
                chunk_text = f"{header}{body}{visual_addon}"
                chunk_id = f"{doc_name}_p{page_num}_c{chunk_index}"
                
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    document_name=doc_name,
                    page_number=page_num,
                    chunk_text=chunk_text,
                    enriched_text=chunk_text,
                    source_path=doc_name,
                    visual_context_available=has_visual,
                    image_path=page_data.image_path,
                    table_context=has_table or ("TABLES:" in body)
                ))
                chunk_index += 1

                # Retain overlap paragraphs
                overlap_length = 0
                overlap_paras = []
                for p in reversed(current_chunk_paras):
                    if overlap_length + len(p) <= self.chunk_overlap:
                        overlap_paras.insert(0, p)
                        overlap_length += len(p)
                    else:
                        break
                current_chunk_paras = overlap_paras
                current_length = overlap_length

            current_chunk_paras.append(para)
            current_length += para_len

        # Final remaining chunk
        if current_chunk_paras:
            body = "\n\n".join(current_chunk_paras)
            chunk_text = f"{header}{body}{visual_addon}"
            chunk_id = f"{doc_name}_p{page_num}_c{chunk_index}"
            chunks.append(DocumentChunk(
                chunk_id=chunk_id,
                document_name=doc_name,
                page_number=page_num,
                chunk_text=chunk_text,
                enriched_text=chunk_text,
                source_path=doc_name,
                visual_context_available=has_visual,
                image_path=page_data.image_path,
                table_context=has_table or ("TABLES:" in body)
            ))

        return chunks

