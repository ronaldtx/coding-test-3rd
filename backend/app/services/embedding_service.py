"""
Embedding service using OpenAI API
"""
import os
import openai
from typing import List

openai.api_key = os.getenv("OPENAI_API_KEY")

class EmbeddingService:
    """Handles text embedding generation"""

    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts
        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Call OpenAI embedding API
        response = await openai.embeddings.create(
            model=self.model,
            input=texts
        )

        embeddings = [item.embedding for item in response.data]
        return embeddings
