"""
Document Pydantic schemas
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List


class DocumentBase(BaseModel):
    """Base document schema"""
    file_name: str
    fund_id: Optional[int] = None


class DocumentCreate(DocumentBase):
    """Document creation schema"""
    file_path: str


class DocumentUpdate(BaseModel):
    """Document update schema"""
    parsing_status: Optional[str] = None
    error_message: Optional[str] = None


class Document(DocumentBase):
    """Document response schema"""
    id: int
    file_path: Optional[str] = None
    upload_date: datetime
    parsing_status: str
    error_message: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class DocumentStatus(BaseModel):
    """Document parsing status"""
    document_id: int
    status: str
    progress: Optional[float] = None
    error_message: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    """Document upload response"""
    document_id: int
    task_id: Optional[str] = None
    status: str
    message: str


class DocumentTable(BaseModel):
    """Parsed table schema"""
    id: int
    document_id: int
    table_json: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)