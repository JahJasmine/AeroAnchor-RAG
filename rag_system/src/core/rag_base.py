# src/core/rag_base.py - use global cached model
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from pathlib import Path
import warnings
import torch
import os
from ..utils.config import config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# ============================================
# Global model cache - load from local
# ============================================
_global_embedding_model = None
_global_device = None

def get_embedding_model():
    """Get the globally cached embedding model - load from local cache"""
    global _global_embedding_model, _global_device

    if _global_embedding_model is not None:
        return _global_embedding_model, _global_device

    # Set the cache directory (models have been downloaded here)
    cache_dir = '/root/.cache/huggingface/hub'
    os.makedirs(cache_dir, exist_ok=True)

    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
    os.environ['TRANSFORMERS_CACHE'] = cache_dir
    os.environ['HF_HUB_CACHE'] = cache_dir

    device = 'cpu'  # Force CPU to avoid CUDA errors
    model_name = config.get('llm.embedding_model', 'paraphrase-MiniLM-L3-v2')

    try:
        from sentence_transformers import SentenceTransformer

        logger.info(f"Loading model from cache: {model_name} (using CPU, stable mode)")
        logger.info(f"Cache directory: {cache_dir}")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _global_embedding_model = SentenceTransformer(
                model_name,
                device=device,
                cache_folder=cache_dir
            )
            _global_device = device
            logger.info(f"✅ Model loaded successfully (device: {device})")

            test_emb = _global_embedding_model.encode(["test"], convert_to_numpy=True)
            logger.info(f"Model test successful, embedding dimension: {test_emb.shape}")

            return _global_embedding_model, _global_device

    except Exception as e:
        logger.error(f"Model loading failed: {e}")
        logger.info("Will use simple random embedding (limited functionality)")
        _global_embedding_model = None
        _global_device = device
        return None, device

# GPU configuration
def configure_gpu():
    if torch.cuda.is_available():
        try:
            torch.cuda.set_per_process_memory_fraction(0.85)
            torch.backends.cudnn.benchmark = True
            total_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
            logger.info(f"GPU: {torch.cuda.get_device_name(0)} ({total_mem:.1f}GB)")
        except Exception as e:
            logger.warning(f"GPU configuration failed: {e}")

configure_gpu()

