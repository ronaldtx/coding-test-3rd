"""
Query engine service for RAG-based question answering
"""
import os
from typing import Dict, Any, List, Optional
import time
from langchain_openai import ChatOpenAI
from langchain_community.llms import Ollama
from langchain.prompts import ChatPromptTemplate
from app.core.config import settings
from app.services.vector_store import VectorStore
from app.services.metrics_calculator import MetricsCalculator
from sqlalchemy.orm import Session


class QueryEngine:
    """RAG-based query engine for fund analysis"""
    
    def __init__(self, db: Session):
        self.db = db
        self.vector_store = VectorStore(db=db)
        self.metrics_calculator = MetricsCalculator(db)
        self.llm = self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LLM"""
        if settings.OPENAI_API_KEY:
            return ChatOpenAI(
                model=settings.OPENAI_MODEL,
                temperature=0,
                openai_api_key=settings.OPENAI_API_KEY
            )
        else:
            # Fallback to local LLM
            return Ollama(
                base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
                model=os.getenv("OLLAMA_MODEL", "llama3.2")
            )
            # return Ollama(model="llama2")
    
    async def process_query(
            self,
            query: str,
            fund_id: Optional[int] = None,
            conversation_history: List[Dict[str, str]] = None
        ) -> Dict[str, Any]:
        """Process a user query using RAG pipeline"""
        start_time = time.time()

        # Step 1. Classify query intent
        intent = await self._classify_intent(query)

        # Step 2. Retrieve relevant chunks from pgvector
        filter_metadata = {"fund_id": fund_id} if fund_id else None
        relevant_docs = await self.vector_store.similarity_search(
            query=query,
            k=settings.TOP_K_RESULTS,
            filter_metadata=filter_metadata
        )

        # Step 3. Calculate fund metrics if relevant
        metrics = None
        if intent == "calculation" and fund_id:
            metrics = self.metrics_calculator.calculate_all_metrics(fund_id)

        # Step 4. Generate final answer using context
        answer = await self._generate_response(
            query=query,
            context=relevant_docs,
            metrics=metrics,
            conversation_history=conversation_history or []
        )

        processing_time = round(time.time() - start_time, 2)

        # Step 5. Return structured response
        return {
            "answer": answer,
            "sources": [
                {
                    "content": doc["content"],
                    "page": doc.get("page"),
                    "score": doc.get("score"),
                    "metadata": {
                        "document_id": doc.get("document_id"),
                        "source_type": "database",
                        "retrieved_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
                for doc in relevant_docs
            ],
            "metrics": metrics,
            "processing_time": processing_time
        }

    
    async def _classify_intent(self, query: str) -> str:
        """
        Classify query intent
        
        Returns:
            'calculation', 'definition', 'retrieval', or 'general'
        """
        query_lower = query.lower()
        
        # Calculation keywords
        calc_keywords = [
            "calculate", "what is the", "current", "dpi", "irr", "tvpi", 
            "rvpi", "pic", "paid-in capital", "return", "performance"
        ]
        if any(keyword in query_lower for keyword in calc_keywords):
            return "calculation"
        
        # Definition keywords
        def_keywords = [
            "what does", "mean", "define", "explain", "definition", 
            "what is a", "what are"
        ]
        if any(keyword in query_lower for keyword in def_keywords):
            return "definition"
        
        # Retrieval keywords
        ret_keywords = [
            "show me", "list", "all", "find", "search", "when", 
            "how many", "which"
        ]
        if any(keyword in query_lower for keyword in ret_keywords):
            return "retrieval"
        
        return "general"
    
    async def _generate_response(
            self,
            query: str,
            context: List[Dict[str, Any]],
            metrics: Optional[Dict[str, Any]],
            conversation_history: List[Dict[str, str]]
        ) -> str:
        """Generate response using local LLM (Ollama)"""
        context_text = "\n\n".join(
            [f"[Page {doc.get('page', '?')}]\n{doc['content']}" for doc in context]
        )

        prompt = f"""
You are a fund analysis assistant with access to financial documents.

Use ONLY the following context extracted from PDF documents:
{context_text}

Metrics (if available): {metrics}

Previous conversation (if any): {conversation_history}

Question: {query}

Answer clearly and concisely based only on the provided context.
If the context doesn't have enough information, say so explicitly.
"""

        try:
            response = self.llm.invoke(prompt)
            if hasattr(response, "content"):
                return response.content
            return str(response)
        except Exception as e:
            return f"Error generating response: {str(e)}"