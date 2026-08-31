# ✈️ Airplane Edu — Aircraft Education Q&A System

An aviation knowledge Q&A system for pilot education: interactive 3D aircraft model + multi-agent RAG retrieval + LLM explanation + digital-human narrator.

A student clicks a part on the 3D model to ask a question; the system retrieves relevant content from the flight manuals, answers in the voice of a "flight theory instructor" using an LLM (DeepSeek), highlights the corresponding 3D parts in real time in the teaching order, and reads the answer aloud through a digital human.

---

## System Architecture (three independent services)

```
┌───────────────┐  /api/*   ┌───────────────┐  /api/query  ┌──────────────────┐
│   frontend     │ ────────► │    backend     │ ───────────► │   rag_system      │
│  React+Vite    │  (proxy)   │    FastAPI     │   (HTTP)     │   multi-agent RAG │
│  :5173         │            │    :3001       │              │   :8000           │
└───────────────┘            └───────────────┘              └──────────────────┘
```

| Service | Stack | Port | Responsibility |
|---|---|---|---|
| `frontend/` | React 19 + Vite + Three.js | 5173 | 3D model interaction, chat, digital human, speech |
| `backend/` | Python + FastAPI | 3001 | Q&A endpoint `/api/chat-parts`, TTS `/api/speak` |
| `rag_system/` | Python + FastAPI + ChromaDB + BGE-M3 | 8000 | Multi-agent retrieval, aggregates into segmented teaching JSON |

**A full Q&A pipeline**:

```
User clicks a part → asks a question
  → frontend POSTs /api/chat-parts (with conversation history + selected part + aircraft type)
  → backend assembles context and forwards to rag_system POST /api/query
  → rag_system routes to expert Agents (safety/operation/compliance/student/interaction) for parallel retrieval
  → aggregates prompts into segmented teaching JSON {segments:[{text, parts}]}
  → backend parses the segments → frontend highlights parts segment by segment + digital human reads aloud
```

> Note: when rag_system is unavailable, backend automatically falls back to calling DeepSeek directly, so the frontend never shows a blank screen.

---

## Prerequisites

- **Python 3.10+** (3.11 recommended)
- **Node.js 18+** (with npm)
- On first startup, rag_system needs internet access to download the BGE-M3 embedding model (in China, configure a HuggingFace mirror).

---

## Deployment

Start the three services in this order: **rag_system → backend → frontend**.

### 1. Start rag_system (RAG retrieval service, :8000)

```bash
# 1.1 Install dependencies (includes chromadb / sentence-transformers / torch; large and slow)
cd rag_system
pip install -r requirements.txt

# 1.2 Configure the API key (set once at the project root)
#     cp ../.env.example ../.env   then fill in DEEPSEEK_API_KEY
#     (rag_system and backend both read this shared key)

# 1.3 Prepare the knowledge base
#     Place flight manuals and other documents under rag_system/data/raw_documents/<document_group>/
#     The <document_group> directory name must match rag_instances.*.document_groups in config.yaml
#     Supported formats: .pdf / .txt / .md / .json (PDFs are chunked every 5 pages)
#     Example directory layout:
#       rag_system/data/raw_documents/
#         ├── aircraft_params/   # aircraft parameters
#         ├── checklists/        # checklists
#         ├── regulations/       # regulations
#         ├── acs/               # assessment standards
#         ├── components/        # component hierarchy index
#         ├── manipulation/      # control mapping
#         ├── performance/       # performance / envelope data
#         ├── emergency/         # emergency procedures
#         ├── general/           # general (weather, licensing, etc.)
#         ├── flight_manual/     # flight manual
#         └── ground_crew/       # ground crew knowledge

# 1.4 Start (first startup reads documents and auto-builds the vector store; please be patient)
python src/main.py
# → http://localhost:8000 (API docs at /docs)
```

### 2. Start backend (Q&A endpoint, :3001)

```bash
cd backend
pip install -r requirements.txt

# Configuration — already set in the root .env (step 1.2); no per-service .env needed

python main.py
# → http://localhost:3001
```

### 3. Start frontend (frontend, :5173)

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173 (vite.config.js already proxies /api to localhost:3001)
```

Open **http://localhost:5173** in your browser.

---

## Configuration

### API key is configured in ONE place

| Location | File | Description |
|---|---|---|
| project root | `.env` (copy from `.env.example`) | `DEEPSEEK_API_KEY` — shared by rag_system (multi-agent RAG) and backend (Q&A fallback) |

> ⚠️ All real keys in this package have been redacted to `YOUR_API_KEY_HERE`; fill them in yourself.
> `.env` / `config.yaml` contain plaintext keys — **never commit them to a public repository**.
> If you switch `llm.provider` in `rag_system/config.yaml` to `"openai"`, also set `OPENAI_API_KEY` in `.env`.

### Key configuration items

| Item | File | Description |
|---|---|---|
| `llm.provider` | `rag_system/config.yaml` | `"deepseek"` or `"openai"` |
| `aircraft_types` | `rag_system/config.yaml` | Supported aircraft types, default `["c172p"]` |
| `rag_instances` | `rag_system/config.yaml` | Document groups + Agents for each retrieval instance |
| `RAG_SYSTEM_URL` | `.env` (root) | rag_system address, default `http://localhost:8000` |
| `/api` proxy | `frontend/vite.config.js` | Points to `http://localhost:3001` by default |

---

## FAQ

- **rag_system is slow on first startup**: it reads documents to build the vector store and downloads the BGE-M3 model — this is expected.
- **BGE-M3 download fails**: set the environment variable `HF_ENDPOINT=https://hf-mirror.com`.
- **backend reports a rag_system connection error**: confirm rag_system is running and `RAG_SYSTEM_URL` is correct; backend automatically falls back to calling DeepSeek directly when rag_system is unavailable.
- **Port conflicts**: Vite defaults to 5173 and auto-increments to 5174 if occupied (the `/api` proxy still points to 3001); backend is fixed at 3001 and rag_system at 8000.
