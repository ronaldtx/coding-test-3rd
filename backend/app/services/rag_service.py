"""
RAG (Retrieval-Augmented Generation) Service
Handles semantic search and contextual document retrieval
"""
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer, util
import numpy as np
from app.models.document import DocumentChunk

class RAGService:
    """Perform semantic search on document chunks"""

    def __init__(self, db: Session):
        self.db = db
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def search(self, query: str, top_k: int = 5):
        """
        Search for semantically similar chunks to the query.

        Args:
            query (str): User query text
            top_k (int): Number of top results to return

        Returns:
            List of matching document chunks with similarity scores
        """
        # Encode query to embedding
        query_embedding = self.model.encode([query])[0]

        # Fetch document chunks
        chunks = self.db.query(DocumentChunk).all()

        # Prepare embeddings & compute similarities
        chunk_embeddings = np.array([np.array(c.embedding) for c in chunks])
        similarities = util.cos_sim(query_embedding, chunk_embeddings)[0].cpu().numpy()

        # Sort and pick top results
        top_indices = np.argsort(similarities)[::-1][:top_k]
        results = [
            {
                "chunk_id": chunks[i].id,
                "page": chunks[i].page,
                "content": chunks[i].content,
                "score": float(similarities[i])
            }
            for i in top_indices
        ]
        return results
