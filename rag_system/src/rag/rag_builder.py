# src/rag/rag_builder.py - simplified quick version
from typing import List, Dict, Any, Optional
from pathlib import Path
from ..core.rag_base import RAGInstance
from ..utils.config import config
from ..utils.logger import setup_logger
from ..utils.document_loader import DocumentLoader, DocumentProcessor

logger = setup_logger(__name__)

class RAGBuilder:
    """RAG instance builder - quick version"""

    def __init__(self):
        self.rag_configs = config.get('rag_instances', {})
        self.instances = {}
        self.doc_loader = DocumentLoader()
        self.doc_processor = DocumentProcessor()
        logger.info(f"RAGBuilder initialized, found {len(self.rag_configs)} RAG configurations")

    def build_all(self, load_documents: bool = True, aircraft_type: Optional[str] = None) -> Dict[str, RAGInstance]:
        """Build all RAG instances"""
        if load_documents:
            if aircraft_type:
                all_docs = self.doc_loader.load_documents_by_aircraft(aircraft_type)
            else:
                all_docs = self.doc_loader.load_all_documents()
        else:
            all_docs = {}

        for name, rag_config in self.rag_configs.items():
            try:
                instance = RAGInstance(name)

                if load_documents and name in all_docs and all_docs[name]:
                    processed_docs = self._process_documents(all_docs[name])
                    if processed_docs:
                        instance.add_documents(processed_docs)
                        logger.info(f"RAG {name}: added {len(processed_docs)} documents")

                self.instances[name] = instance
                logger.info(f"RAG instance {name} built successfully, document count: {instance.collection.count()}")

            except Exception as e:
                logger.error(f"RAG instance {name} build failed: {str(e)}")

        return self.instances

    def _process_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process documents - simple chunking"""
        processed = []

        for doc in documents:
            text = doc.get('text', '')
            if not text or len(text) < 10:
                continue

            # Only chunk very large documents
            if len(text) > 3000:
                chunks = self.doc_processor.chunk_document(text, chunk_size=800, overlap=100)
                for i, chunk in enumerate(chunks):
                    if len(chunk) > 50:
                        chunk_doc = {
                            'id': f"{doc['id']}_chunk_{i:03d}",
                            'text': chunk,
                            'metadata': {
                                **doc.get('metadata', {}),
                                'chunk_index': i,
                                'total_chunks': len(chunks)
                            }
                        }
                        processed.append(chunk_doc)
            else:
                processed.append(doc)

        return processed

    def get_instance(self, name: str) -> RAGInstance:
        if name not in self.instances:
            self.instances[name] = RAGInstance(name)
        return self.instances[name]

    def build_for_aircraft(self, aircraft_type: str) -> Dict[str, RAGInstance]:
        return self.build_all(load_documents=True, aircraft_type=aircraft_type)
