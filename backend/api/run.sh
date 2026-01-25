#!/bin/bash
# Helper to run API
cd "$(dirname "$0")/.." || exit
python3 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8081
