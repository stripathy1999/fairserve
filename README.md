 # FairServe
 
 FairServe is a city services fairness platform. It combines a Python analytics and simulation backend (Zone 2) with a Next.js web UI to propose, simulate, verify, and review policy changes for service delivery equity.
 
 ## Repo layout
 - `backend/`: Python pipeline + FastAPI services (Zone 2 analytics, simulation, agents)
 - `frontend/`: Next.js app and API routes for the UI
 - `test_nemotron_endpoint.py`: simple client test script
 
 ## Requirements
 - Python 3.10+ (virtualenv recommended)
 - Node.js 18+ and npm
 
 ## Quick start
 
 ### 1) Backend (Zone 2 APIs)
 From the repo root:
 
 ```bash
 cd backend
 python -m venv .venv
 source .venv/bin/activate
 # Install backend dependencies for your environment
 
 # Zone 2 gateway (agents, simulation, verification)
 uvicorn api.main:zone2_app --reload --host 0.0.0.0 --port 8001
 
 # Live stream API (optional)
 uvicorn api.app:app --reload --host 0.0.0.0 --port 8004
 ```
 
 ### 2) Frontend (UI)
 ```bash
 cd frontend
 npm install
 npm run dev
 ```
 
 Open `http://localhost:3000`.
 
 ## Data pipeline (Zone 2)
 The analytical pipeline is deterministic and runs in this order:
 1. `metrics/compute_fairness_metrics.py`
 2. `metrics/compute_neighborhood_signals.py`
 3. `state/build_city_state.py`
 4. `sim/simulator.py`
 5. `sim/verifier.py`
 
 To run the pipeline after new live batches arrive:
 ```bash
 cd backend
 python scripts/trigger_zone2.py
 ```
 
 ## Agent workflow endpoints
 Key FastAPI routes (Zone 2 gateway):
 - `POST /agents/propose`: propose policies from a city state
 - `POST /simulate`: simulate a policy
 - `POST /verify`: verify a simulated policy
 - `POST /agents/workflow`: end-to-end propose → simulate → verify → redteam → memo
 - `GET /agents/stream`: SSE stream of the multi-agent workflow

## AgentIQ / NeMo Agent Toolkit workflow
This repo includes an AgentIQ-compatible workflow that traces the full
propose → simulate → verify → redteam → memo pipeline.

```bash
pip install "nvidia-nat[langchain]"
pip install -e backend/agentiq

# Start the AgentIQ API server
nat serve --config_file backend/agentiq/configs/fairserve_workflow.yml
```

The API server runs on `http://localhost:8000` with `/generate` and streaming endpoints.
To use the AgentIQ UI, follow the setup in:
`https://github.com/NVIDIA/NeMo-Agent-Toolkit-UI`
 
 ## Notes
 - Set `CORS_ORIGIN` to point the backend at your frontend origin if needed.
 - Generated build artifacts and local virtualenvs are ignored by default (`.next/`, `nemotron-venv/`).
