# src/main.py
import uvicorn
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.llm_client import llm_client

def main():
    """Start the main program"""
    print("="*50)
    print("Aviation Education Multi-Agent RAG System")
    print("="*50)
    print(f"🤖 LLM provider: {llm_client.get_provider()}")
    print(f"📦 LLM model: {llm_client.get_model()}")
    print("="*50)
    print("Starting system...")
    print("API docs: http://localhost:8000/docs")
    print("Press Ctrl+C to stop the service")
    print("="*50)
    
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()