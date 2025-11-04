import pdfplumber
from app.models.document import DocumentChunk, DocumentTable
from sqlalchemy.orm import Session
import json

def parse_pdf(db: Session, document_id: int, file_path: str):
    """Extract text & table from PDF then save to DB"""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # --- Extract text ---
                text = page.extract_text()
                if text:
                    chunk = DocumentChunk(
                        document_id=document_id,
                        page=page_num,
                        content=text
                    )
                    db.add(chunk)

                # --- Extract table ---
                tables = page.extract_tables()
                for tbl in tables:
                    if tbl:
                        table_json = json.dumps(tbl)
                        table_record = DocumentTable(
                            document_id=document_id,
                            page=page_num,
                            table_data=table_json
                        )
                        db.add(table_record)

        db.commit()
        return True

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Fail to parse {file_path}: {e}")
        return False
