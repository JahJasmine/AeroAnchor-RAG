# init_data.py - Data initialization script
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.rag.rag_builder import init_data_structure

if __name__ == "__main__":
    print("=" * 50)
    print("Initializing aviation RAG system data structure")
    print("=" * 50)
    init_data_structure()
    print("\nNext steps:")
    print("1. Configure DEEPSEEK_API_KEY in the root .env (copy ../.env.example to ../.env)")
    print("2. Run python run.py to start the system")