# src/utils/document_loader.py
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import PyPDF2
from .config import config
from .logger import setup_logger

logger = setup_logger(__name__)

class DocumentLoader:
    """Document loader - supports loading documents in multiple formats"""

    def __init__(self):
        self.data_root = Path(__file__).parent.parent.parent / "data"
        self.raw_docs_dir = self.data_root / config.get('data.raw_documents', 'raw_documents')
        self.processed_dir = self.data_root / config.get('data.processed', 'processed')

        # Supported document formats
        self.supported_formats = {
            '.json': self._load_json,
            '.txt': self._load_txt,
            '.pdf': self._load_pdf_with_chunks,  # PDFs are loaded with chunking
            '.md': self._load_txt,
        }

        logger.info(f"Document loader initialized, data directory: {self.data_root}")

    def load_all_documents(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load documents for all RAG instances"""
        all_docs = {}
        rag_configs = config.get('rag_instances', {})

        for rag_name, rag_config in rag_configs.items():
            doc_groups = rag_config.get('document_groups', [])
            documents = []

            for group_name in doc_groups:
                group_dir = self.raw_docs_dir / group_name
                print(f"Checking directory: {group_dir}")  # added debug
                if not group_dir.exists():
                    print(f"  ❌ Directory does not exist: {group_dir}")  # added debug
                    logger.warning(f"Document group directory does not exist: {group_dir}")
                    continue

                # List files in the directory
                files = list(group_dir.glob("*"))
                print(f"  ✅ Directory exists, found {len(files)} files")  # added debug

                for file_path in group_dir.rglob("*"):
                    if file_path.is_file():
                        ext = file_path.suffix.lower()
                        print(f"    Processing file: {file_path.name} (extension: {ext})")  # added debug
                        if ext in self.supported_formats:
                            docs = self._load_document_with_chunks(file_path, group_name)
                            if docs:
                                documents.extend(docs)
                                print(f"      Loaded {len(docs)} document chunks")  # added debug
                        else:
                            print(f"      Skipping: unsupported format {ext}")  # added debug

            if documents:
                all_docs[rag_name] = documents
                logger.info(f"Loaded {rag_name}: {len(documents)} document chunks")
            else:
                logger.warning(f"Loaded {rag_name}: no documents found")

        return all_docs

    def _load_document_with_chunks(self, file_path: Path, group_name: str) -> List[Dict[str, Any]]:
        """Load a document and chunk it"""
        ext = file_path.suffix.lower()

        if ext in self.supported_formats:
            try:
                if ext == '.pdf':
                    return self._load_pdf_with_chunks(file_path, group_name)
                else:
                    content = self.supported_formats[ext](file_path)
                    if content:
                        # Ordinary documents are treated as a single chunk
                        return [{
                            'id': f"{group_name}_{file_path.stem}_{hash(file_path.name) % 10000}",
                            'text': content,
                            'metadata': {
                                'source': str(file_path),
                                'group': group_name,
                                'file_name': file_path.name,
                                'file_type': ext[1:],
                                'file_path': str(file_path.relative_to(self.raw_docs_dir))
                            }
                        }]
            except Exception as e:
                logger.error(f"Failed to load document {file_path}: {str(e)}")

        return []

    def _load_pdf_with_chunks(self, file_path: Path, group_name: str) -> List[Dict[str, Any]]:
        """Load a PDF and chunk it"""
        chunks = []
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                total_pages = len(pdf_reader.pages)

                # Extract metadata
                base_metadata = {
                    'source': str(file_path),
                    'group': group_name,
                    'file_name': file_path.name,
                    'file_type': 'pdf',
                    'total_pages': total_pages
                }

                # Chunk by page (5 pages per chunk to avoid overly large chunks)
                chunk_size = 5
                current_chunk = []
                current_page_start = 1

                for page_num, page in enumerate(pdf_reader.pages, 1):
                    text = page.extract_text()
                    if text:
                        current_chunk.append(text)

                    # Save a chunk every 5 pages or at the last page
                    if len(current_chunk) >= chunk_size or page_num == total_pages:
                        if current_chunk:
                            chunk_text = '\n'.join(current_chunk)
                            if len(chunk_text) > 100:  # at least 100 characters
                                chunk_id = f"{group_name}_{file_path.stem}_pages_{current_page_start}_{page_num}"
                                chunks.append({
                                    'id': chunk_id,
                                    'text': chunk_text,
                                    'metadata': {
                                        **base_metadata,
                                        'page_start': current_page_start,
                                        'page_end': page_num,
                                        'chunk_size': len(current_chunk)
                                    }
                                })
                            current_chunk = []
                            current_page_start = page_num + 1

                logger.info(f"PDF {file_path.name}: chunked into {len(chunks)} chunks")

        except Exception as e:
            logger.error(f"PDF loading failed {file_path}: {str(e)}")

        return chunks

    def _load_json(self, file_path: Path) -> str:
        """Load a JSON document"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, dict):
            return data.get('text', data.get('content', json.dumps(data, ensure_ascii=False)))
        elif isinstance(data, list):
            texts = []
            for item in data:
                if isinstance(item, dict):
                    text = item.get('text', item.get('content', ''))
                    if text:
                        texts.append(text)
            return '\n'.join(texts)
        else:
            return str(data)

    def _load_txt(self, file_path: Path) -> str:
        """Load a TXT document"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    def load_documents_by_aircraft(self, aircraft_type: str) -> Dict[str, List[Dict[str, Any]]]:
        """Load documents for a specific aircraft type"""
        all_docs = {}
        rag_configs = config.get('rag_instances', {})

        for rag_name, rag_config in rag_configs.items():
            doc_groups = rag_config.get('document_groups', [])
            documents = []

            for group_name in doc_groups:
                group_dir = self.raw_docs_dir / group_name
                if not group_dir.exists():
                    continue

                # Find directories or files containing the aircraft type name
                for file_path in group_dir.rglob("*"):
                    if file_path.is_file():
                        # Check whether the file path contains the aircraft type
                        if aircraft_type in str(file_path).lower():
                            docs = self._load_document_with_chunks(file_path, group_name)
                            if docs:
                                documents.extend(docs)

            if documents:
                all_docs[rag_name] = documents
                logger.info(f"Loaded {rag_name} aircraft type {aircraft_type}: {len(documents)} documents")

        return all_docs


class DocumentProcessor:
    """Document processor - used for document preprocessing and chunking"""

    @staticmethod
    def chunk_document(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Chunk a long document"""
        chunks = []

        # Split by sentence
        sentences = re.split(r'(?<=[.!?])\s*', text)

        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence_len = len(sentence)
            if current_size + sentence_len > chunk_size and current_chunk:
                chunks.append(''.join(current_chunk))
                overlap_text = ''.join(current_chunk[-overlap:]) if overlap > 0 else ''
                current_chunk = [overlap_text] if overlap_text else []
                current_size = len(overlap_text)

            current_chunk.append(sentence)
            current_size += sentence_len

        if current_chunk:
            chunks.append(''.join(current_chunk))

        return chunks


def init_data_structure():
    """Initialize the data directory structure"""
    from pathlib import Path

    data_root = Path(__file__).parent.parent.parent / "data"

    # Create the directory structure
    directories = [
        'raw_documents/acs',
        'raw_documents/aircraft_params/01_aircraft_params',
        'raw_documents/aircraft_params/02_v_speeds',
        'raw_documents/aircraft_params/03_flight_limits',
        'raw_documents/aircraft_params/12_redlines',
        'raw_documents/checklists/08_normal_checklist',
        'raw_documents/checklists/09_abnormal_checklist',
        'raw_documents/checklists/10_memory_items',
        'raw_documents/checklists/11_emergency_procedures',
        'raw_documents/components/26_component_index',
        'raw_documents/emergency/09_abnormal_checklist',
        'raw_documents/emergency/10_memory_items',
        'raw_documents/emergency/11_emergency_procedures',
        'raw_documents/flight_manual',
        'raw_documents/general',
        'raw_documents/ground_crew',
        'raw_documents/manipulation/04_control_mapping',
        'raw_documents/manipulation/05_atomic_actions',
        'raw_documents/manipulation/27_manipulation_principles',
        'raw_documents/performance/01_performance_data',
        'raw_documents/performance/03_envelope_data',
        'raw_documents/regulations',
        'vector_stores',
        'processed/chunked_documents',
        'logs'
    ]

    for dir_path in directories:
        (data_root / dir_path).mkdir(parents=True, exist_ok=True)

    print("✅ Data directory initialization complete!")
    print(f"Data root directory: {data_root}")
