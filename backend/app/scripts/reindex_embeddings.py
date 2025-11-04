"""
Re-generate all embeddings in document_chunks using the new E5-base model
"""
import asyncio
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.core.config import settings
from app.models.document import DocumentChunk
from app.models.transaction import CapitalCall
from app.models.transaction import Distribution
from app.models.transaction import Adjustment
from app.models.fund import Fund

from app.services.local_embedding_service import LocalEmbeddingService


async def reindex_all_embeddings():
    print("Start re-embedding process all document_chunks...")
    
    # Setup DB session
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    embedding_service = LocalEmbeddingService()

    # get all chunks
    chunks = db.query(DocumentChunk).all()
    print(f"Total chunks: {len(chunks)}")

    updated = 0

    for chunk in chunks:
        if not chunk.content:
            continue
        
        # Generate new embedding
        embedding = embedding_service.embed_text(chunk.content)
        if embedding is not None and len(embedding) > 0:
            chunk.embedding = embedding.tolist()
            updated += 1

        if updated % 10 == 0:
            db.commit()
            print(f"Progress: {updated}/{len(chunks)} fixing chunks ...")

    # Commit all changes
    db.commit()
    db.close()

    print(f"Re-embedding done. Total fixed: {updated}")


if __name__ == "__main__":
    asyncio.run(reindex_all_embeddings())
