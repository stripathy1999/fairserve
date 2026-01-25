"""
FairServe Zone-2 API

Lightweight FastAPI layer exposing Zone-2 capabilities:
- Metrics (read-only evidence)
- City State (primary briefing packet)
- Simulation (policy testing)
- Verification (constitution enforcement)
- Refresh (recompute Zone-2 outputs)
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import json
from pathlib import Path
import logging

from api.models import (
    SimulateRequest, SimulateResponse,
    VerifyRequest, VerifyResponse,
    RefreshResponse, HealthResponse
)
from api.runner import (
    run_simulator, run_verifier, run_refresh, check_required_files
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="FairServe Zone-2 API",
    description="API layer for FairServe Zone-2 capabilities",
    version="1.0.0"
)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"


@app.get("/")
async def root():
    """
    Root endpoint - API information and available endpoints.
    """
    return {
        "name": "FairServe Zone-2 API",
        "version": "1.0.0",
        "description": "API layer for FairServe Zone-2 capabilities",
        "endpoints": {
            "GET /": "This endpoint - API information",
            "GET /health": "Health check - verify required files exist",
            "GET /fairness_metrics": "Read-only fairness metrics evidence",
            "GET /city_state": "Primary briefing packet for agents",
            "POST /simulate": "Run policy simulation",
            "POST /verify": "Verify policy against constitution",
            "POST /refresh": "Recompute all Zone-2 outputs",
            "GET /docs": "Interactive API documentation (Swagger UI)",
            "GET /redoc": "Alternative API documentation (ReDoc)"
        },
        "documentation": {
            "interactive": "http://localhost:8080/docs",
            "redoc": "http://localhost:8080/redoc"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Verifies that required Zone-2 output files exist.
    """
    all_exist, missing = check_required_files()
    
    if all_exist:
        return HealthResponse(
            status="healthy",
            missing_files=[],
            message="All required Zone-2 files are present"
        )
    else:
        return HealthResponse(
            status="degraded",
            missing_files=missing,
            message=f"Missing {len(missing)} required files. Run /refresh to regenerate."
        )


@app.get("/fairness_metrics")
async def get_fairness_metrics():
    """
    Read-only evidence: Returns fairness metrics.
    
    No computation triggered.
    """
    metrics_file = DATA_DIR / "fairness_metrics.json"
    
    if not metrics_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Fairness metrics not found at {metrics_file}. Run /refresh to generate."
        )
    
    try:
        with open(metrics_file, 'r') as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in fairness_metrics.json: {e}")


@app.get("/city_state")
async def get_city_state():
    """
    Primary briefing packet for agents.
    
    Returns comprehensive city state including:
    - City context and baselines
    - Neighborhood profiles with fairness metrics
    - Governance constraints (constitution)
    - Derived insights (worst neighborhoods, etc.)
    """
    city_state_file = DATA_DIR / "city_state.json"
    
    if not city_state_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"City state not found at {city_state_file}. Run /refresh to generate."
        )
    
    try:
        with open(city_state_file, 'r') as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in city_state.json: {e}")


@app.post("/simulate", response_model=SimulateResponse)
async def simulate_policy(request: SimulateRequest):
    """
    Run one policy simulation.
    
    Accepts policy parameters, runs simulator.py, and returns only the result
    for the requested policy (not the full scenario_results.json).
    
    Parameters are validated against constraints defined in sim/policies.py.
    """
    logger.info(f"Simulating policy: {request.policy_id}")
    
    # Convert request to policy dict
    policy_dict = {
        "policy_id": request.policy_id,
        "parameters": request.parameters.model_dump()
    }
    
    try:
        result = run_simulator(policy_dict)
        logger.info(f"Simulation completed for {request.policy_id}")
        return SimulateResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during simulation: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.post("/verify", response_model=VerifyResponse)
async def verify_policy(request: VerifyRequest):
    """
    Constitution enforcement.
    
    Accepts a simulated policy result and returns verification verdict
    (whether it passes all constitutional constraints).
    """
    logger.info(f"Verifying policy: {request.policy_result.policy_id}")
    
    # Convert to dict for verifier
    policy_result_dict = request.policy_result.model_dump()
    
    try:
        verdict = run_verifier(policy_result_dict)
        logger.info(f"Verification completed for {request.policy_result.policy_id}")
        return VerifyResponse(**verdict)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during verification: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.post("/refresh", response_model=RefreshResponse)
async def refresh_zone2():
    """
    Recompute Zone-2 outputs.
    
    Sequentially runs:
    1. compute_fairness_metrics.py
    2. compute_neighborhood_signals.py
    3. build_city_state.py
    
    Safe to call multiple times. Returns status and timestamp.
    """
    logger.info("Starting Zone-2 refresh")
    
    try:
        result = run_refresh()
        logger.info("Zone-2 refresh completed successfully")
        return RefreshResponse(**result)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during refresh: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
