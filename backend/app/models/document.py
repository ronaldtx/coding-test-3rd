"""
Document database model
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY, DOUBLE_PRECISION
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class Document(Base):
    """Document model"""
    
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    fund_id = Column(Integer, ForeignKey("funds.id"))
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500))
    upload_date = Column(DateTime, default=datetime.utcnow)
    parsing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text)
    
    # Relationships
    fund = relationship("Fund", back_populates="documents")

class DocumentChunk(Base):
    """Store extracted text chunks from documents"""
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    page = Column(Integer)
    content = Column(Text)
    embedding = Column(ARRAY(DOUBLE_PRECISION))

    document = relationship("Document", backref="chunks")


class DocumentTable(Base):
    """Store extracted tables from documents"""
    __tablename__ = "document_tables"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    page = Column(Integer)
    table_data = Column(Text)

    document = relationship("Document", backref="tables")