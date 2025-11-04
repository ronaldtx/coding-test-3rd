import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.document import Document
from app.services.document_parser import parse_pdf
from datetime import datetime

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = "uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload file PDF lalu parsing"""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Hanya file PDF yang didukung.")

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Save metadata
    doc = Document(
        file_name=file.filename,
        file_path=file_path,
        upload_date=datetime.utcnow(),
        parsing_status="processing"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Parsing file
    success = parse_pdf(db, doc.id, file_path)
    doc.parsing_status = "completed" if success else "failed"
    db.commit()

    return {"document_id": doc.id, "status": doc.parsing_status}
