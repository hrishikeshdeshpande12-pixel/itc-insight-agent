import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("rag.loader")

class PageData:
    def __init__(
        self,
        document_name: str,
        doc_checksum: str,
        page_number: int,
        raw_text: str,
        tables_text: str,
        has_visuals: bool,
        image_count: int,
        drawing_count: int,
        table_count: int,
        page_checksum: str,
        image_path: Optional[str] = None
    ):
        self.document_name = document_name
        self.doc_checksum = doc_checksum
        self.page_number = page_number
        self.raw_text = raw_text
        self.tables_text = tables_text
        self.has_visuals = has_visuals
        self.image_count = image_count
        self.drawing_count = drawing_count
        self.table_count = table_count
        self.page_checksum = page_checksum
        self.image_path = image_path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_name": self.document_name,
            "doc_checksum": self.doc_checksum,
            "page_number": self.page_number,
            "raw_text": self.raw_text,
            "tables_text": self.tables_text,
            "has_visuals": self.has_visuals,
            "image_count": self.image_count,
            "drawing_count": self.drawing_count,
            "table_count": self.table_count,
            "page_checksum": self.page_checksum,
            "image_path": self.image_path,
        }

def compute_file_checksum(file_path: Path) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()

def compute_page_checksum(text: str, page_number: int, image_count: int) -> str:
    hasher = hashlib.sha256()
    hasher.update(f"{page_number}:{image_count}:{text[:300]}".encode("utf-8"))
    return hasher.hexdigest()

def extract_tables_from_page(page: fitz.Page) -> str:
    """Extract tables using PyMuPDF and format into structured textual form."""
    try:
        tabs = page.find_tables()
        if not tabs.tables:
            return ""
        
        table_outputs = []
        for idx, table in enumerate(tabs.tables, 1):
            rows = table.extract()
            if not rows or len(rows) < 2:
                continue
            
            headers = [str(col).strip() if col is not None else "" for col in rows[0]]
            header_line = " | ".join(h if h else "-" for h in headers)
            
            data_lines = []
            for row in rows[1:]:
                row_vals = [str(val).strip() if val is not None else "" for val in row]
                if any(row_vals):
                    data_lines.append(" | ".join(row_vals))
            
            if data_lines:
                table_str = f"Table {idx}:\nColumns: {header_line}\n" + "\n".join(data_lines)
                table_outputs.append(table_str)
                
        return "\n\n".join(table_outputs)
    except Exception:
        return ""

def render_page_image_if_needed(doc: fitz.Document, page_num: int, doc_stem: str) -> Optional[str]:
    """Renders single page image at 150 DPI and returns path."""
    safe_stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in doc_stem)
    img_file = settings.PAGE_IMAGES_DIR / f"{safe_stem}_page_{page_num}.png"
    if img_file.exists():
        return str(img_file)
    try:
        page = doc[page_num - 1]
        pix = page.get_pixmap(dpi=150)
        pix.save(str(img_file))
        return str(img_file)
    except Exception as e:
        logger.warning(f"Failed to render page {page_num}: {e}")
        return None

class DocumentLoader:
    def __init__(self, source_dir: Optional[Path] = None):
        self.source_dir = source_dir or settings.DATA_SOURCE_DIR

    def discover_documents(self) -> List[Path]:
        """Discover PDF documents in the source directory."""
        if not self.source_dir.exists():
            logger.error(f"Source directory does not exist: {self.source_dir}")
            return []
        
        pdf_files = sorted(list(self.source_dir.glob("*.pdf")))
        logger.info(f"Discovered {len(pdf_files)} PDF document(s) in {self.source_dir}")
        for pdf in pdf_files:
            logger.info(f" - {pdf.name} ({pdf.stat().st_size:,} bytes)")
        return pdf_files

    def load_document(self, pdf_path: Path, render_images: bool = True) -> List[PageData]:
        """Load and extract pages from a single PDF document efficiently."""
        doc_checksum = compute_file_checksum(pdf_path)
        doc_name = pdf_path.name
        doc_stem = pdf_path.stem
        pages_data: List[PageData] = []
        is_presentation = "presentation" in doc_name.lower()
        is_theme_feature = "theme-feature" in doc_name.lower()

        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logger.error(f"Failed to open PDF {pdf_path}: {e}")
            return []

        logger.info(f"Loading '{doc_name}' ({len(doc)} pages)...")

        for pno in range(len(doc)):
            page_num = pno + 1
            page = doc[pno]
            
            raw_text = page.get_text("text").strip()
            images = page.get_images()
            image_count = len(images)

            # Table extraction:
            # For presentations or pages with table indicators, extract tables
            tables_text = ""
            table_count = 0
            has_table_clues = (
                is_presentation or 
                is_theme_feature or 
                ("table" in raw_text.lower()) or 
                ("\t" in raw_text) or
                ("particulars" in raw_text.lower()) or
                ("rs. in crore" in raw_text.lower())
            )
            if has_table_clues and len(raw_text) < 3000:
                tables_text = extract_tables_from_page(page)
                if tables_text:
                    table_count = tables_text.count("Table ")

            # Visual criteria: presentations, theme feature, or sparse pages with graphics
            has_visuals = is_presentation or is_theme_feature or (image_count > 0 and len(raw_text) < 800)

            image_path = None
            if render_images and (is_presentation or is_theme_feature or (image_count > 0 and len(raw_text) < 500)):
                image_path = render_page_image_if_needed(doc, page_num, doc_stem)

            p_checksum = compute_page_checksum(raw_text, page_num, image_count)

            page_obj = PageData(
                document_name=doc_name,
                doc_checksum=doc_checksum,
                page_number=page_num,
                raw_text=raw_text,
                tables_text=tables_text,
                has_visuals=has_visuals,
                image_count=image_count,
                drawing_count=0,
                table_count=table_count,
                page_checksum=p_checksum,
                image_path=image_path
            )
            pages_data.append(page_obj)

        doc.close()
        logger.info(f"Successfully loaded {len(pages_data)} pages from '{doc_name}'")
        return pages_data
