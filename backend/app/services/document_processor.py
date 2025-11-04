"""
Document processing service using pdfplumber
with automatic DB persistence for tables and text chunks.
"""

from typing import Dict, List, Any
import pdfplumber
import re
import logging
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.document import Document, DocumentChunk, DocumentTable
from app.services.table_parser import TableParser
# from app.services.embedding_service import EmbeddingService
from app.services.local_embedding_service import LocalEmbeddingService

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process PDF documents and extract structured data."""

    def __init__(self, db: Session = None):
        self.table_parser = TableParser()
        self.db = db

    async def process_document(self, file_path: str, document_id: int, fund_id: int):
        """Main entrypoint: extract tables & text, then save results to DB."""
        try:
            if not self.db:
                raise ValueError("Database session (db) is required for persistence.")

            # Mark as processing
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.parsing_status = "processing"
                self.db.commit()

            tables = []
            text_content = []

            # === STEP 1: Extract content ===
            with pdfplumber.open(file_path) as pdf:
                for page_number, page in enumerate(pdf.pages, start=1):
                    parsed_table = self.table_parser.parse_table(page)
                    if parsed_table:
                        table_type = self.table_parser.classify_table(parsed_table)
                        tables.append({
                            "page": page_number,
                            "table": parsed_table,
                            "type": table_type
                        })

                    text = page.extract_text()
                    if text and text.strip():
                        text_content.append({"page": page_number, "text": text})

            # === STEP 2: Chunk text ===
            chunks = self._chunk_text(text_content)

            # === STEP 3: Persist results ===
            self._save_to_db(document_id, tables, chunks)

            # === STEP 4: Mark completed ===
            # embedding_service = EmbeddingService() # for openai
            embedding_service = LocalEmbeddingService() # for local only

            texts = [c["chunk"] for c in chunks]
            if texts:
                embeddings = await embedding_service.generate_embeddings(texts)
                self._save_embeddings(document_id, embeddings)

            # === STEP 5: Mark completed ===
            document.parsing_status = "completed"
            document.error_message = None
            self.db.commit()

            logger.info(f"Document {document_id} processed successfully with {len(tables)} tables and {len(chunks)} chunks.")

        except Exception as e:
            logger.exception(f"Error processing document {document_id}: {e}")
            if self.db:
                document = self.db.query(Document).filter(Document.id == document_id).first()
                if document:
                    document.parsing_status = "failed"
                    document.error_message = str(e)
                    self.db.commit()

    # -------------------------------------------------------------------------
    # Helper: Save extracted data to DB
    # -------------------------------------------------------------------------
    def _save_to_db(self, document_id: int, tables: List[Dict[str, Any]], chunks: List[Dict[str, Any]]):
        """Save extracted tables and text chunks to their respective tables."""
        # Save tables
        for t in tables:
            record = DocumentTable(
                document_id=document_id,
                page=t["page"],
                table_data=str(t["table"])  # you may convert to JSON if needed
            )
            self.db.add(record)

        # Save text chunks
        for c in chunks:
            record = DocumentChunk(
                document_id=document_id,
                page=c["metadata"]["page"],
                content=c["chunk"]
            )
            self.db.add(record)

        self.db.commit()


    # -------------------------------------------------------------------------
    # Helper: Save Embedding
    # -------------------------------------------------------------------------
    def _save_embeddings(self, document_id: int, embeddings: List[List[float]]):
        """Save generated embeddings into document_chunks table"""
        chunks = self.db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()

        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding

        self.db.commit()


    # -------------------------------------------------------------------------
    # Helper: Text chunking
    # -------------------------------------------------------------------------
    def _chunk_text(self, text_content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Split text into smaller chunks for vectorization."""
        chunks = []
        chunk_size = 500
        overlap = 50
        sentence_splitter = re.compile(r'(?<=[.!?])\s+')

        for page in text_content:
            sentences = sentence_splitter.split(page["text"])
            buffer = ""
            for sentence in sentences:
                if len(buffer) + len(sentence) < chunk_size:
                    buffer += sentence + " "
                else:
                    chunks.append({
                        "chunk": buffer.strip(),
                        "metadata": {
                            "page": page["page"],
                            "chunk_size": len(buffer),
                            "type": "text"
                        }
                    })
                    buffer = sentence[-overlap:] + " "
            if buffer.strip():
                chunks.append({
                    "chunk": buffer.strip(),
                    "metadata": {
                        "page": page["page"],
                        "chunk_size": len(buffer),
                        "type": "text"
                    }
                })

        return chunks
