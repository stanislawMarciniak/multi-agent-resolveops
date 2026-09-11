# ResolveOps AI

Multi-agent enterprise case resolution platform: investigate CRM and legacy billing systems, consult policies, propose safe remediation, run independent review, require human approval, then execute mutations deterministically.

![ResolveOps AI operator console](assets/web_view.jpg)

## What it does

ResolveOps separates **diagnosis**, **planning**, **safety review**, **human approval**, and **deterministic execution**:

```text
Untrusted enterprise data
        ↓
READ-only Investigator (MCP)
        ↓
Evidence-backed diagnosis
        ↓
Planner (no tools)
        ↓
Independent Reviewer
        ↓
Human approval
        ↓
Deterministic Executor
        ↓
Read-after-write verification
```

LLMs never write directly to enterprise systems. Mutations go through approved plans and deterministic application code.

## Highlights

- Multi-agent workflow: Investigator → Planner → Reviewer
- MCP tool boundary (READ vs WRITE)
- Policy RAG over enterprise runbooks and contracts
- Human-in-the-loop approval gate
- Deterministic executor + verifier
- Prompt-injection sanitization on tool output
- Persisted, resumable `CaseState`
- OpenTelemetry instrumentation
- Evaluation suite: multi-agent vs single-agent vs no-reviewer ablation

## Repository layout

```text
resolveops-ai/
├── assets/                 # README / demo media
├── backend/app/            # FastAPI, agents, execution, evals
├── data/evals/             # Dataset + stored evaluation results
├── documents/policies/     # Policy corpus for RAG
├── frontend/               # React operator + showcase UI
├── simulator/              # CRM + billing simulators
└── tests/
```

## Quick start

### 1. Backend

```bash
python -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -e ".[dev]"

cp .env.example .env
# set at least GOOGLE_API_KEY

PYTHONPATH=backend uvicorn app.main:app --reload --app-dir backend --host 0.0.0.0 --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)  
Health: [http://localhost:8000/health](http://localhost:8000/health)

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

UI: [http://localhost:5173](http://localhost:5173)

In local development the Vite server proxies `/api` → `http://127.0.0.1:8000`, so the browser does not need cross-origin calls. To call the API directly, set:

```bash
# frontend/.env.local
VITE_API_URL=http://127.0.0.1:8000
```

### 3. Optional simulators / MCP

Use Docker Compose for CRM, billing, MCP, and backend together:

```bash
docker compose up --build
```

## Operator UI

| Route | Purpose |
| --- | --- |
| `/` | Overview & live evaluation KPIs |
| `/cases` | Persisted cases |
| `/cases/:caseId` | Case Explorer (evidence → plan → review → approval) |
| `/showcase` | Dataset scenario cards |
| `/showcase/:evalId` | Multi / single / no-reviewer comparison |
| `/evaluations` | Charts, tag heatmap, reviewer ablation |
| `/architecture` | System & security diagrams |
| `/observability` | Cost, latency, tokens, errors |
| `/about` | Project narrative & limitations |

## Evaluations

Stored results live under `data/evals/results/`:

- `multi_agent.json`
- `single_agent.json`
- `no_reviewer.json`
- `final_comparison.json`

The UI reads them through read-only API endpoints (`GET /evaluations`, `/evaluations/comparison`, …). Numbers are never hardcoded in React.

Example interview walkthrough:

1. Overview — architecture story + pass rates  
2. Evaluations — multi-agent vs single-agent tradeoff  
3. ACME case — identifier normalization / unmatched payment  
4. ATLAS — contract override / safe escalation  
5. VEGA — multi-invoice limitation  
6. LYRA — stored prompt-injection security case  
7. Architecture — LLMs never execute enterprise writes  

## API surface (selected)

| Method | Path | Notes |
| --- | --- | --- |
| `GET` | `/health` | Liveness |
| `GET` | `/cases` | List persisted cases (public read) |
| `GET` | `/cases/{id}` | Full `CaseState` |
| `POST` | `/cases/{id}/approval` | Operator auth required |
| `POST` | `/cases/{id}/execute` | Operator auth required |
| `GET` | `/evaluations` | Eval summaries |
| `GET` | `/evaluations/comparison` | `final_comparison.json` |
| `GET` | `/system/status` | Backend / MCP / CRM / billing probes |

## Development notes

- Python **3.12**
- Backend CORS allows configured `FRONTEND_ORIGIN` plus localhost/`127.0.0.1` Vite ports in development
- Frontend stack: React, TypeScript, Vite, Tailwind, React Router, Recharts, React Flow, Lucide
- Tests: `pytest`

```bash
pytest
cd frontend && npm run build
```

## License / status

Internal / portfolio project — evaluation results and simulators are synthetic and intended for demos, not production enterprise data.
