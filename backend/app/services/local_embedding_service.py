"""
Local embedding service using multilingual e5-base model
Optimized for semantic search in English and Indonesian.
"""
from sentence_transformers import SentenceTransformer
import numpy as np


class LocalEmbeddingService:
    def __init__(self):
        # Load multilingual model for semantic retrieval
        self.model_name = "intfloat/multilingual-e5-base"
        print(f"[EmbeddingService] Loading model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)

    def embed_text(self, text: str):
        """
        Generate embedding for given text using multilingual e5-base model.

        Args:
            text (str): input text or query

        Returns:
            np.ndarray: embedding vector (float64)
        """
        try:
            if not text or not isinstance(text, str):
                print("[EmbeddingService] Invalid text input for embedding.")
                return np.array([])

            # E5 model expects the "query: " prefix for semantic search
            formatted_text = f"query: {text.strip()}"
            embedding = self.model.encode([formatted_text], normalize_embeddings=True)

            # Convert to numpy array float64 for compatibility with PostgreSQL float8[]
            vec = np.array(embedding[0], dtype=np.float64)
            print(f"[EmbeddingService] Embedding generated len={len(vec)} norm={np.linalg.norm(vec):.3f}")
            return vec

        except Exception as e:
            print(f"[EmbeddingService] Error generating embedding: {e}")
            return np.array([])
