"""
Document API endpoints
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import pdfplumber
import os
import io, re
import shutil
from datetime import datetime
from app.db.session import get_db
from app.models.document import Document
from app.models.transaction import CapitalCall
from app.models.transaction import Distribution
from app.models.transaction import Adjustment
from app.schemas.document import (
    Document as DocumentSchema,
    DocumentUploadResponse,
    DocumentStatus,
    DocumentTable
)
from app.services.document_processor import DocumentProcessor
from app.services.table_parser import TableParser
from app.core.config import settings
from app.tasks.document_tasks import process_document_task

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    fund_id: int = None,
    db: Session = Depends(get_db)
):
    """Upload and process a PDF document"""
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Validate file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE} bytes"
        )

    # Create upload directory if it doesn't exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Save file
    pdf_bytes = await file.read()
    if not pdf_bytes or len(pdf_bytes) < 100:
        raise HTTPException(status_code=400, detail="Uploaded file is empty or invalid")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    # save pdf to disk
    with open(file_path, "wb") as f:
        f.write(pdf_bytes)

    # open PDF from memory bytes
    try:
        pdf = pdfplumber.open(io.BytesIO(pdf_bytes))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal membaca PDF: {e}")

    text_pages = []
    for i, page in enumerate(pdf.pages):
        page_text = page.extract_text()
        if page_text:
            text_pages.append(page_text)
        else:
            print(f"[WARNING] Page {i+1} empty or just images.")
    pdf.close()

    if not text_pages:
        raise HTTPException(status_code=400, detail="No text can be extraced from PDF.")

    text = "\n".join(text_pages)
    # Create document record
    document = Document(
        fund_id=fund_id,
        file_name=file.filename,
        file_path=file_path,
        parsing_status="pending"
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Start background processing
    background_tasks.add_task(
        DocumentProcessor(db).process_document,
        file_path,
        document.id,
        fund_id or 1  # Default fund_id if not provided
    )

    capital_calls = re.findall(r"(\d{4}-\d{2}-\d{2}).*?Call\s\d.*?\$([\d,]+)", text)
    for date_str, amount_str in capital_calls:
        amount = float(amount_str.replace(",", ""))
        db.add(CapitalCall(
            fund_id=fund_id,
            call_date=date_str,
            call_type="Capital Call",
            amount=amount,
            description="Imported from PDF",
            created_at=datetime.utcnow()
        ))

    distributions = re.findall(r"(\d{4}-\d{2}-\d{2}).*?(Income|Return of Capital).*?\$([\d,]+)", text)
    for date_str, dtype, amount_str in distributions:
        amount = float(amount_str.replace(",", ""))
        db.add(Distribution(
            fund_id=fund_id,
            distribution_date=date_str,
            distribution_type=dtype,
            is_recallable=False,
            amount=amount,
            description="Imported from PDF",
            created_at=datetime.utcnow()
        ))

    adjustments = re.findall(r"(\d{4}-\d{2}-\d{2}).*?(Adjustment).*?\$?(-?[\d,]+)", text)
    for date_str, atype, amount_str in adjustments:
        amount = float(amount_str.replace(",", ""))
        db.add(Adjustment(
            fund_id=fund_id,
            adjustment_date=date_str,
            adjustment_type=atype,
            amount=amount,
            description="Imported from PDF",
            created_at=datetime.utcnow()
        ))

    db.commit()


    return DocumentUploadResponse(
        document_id=document.id,
        task_id=None,
        status="pending",
        message="Document uploaded successfully. Processing started."
    )


async def process_document_task(document_id: int, file_path: str, fund_id: int):
    """Background task to process document"""
    from app.db.session import SessionLocal
    
    db = SessionLocal()
    
    try:
        # Update status to processing
        document = db.query(Document).filter(Document.id == document_id).first()
        document.parsing_status = "processing"
        db.commit()
        
        # Process document
        processor = DocumentProcessor()
        result = await processor.process_document(file_path, document_id, fund_id)
        
        # Update status
        document.parsing_status = result["status"]
        if result["status"] == "failed":
            document.error_message = result.get("error")
        db.commit()
        
    except Exception as e:
        document = db.query(Document).filter(Document.id == document_id).first()
        document.parsing_status = "failed"
        document.error_message = str(e)
        db.commit()
    finally:
        db.close()


@router.get("/{document_id}/status", response_model=DocumentStatus)
async def get_document_status(document_id: int, db: Session = Depends(get_db)):
    """Get document parsing status"""
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentStatus(
        document_id=document.id,
        status=document.parsing_status,
        error_message=document.error_message
    )


@router.get("/{document_id}", response_model=DocumentSchema)
async def get_document(document_id: int, db: Session = Depends(get_db)):
    """Get document details"""
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return document


@router.get("/", response_model=List[DocumentSchema])
async def list_documents(
    fund_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all documents"""
    query = db.query(Document)
    
    if fund_id:
        query = query.filter(Document.fund_id == fund_id)
    
    documents = query.offset(skip).limit(limit).all()
    return documents


@router.delete("/{document_id}")
async def delete_document(document_id: int, db: Session = Depends(get_db)):
    """Delete a document"""
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file
    if document.file_path and os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    # Delete database record
    db.delete(document)
    db.commit()
    
    return {"message": "Document deleted successfully"}
