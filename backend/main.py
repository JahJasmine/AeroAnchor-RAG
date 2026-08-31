"""
Airplane education Q&A backend — FastAPI + Edge TTS
================================================
rag_system : standalone multi-agent RAG service (HTTP, port 8000)
backend/   : Q&A endpoint (/api/chat-parts), TTS
"""

import io
import os
import sys
import json
import re
import edge_tts
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import OpenAI

# Add the project root to sys.path so the `backend` package can be imported (when running python main.py directly)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load the shared root .env (project root) — API keys are configured in one place
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# ── RAG System adapter layer (rag_system goes over HTTP, does not import the old rag/) ──
from backend.rag_system_client import query_rag_system, extract_final_response

# ── Config ─────────────────────────────────────────────────────────
EDGE_VOICE = "en-US-GuyNeural"

# ── DeepSeek direct connection (pure API, no RAG) ─────────────────
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
_deepseek_client = None

def get_deepseek():
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=DEEPSEEK_BASE_URL,
        )
    return _deepseek_client

# ── App ────────────────────────────────────────────────────────────
app = FastAPI(title="Airplane Edu API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response Models ────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str
    content: str


class SpeakRequest(BaseModel):
    text: str


# ── Routes ─────────────────────────────────────────────────────────

class ChatPartsRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    messages: list[ChatMessage]
    selected_parts: list[str] = []
    available_parts: list[str] = []
    model_name: str = ''
    session_id: str = ''


def _call_deepseek(messages: list) -> str:
    """Call DeepSeek (json_object mode first, fall back to plain mode on error/empty), return the raw text."""
    client = get_deepseek()
    raw = ""
    for use_json in (True, False):
        try:
            kwargs = dict(model=DEEPSEEK_MODEL, messages=messages, temperature=0.3, max_tokens=800)
            if use_json:
                kwargs["response_format"] = {"type": "json_object"}
            resp = client.chat.completions.create(**kwargs)
            raw = (resp.choices[0].message.content or "").strip()
        except Exception as e:
            print(f"[chat-parts] call error (json={use_json}): {e}")
            raw = ""
        if raw:
            break
    return raw


# The model sometimes injects meta-discourse/format residue into the explanation ("This is the answer", "The answer is", markdown symbols, etc.), strip them all before reading aloud
_META_PHRASES = (
    "This is the answer", "This is the answer", "The above is the answer", "The following is my answer",
    "The answer is as follows", "The answer is as follows", "The answer is", "The answer is",
)

# Leading pleasantries/evaluations (stripped only at the start): "OK, ...", "That's a very good question, ..."
_LEADING_META_RE = re.compile(
    r'^\s*'
    r'(?:(?:okay|ok|um|right|correct|yes)[,.\s!]*)?'
    r'(?:this question[^.! \n,]{0,18}[,.!]\s*)?'
)


def _strip_trailing_transition(t: str) -> str:
    """Strip the trailing transition clause ("Remember this division of labor, and we'll cover coordination next" — that kind of closing remark)."""
    parts = [p for p in re.split(r'(?<=[.!])', t) if p.strip()]
    if len(parts) >= 2:
        last = parts[-1].strip()
        if 0 < len(last) <= 20 and re.search(r'next|continue|cover', last):
            return ''.join(parts[:-1]).strip()
    return t


def _clean_segment_text(t: str) -> str:
    """Clean a single explanation segment: remove markdown, remove leaked meta-discourse/pleasantries/transitions, trim whitespace."""
    t = (t or "").replace("*", "").replace("`", "").replace("#", "")
    for phrase in _META_PHRASES:
        t = t.replace(phrase, "")
    # Repeatedly strip leading pleasantries/evaluations and trailing transitions (e.g. "OK, that's a very good question, ... Remember this division of labor, we'll cover coordination next.")
    for _ in range(3):
        new = _LEADING_META_RE.sub("", t)
        new = _strip_trailing_transition(new)
        if new == t:
            break
        t = new
    return t.strip(" \t\n\r")


def _parse_segments(raw: str, available_parts: list) -> list:
    """Parse DeepSeek's returned text into segments [{text, parts}]; on JSON failure, fall back to a single segment + keyword matching."""
    if not raw:
        return []
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    m = re.search(r'\{.*\}', raw, re.DOTALL)
    data = None
    try:
        data = json.loads(m.group(0) if m else raw)
    except Exception:
        data = None

    segments = []
    if isinstance(data, dict) and isinstance(data.get("segments"), list):
        for s in data["segments"]:
            if not isinstance(s, dict):
                continue
            t = _clean_segment_text(str(s.get("text", "")))
            if len(t) < 4:  # empty or too short after cleaning, treat as garbage and discard
                continue
            raw_parts = s.get("parts", [])
            if isinstance(raw_parts, str):
                raw_parts = [raw_parts]
            ps = []
            for rp in raw_parts:
                rp = str(rp)
                if rp in available_parts:  # exact match takes priority
                    ps.append(rp)
                    continue
                # substring normalization: normalize something like "bypass duct and tail nozzle still not cleaned up..." (carrying garbage) to "bypass duct and tail nozzle"
                for p in available_parts:
                    if p and p in rp:
                        ps.append(p)
                        break
            seen = set()
            ps = [p for p in ps if not (p in seen or seen.add(p))]  # dedupe preserving order
            if not ps:
                ps = [p for p in available_parts if p in t]
            segments.append({"text": t, "parts": ps})

    if not segments:
        t = _clean_segment_text(raw)
        if len(t) >= 4:
            ps = [p for p in available_parts if p in t]
            segments = [{"text": t, "parts": ps}]
    return segments


@app.post("/api/chat-parts")
async def chat_parts(req: ChatPartsRequest):
    """Segmented part highlighting: rag_system's aggregated prompt directly outputs segmented teaching JSON, which backend parses and returns"""
    user_msgs = [m for m in req.messages if m.role == "user"]
    if not user_msgs:
        return {"error": "no user message found"}
    question = user_msgs[-1].content.strip()
    if not question:
        return {"error": "empty question"}

    segments = []
    sources = []

    # 1. Ask rag_system for the "grounded answer" (set empty on failure, fall back below)
    grounded = ""
    try:
        # Put the aircraft type / selected parts / available parts into context; rag_system's router and aggregator will read them
        rag_context = {
            "model_name": req.model_name,
            "selected_parts": req.selected_parts,
            "available_parts": req.available_parts,
        }
        data = query_rag_system(question, context=rag_context)
        grounded = extract_final_response(data)
        print(f"[chat-parts] rag_system answer={grounded[:300]}")
    except Exception as e:
        print(f"[chat-parts] rag_system error: {e}")
        grounded = ""

    # 2. Directly parse the segmented answer returned by rag_system (no re-processing needed)
    if grounded:
        segments = _parse_segments(grounded, req.available_parts)

    # 3. When rag_system returns no answer, fall back to pure DeepSeek direct answering (existing fallback logic)
    if not segments:
        try:
            raw = _call_deepseek([
                {"role": "system", "content": "You are a senior flight theory instructor. Please answer flight students in English, covering both principles and flight applications, in 1-3 sentences, without mentioning any materials or source numbers."},
                *[{"role": m.role, "content": m.content} for m in req.messages],
            ])
            answer = raw.replace("*", "").replace("`", "").strip()
            segments = _parse_segments(answer, req.available_parts)
        except Exception as e:
            print(f"[chat-parts] fallback error: {e}")
            segments = []

    if not segments:
        return {"segments": [{"text": "Sorry, something went wrong. Please try again later.", "parts": []}], "sources": []}

    print(f"[chat-parts] segments={segments}")
    return {"segments": segments, "sources": sources}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/speak")
async def speak(req: SpeakRequest):
    """TTS voice synthesis — Microsoft Edge TTS"""
    if not req.text:
        raise HTTPException(status_code=400, detail="text required")

    try:
        communicate = edge_tts.Communicate(req.text, EDGE_VOICE)
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]

        if not audio_bytes:
            raise HTTPException(status_code=500, detail="TTS generated no audio")

    except Exception as e:
        print(f"/api/speak error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS failed: {e}")

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={"Content-Length": str(len(audio_bytes))},
    )


# ── Main ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", "3001"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
