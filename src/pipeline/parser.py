"""Document parsing module for industrial datasets (TXT, PDF, DOCX, CSV)."""

from pathlib import Path
import pandas as pd
import pdfplumber
import docx
from loguru import logger


def parse_txt(file_path: Path) -> str:
    """Parse text files."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error parsing TXT file {file_path}: {e}")
        raise e


def parse_pdf(file_path: Path) -> str:
    """Parse PDF files using pdfplumber, falling back to Tesseract OCR for scanned pages."""
    try:
        text_pages = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text and len(page_text.strip()) > 10:
                    text_pages.append(page_text)
                else:
                    logger.warning(f"Page {i+1} of PDF {file_path} appears to be scanned/empty. Attempting OCR fallback...")
                    try:
                        # Extract page image and run OCR
                        page_image = page.to_image(resolution=150).original
                        import pytesseract
                        ocr_text = pytesseract.image_to_string(page_image)
                        if ocr_text and len(ocr_text.strip()) > 5:
                            text_pages.append(ocr_text)
                            logger.info(f"Successfully extracted {len(ocr_text)} chars from page {i+1} using Tesseract OCR fallback.")
                        else:
                            text_pages.append("")
                    except Exception as ocr_err:
                        logger.warning(f"OCR failed for page {i+1}: {ocr_err}. Is Tesseract binary installed?")
                        text_pages.append("")
        
        full_text = "\n\n".join(text_pages).strip()
        if not full_text:
            logger.error(f"Failed to extract any text from PDF {file_path} (parsed 0 characters).")
        return full_text
    except Exception as e:
        logger.error(f"Error parsing PDF file {file_path}: {e}")
        raise e


def parse_docx(file_path: Path) -> str:
    """Parse DOCX files using python-docx."""
    try:
        doc = docx.Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except Exception as e:
        logger.error(f"Error parsing DOCX file {file_path}: {e}")
        raise e


def parse_csv(file_path: Path) -> list[dict]:
    """Parse CSV files row-by-row into self-describing text records.

    Each row is represented as a dictionary:
    {
        "text": "Formatted string with all row fields",
        "metadata": {
            "doc_id": "filename.csv",
            "record_id": "WO-1001",
            "record_type": "csv_row",
            "equipment_tag": "EQ-1001",
            "regulation_ref": "OISD-116",
            ...
        }
    }
    """
    try:
        df = pd.read_csv(file_path)
        df = df.fillna("")
        
        # Identify key identifier column (e.g. work_order_id, permit_id, etc.)
        id_col = None
        for col in df.columns:
            if "id" in col.lower():
                id_col = col
                break

        records = []
        record_type = file_path.stem.replace("_", " ").title() # e.g. "Work Orders"
        
        for idx, row in df.iterrows():
            row_id = str(row[id_col]).strip() if id_col else f"{file_path.stem}_{idx}"
            
            # Format row data as descriptive lines
            lines = [f"[{record_type} Record {row_id}]"]
            for col in df.columns:
                val = str(row[col]).strip()
                if val:
                    # Format column names nicely: e.g. "equipment_tag" -> "Equipment Tag"
                    formatted_col = col.replace("_", " ").title()
                    lines.append(f"{formatted_col}: {val}")
            
            row_text = "\n".join(lines)
            
            # Construct metadata dictionary
            metadata = {
                "doc_id": file_path.name,
                "record_id": row_id,
                "record_type": file_path.stem,
                "chunk_index": idx
            }
            
            # Extract common taxonomy fields into metadata for filtering/linking
            for col in ["equipment_tag", "regulation_ref", "plant", "status", "priority", "incident_type", "permit_type"]:
                if col in row and str(row[col]).strip():
                    metadata[col] = str(row[col]).strip()
            
            records.append({
                "id": f"{file_path.stem}_{row_id}",
                "text": row_text,
                "metadata": metadata
            })
            
        logger.info(f"Parsed CSV '{file_path.name}': {len(records)} records extracted")
        return records
    except Exception as e:
        logger.error(f"Error parsing CSV file {file_path}: {e}")
        raise e


def parse_file(file_path: Path) -> list[dict]:
    """Parse any supported file based on extension.

    Returns:
        List of dicts: [{"text": str, "metadata": dict}]
    """
    suffix = file_path.suffix.lower()
    filename = file_path.name

    if suffix == ".csv":
        return parse_csv(file_path)
    
    # Non-CSV files return a single record that will be chunked later
    metadata = {
        "doc_id": filename,
        "record_id": filename,
        "record_type": suffix.lstrip("."),
        "chunk_index": 0
    }
    
    if suffix == ".txt":
        text = parse_txt(file_path)
    elif suffix == ".pdf":
        text = parse_pdf(file_path)
    elif suffix == ".docx":
        text = parse_docx(file_path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    return [{"text": text, "metadata": metadata}]
