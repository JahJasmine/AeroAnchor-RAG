"""
HTTP adapter layer for rag_system
=================================
Call rag_system through its existing HTTP interface (FastAPI, port 8000),
without importing or modifying any code in rag_system.

The backend (3001) uses this module to obtain the "grounded answer" from rag_system,
which main.py's DeepSeek then reworks into segmented explanations.
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# rag_system service address (configure RAG_SYSTEM_URL in .env, defaults to localhost 8000)
RAG_SYSTEM_URL = os.getenv("RAG_SYSTEM_URL", "http://localhost:8000").rstrip("/")

# Per-query timeout (seconds): rag_system's multi-agent + LLM may be slow
RAG_SYSTEM_TIMEOUT = float(os.getenv("RAG_SYSTEM_TIMEOUT", "120"))


def query_rag_system(question, aircraft_type="c172p", context=None, timeout=None):
    """Call rag_system's POST /api/query and return the full JSON.

    Args:
        question:      the student's question text
        aircraft_type: aircraft type (defaults to c172p in the rag_system config)
        context:       extra context dict (optional; rag_system merges it with aircraft_type and passes it to the orchestrator)
        timeout:       timeout in seconds, defaults to RAG_SYSTEM_TIMEOUT

    Returns:
        dict, key fields: final_response (the final text answer), selected_agents,
        router_decision, agent_responses, aircraft_type

    Raises:
        httpx.HTTPError / connection errors: caught by the caller (main.py) which then falls back to DeepSeek
    """
    payload = {
        "query": question,
        "aircraft_type": aircraft_type,
        "context": context or {},
    }
    resp = httpx.post(
        f"{RAG_SYSTEM_URL}/api/query",
        json=payload,
        timeout=timeout or RAG_SYSTEM_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def extract_final_response(data):
    """Extract the final answer text from the /api/query response (returns an empty string if empty)."""
    if not isinstance(data, dict):
        return ""
    return (data.get("final_response") or "").strip()
