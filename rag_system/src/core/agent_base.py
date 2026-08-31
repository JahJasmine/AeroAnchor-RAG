# src/core/agent_base.py
from typing import List, Dict, Any, Optional
import asyncio
from ..utils.llm_client import llm_client
from ..utils.logger import setup_logger
from .rag_base import RAGInstance

logger = setup_logger(__name__)

class BaseAgent:
    """Agent base class - enhanced error handling"""

    def __init__(self, name: str, rag_instances: List[RAGInstance], system_prompt: str):
        self.name = name
        self.rag_instances = {rag.name: rag for rag in rag_instances}
        self.system_prompt = system_prompt
        self.enabled = True
        logger.info(f"Agent {self.name} initialized, bound RAGs: {list(self.rag_instances.keys())}")

    async def process(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Main method for processing queries - enhanced error handling"""
        if not self.enabled:
            return {'status': 'disabled', 'agent': self.name}

        try:
            # 1. Retrieve documents
            retrieved_docs = await self._retrieve_all(query)

            # 2. Build messages
            messages = self._build_messages(query, context, retrieved_docs)

            # 3. Call LLM (with retry)
            try:
                response = await asyncio.wait_for(
                    llm_client.chat_completion(messages),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.error(f"Agent {self.name} LLM call timed out")
                return {
                    'agent': self.name,
                    'status': 'error',
                    'error': 'LLM timeout'
                }

            logger.info(f"Agent {self.name} processing complete")

            return {
                'agent': self.name,
                'status': 'success',
                'response': response,
                'retrieved_docs': retrieved_docs,
                'rag_sources': list(self.rag_instances.keys())
            }

        except Exception as e:
            logger.error(f"Agent {self.name} processing failed: {str(e)}")
            return {
                'agent': self.name,
                'status': 'error',
                'error': str(e)
            }

    async def _retrieve_all(self, query: str) -> Dict[str, List[Dict]]:
        """Retrieve from all bound RAG instances in parallel"""
        tasks = []
        for rag_name, rag_instance in self.rag_instances.items():
            tasks.append(self._retrieve_single(rag_name, rag_instance, query))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        merged = {}
        for result in results:
            if isinstance(result, Exception):
                continue
            rag_name, docs = result
            merged[rag_name] = docs

        return merged

    async def _retrieve_single(self, rag_name: str, rag_instance: RAGInstance, query: str) -> tuple:
        """Retrieve from a single RAG"""
        try:
            docs = rag_instance.query(query, top_k=3)
            return (rag_name, docs)
        except Exception as e:
            logger.warning(f"RAG {rag_name} retrieval failed: {e}")
            return (rag_name, [])

    def _build_messages(self, query: str, context: Dict, retrieved_docs: Dict) -> List[Dict]:
        """Build LLM messages"""
        context_str = ""
        if context:
            context_str = f"\nFlight Context: {context}\n"

        docs_str = ""
        for rag_name, docs in retrieved_docs.items():
            if docs:
                docs_str += f"\n[{rag_name}] Retrieved Documents:\n"
                for i, doc in enumerate(docs[:3], 1):
                    docs_str += f"  {i}. {doc['text'][:300]}...\n"

        if not docs_str:
            docs_str = "\nNo relevant documents retrieved.\n"

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""
User Query: {query}
{context_str}

Reference Documents:
{docs_str}

Please provide a professional, specific, and well-grounded explanation in English based on the reference materials above (do not output option letters or numbers; directly explain the principles and key points).
"""}
        ]

        return messages
