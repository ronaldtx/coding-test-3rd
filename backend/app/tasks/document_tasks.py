import traceback
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.document import Document, DocumentTable
from app.services.table_parser import TableParser

def process_document_task(document_id: int, file_path: str, fund_id: int):
    db: Session = SessionLocal()
    try:
        # Update status to "processing"
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            print(f"Document {document_id} not found")
            return

        doc.parsing_status = "processing"
        db.commit()

        print(f"Processing document {document_id}: {file_path}")

        parser = TableParser()
        tables = parser.parse(file_path)

        print(f"Extracted {len(tables)} tables from {file_path}")

        for t in tables:
            db_table = DocumentTable(
                document_id=document_id,
                page=t["page"],
                table_data=str(t["data"])
            )
            db.add(db_table)

        # Update status to "completed"
        doc.parsing_status = "completed"
        db.commit()

        print(f"Document {document_id} processed successfully.")

    except Exception as e:
        print(f"Error processing document {document_id}: {e}")
        traceback.print_exc()
        # Update status to failed
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.parsing_status = "failed"
            db.commit()
    finally:
        db.close()
