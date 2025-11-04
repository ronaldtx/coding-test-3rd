"""
Vector store service using pgvector (PostgreSQL extension)

TODO: Implement vector storage using pgvector
- Create embeddings table in PostgreSQL
- Store document chunks with vector embeddings
- Implement similarity search using pgvector operators
- Handle metadata filtering
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import numpy as np
from app.services.local_embedding_service import LocalEmbeddingService


class VectorStore:
    """pgvector-based vector store for document chunks"""

    def __init__(self, db: Session = None):
        self.db = db
        self.embedding_service = LocalEmbeddingService()

    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using cosine similarity via pgvector (manual float8[] version)
        with full debug logging.
        """
        try:
            # Step 1: Generate embedding for the query
            query_embedding = self.embedding_service.embed_text(query)

            if query_embedding is None or len(query_embedding) == 0:
                return []

            query_vec = np.array(query_embedding, dtype=np.float64)

            # Step 2: Build WHERE clause (fund_id → document_id mapping)
            where_clause = ""
            params = {}
            if filter_metadata:
                if "fund_id" in filter_metadata:
                    where_clause = "WHERE document_id = :doc_id"
                    params["doc_id"] = filter_metadata["fund_id"]
                elif "document_id" in filter_metadata:
                    where_clause = "WHERE document_id = :doc_id"
                    params["doc_id"] = filter_metadata["document_id"]

            # Step 3: Query chunks from DB
            fetch_sql = text(f"""
                SELECT id, document_id, page, content, embedding
                FROM document_chunks
                {where_clause}
            """)

            rows = self.db.execute(fetch_sql, params).fetchall()

            if not rows:
                return []

            results = []

            # Step 4: Process each row
            for idx, row in enumerate(rows):
                embedding_value = row.embedding

                if embedding_value is None:
                    continue

                # Handle memoryview (psycopg2 behavior)
                if isinstance(embedding_value, memoryview):
                    try:
                        embedding_value = np.frombuffer(embedding_value, dtype=np.float64).tolist()
                    except Exception as err:
                        continue

                # Handle string literal (misalnya "{0.1,0.2,0.3}")
                elif isinstance(embedding_value, str):
                    try:
                        embedding_value = [
                            float(x) for x in embedding_value.strip("{}").split(",") if x
                        ]
                    except Exception as err:
                        continue

                # Handle nested list [[...]]
                elif isinstance(embedding_value, list):
                    if len(embedding_value) == 1 and isinstance(embedding_value[0], list):
                        embedding_value = embedding_value[0]

                # Convert to numpy
                try:
                    doc_vec = np.array(embedding_value, dtype=np.float64)
                except Exception as conv_err:
                    continue

                if doc_vec.size == 0 or np.linalg.norm(doc_vec) == 0:
                    continue

                # Step 5: Cosine similarity
                try:
                    similarity = float(np.dot(query_vec, doc_vec) /
                                       (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec)))
                except Exception as err:
                    continue


                # Step 6: Apply threshold
                if similarity >= 0.3:
                    results.append({
                        "id": row.id,
                        "document_id": row.document_id,
                        "page": row.page,
                        "content": row.content,
                        "score": round(similarity, 3)
                    })

            # Step 7: Sort results
            results.sort(key=lambda x: x["score"], reverse=True)

            return results[:k]

        except Exception as e:
            print(f"[ERROR] Terjadi kesalahan di similarity_search: {e}")
            return []