class RAGInstance:
    """RAG instance - uses the global cached model"""

    def __init__(self, name: str, persist_directory: Optional[str] = None, aircraft_type: Optional[str] = None):
        self.name = name
        self.aircraft_type = aircraft_type or "general"

        base_persist = persist_directory or config.get('chromadb.persist_directory')
        if self.aircraft_type != "general":
            self.persist_directory = Path(base_persist) / self.aircraft_type / name
        else:
            self.persist_directory = Path(base_persist) / name

        self.persist_directory = str(self.persist_directory)
        self.collection_name = f"{config.get('chromadb.collection_prefix')}{name}_{self.aircraft_type}"

        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        # Use the global model (loaded only once)
        self.embedding_model, self.device = get_embedding_model()

        if self.embedding_model:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self._embedding_function
            )
        else:
            logger.warning(f"RAG {self.name}: no embedding model, using random vectors")
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name
            )

        logger.info(f"RAG {self.name} initialized, document count: {self.collection.count()}")

    def _embedding_function(self, texts: List[str]) -> List[List[float]]:
        """Embedding function - uses the global cached model"""
        if self.embedding_model:
            try:
                batch_size = 64
                all_embeddings = []

                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i+batch_size]
                    try:
                        embeddings = self.embedding_model.encode(
                            batch,
                            convert_to_numpy=True,
                            show_progress_bar=False
                        )
                        all_embeddings.append(embeddings)
                    except RuntimeError as e:
                        if "CUDA" in str(e):
                            logger.warning(f"CUDA error, switching to CPU: {e}")
                            self.embedding_model.to('cpu')
                            embeddings = self.embedding_model.encode(
                                batch,
                                convert_to_numpy=True,
                                show_progress_bar=False
                            )
                            all_embeddings.append(embeddings)
                            if torch.cuda.is_available():
                                self.embedding_model.to('cuda')
                        else:
                            raise

                import numpy as np
                if len(all_embeddings) > 1:
                    result = np.vstack(all_embeddings)
                else:
                    result = all_embeddings[0]
                return result.tolist()

            except Exception as e:
                logger.error(f"Embedding encoding failed: {e}")
                try:
                    self.embedding_model.to('cpu')
                    embeddings = self.embedding_model.encode(
                        texts,
                        convert_to_numpy=True,
                        show_progress_bar=False
                    )
                    return embeddings.tolist()
                except:
                    import numpy as np
                    return np.random.randn(len(texts), 384).tolist()
        else:
            import numpy as np
            return np.random.randn(len(texts), 384).tolist()

    def add_documents(self, documents: List[Dict[str, Any]]):
        """Add documents - with deduplication check"""
        if not documents:
            return

        import hashlib
        import time

        ids = []
        texts = []
        metadatas = []

        for i, doc in enumerate(documents):
            doc_id = doc.get('id')
            if not doc_id:
                content = doc.get('text', '')[:100]
                hash_val = hashlib.md5(f"{content}_{time.time()}_{i}".encode('utf-8')).hexdigest()[:12]
                doc_id = f"{self.name}_{self.aircraft_type}_{i}_{hash_val}"
            else:
                doc_id = f"{doc_id}_{int(time.time()*1000)}_{i}"

            ids.append(doc_id)
            texts.append(doc.get('text', ''))

            meta = doc.get('metadata', {})
            meta['aircraft_type'] = self.aircraft_type
            meta['rag_name'] = self.name
            metadatas.append(meta)

        # Check which IDs already exist
        existing_ids = set()
        try:
            batch_size = 1000
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i:i+batch_size]
                try:
                    existing = self.collection.get(ids=batch_ids)
                    if existing and existing['ids']:
                        existing_ids.update(existing['ids'])
                except:
                    pass
        except Exception as e:
            logger.warning(f"Failed to check duplicate IDs: {e}")

        # Filter out new documents
        new_ids = []
        new_texts = []
        new_metadatas = []
        for i, doc_id in enumerate(ids):
            if doc_id not in existing_ids:
                new_ids.append(doc_id)
                new_texts.append(texts[i])
                new_metadatas.append(metadatas[i])

        if not new_ids:
            logger.info(f"RAG {self.name}: no new documents to add ({len(existing_ids)} already exist)")
            return

        try:
            self.collection.add(
                documents=new_texts,
                metadatas=new_metadatas,
                ids=new_ids
            )
            logger.info(f"RAG {self.name}: ✅ added {len(new_ids)} new documents (skipped {len(existing_ids)} existing)")
        except Exception as e:
            logger.warning(f"Batch add failed: {e}")
            success_count = 0
            for i, doc_id in enumerate(new_ids):
                try:
                    self.collection.add(
                        documents=[new_texts[i]],
                        metadatas=[new_metadatas[i]],
                        ids=[f"{doc_id}_{i}_{int(time.time()*1000)}"]
                    )
                    success_count += 1
                except Exception as single_error:
                    logger.debug(f"Single-item add failed: {single_error}")
            logger.info(f"RAG {self.name}: item-by-item add complete, succeeded {success_count}/{len(new_ids)}")

    def query(self, query_text: str, top_k: int = 5, filter_aircraft: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve relevant documents"""
        try:
            where_filter = None
            if filter_aircraft:
                where_filter = {"aircraft_type": filter_aircraft}

            top_k = min(top_k, 5)

            results = self.collection.query(
                query_texts=[query_text],
                n_results=top_k,
                where=where_filter
            )

            documents = []
            if results and results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    doc = {
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else None,
                        'id': results['ids'][0][i] if results['ids'] else None
                    }
                    documents.append(doc)

            return documents

        except Exception as e:
            logger.error(f"RAG {self.name}: query failed - {str(e)}")
            return []

    def get_status(self) -> Dict[str, Any]:
        """Get RAG instance status"""
        return {
            'name': self.name,
            'aircraft_type': self.aircraft_type,
            'document_count': self.collection.count(),
            'collection_name': self.collection_name,
            'persist_directory': self.persist_directory,
            'has_model': self.embedding_model is not None
        }
