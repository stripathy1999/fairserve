# FairServe AgentIQ (NeMo Agent Toolkit) Workflow

This package exposes the FairServe propose → simulate → verify → redteam → memo pipeline
as a **traceable sequential executor** workflow for NVIDIA AgentIQ (now NeMo Agent Toolkit).

## Install
```bash
pip install "nvidia-nat[langchain]"
pip install -e backend/agentiq
```

## Run the AgentIQ API server
```bash
nat serve --config_file backend/agentiq/configs/fairserve_workflow.yml
```

The API server exposes `/generate` (and streaming endpoints) on `http://localhost:8000`.
You can send a JSON input (string) or a dict-shaped payload.

Example:
```bash
curl --request POST \
  --url http://localhost:8000/generate \
  --header 'Content-Type: application/json' \
  --data '{
    "input_message": "{\"service\":\"Encampment\"}"
  }'
```

## AgentIQ UI
The UI is provided by the NeMo Agent Toolkit UI repo:
https://github.com/NVIDIA/NeMo-Agent-Toolkit-UI

Follow its setup instructions, then point it at the API server above.
