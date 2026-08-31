# force_load.py - Force reload all documents
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.rag_base import RAGInstance
from src.utils.document_loader import DocumentLoader
from src.utils.config import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def clear_rag_collection(rag_name):
    """Clear the collection of the specified RAG instance"""
    try:
        instance = RAGInstance(rag_name)
        # Delete all documents
        all_ids = instance.collection.get()['ids']
        if all_ids:
            instance.collection.delete(ids=all_ids)
            print(f"   🗑️ Cleared {len(all_ids)} documents from {rag_name}")
        return instance
    except Exception as e:
        print(f"   ⚠️ Unable to clear {rag_name}: {e}")
        return None

def force_load_all():
    print("="*60)
    print("🔄 Force reloading all RAG documents")
    print("="*60)
    
    loader = DocumentLoader()
    rag_configs = config.get('rag_instances', {})
    
    # List of RAGs that need to be force-loaded
    target_rags = [
        'rag_flight_manual',
        'rag_ground_crew', 
        'rag_regulations',
        'rag_acs'
    ]
    
    for rag_name in target_rags:
        print(f"\n📂 Processing: {rag_name}")
        
        if rag_name not in rag_configs:
            print(f"   ❌ Not in config")
            continue
        
        rag_config = rag_configs[rag_name]
        doc_groups = rag_config.get('document_groups', [])
        
        print(f"   Document groups: {doc_groups}")
        
        # Check directory
        all_docs = []
        for group_name in doc_groups:
            group_dir = loader.raw_docs_dir / group_name
            print(f"   Checking directory: {group_dir}")
            
            if not group_dir.exists():
                print(f"   ❌ Directory does not exist")
                continue
            
            # List all files
            files = list(group_dir.glob("*"))
            print(f"   ✅ Found {len(files)} files")
            
            for file_path in group_dir.rglob("*"):
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext in loader.supported_formats:
                        docs = loader._load_document_with_chunks(file_path, group_name)
                        if docs:
                            all_docs.extend(docs)
                            print(f"      ✅ {file_path.name}: {len(docs)} chunks")
                    else:
                        print(f"      ⏭️ Skipped: {file_path.name} (unsupported format)")
        
        if not all_docs:
            print(f"   ⚠️ No documents found")
            continue
        
        # Clear the old collection
        print(f"   🗑️ Clearing old data...")
        try:
            instance = RAGInstance(rag_name)
            # Delete all existing documents
            existing = instance.collection.get()
            if existing and existing['ids']:
                instance.collection.delete(ids=existing['ids'])
                print(f"      Deleted {len(existing['ids'])} old documents")
        except Exception as e:
            print(f"      ⚠️ Clear failed: {e}")
        
        # Recreate the instance and add documents
        print(f"   📥 Adding {len(all_docs)} documents...")
        try:
            # Add in batches to avoid adding too many at once
            batch_size = 100
            for i in range(0, len(all_docs), batch_size):
                batch = all_docs[i:i+batch_size]
                instance.add_documents(batch)
                print(f"      ✅ Added {min(i+batch_size, len(all_docs))}/{len(all_docs)}")
            
            print(f"   ✅ {rag_name} loaded, {instance.collection.count()} documents total")
        except Exception as e:
            print(f"   ❌ Load failed: {e}")

def check_documents():
    """Check document loading status"""
    print("\n" + "="*60)
    print("📊 Document loading status check")
    print("="*60)
    
    rag_configs = config.get('rag_instances', {})
    
    for rag_name in rag_configs.keys():
        try:
            instance = RAGInstance(rag_name)
            count = instance.collection.count()
            status = "✅" if count > 0 else "❌"
            print(f"  {status} {rag_name}: {count} documents")
        except Exception as e:
            print(f"  ❌ {rag_name}: inaccessible - {e}")

if __name__ == "__main__":
    # Force load
    force_load_all()
    
    # Check results
    check_documents()
    
    print("\n" + "="*60)
    print("💡 Tip: restart the system to apply changes")
    print("   python run.py")
    print("="*60)