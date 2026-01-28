"""
FairServe Zone-2 API

Lightweight FastAPI layer exposing Zone-2 capabilities:
- Metrics (read-only evidence)
- City State (primary briefing packet)
- Budget Context (read-only budget data)
- Simulation (policy testing)
- Verification (constitution enforcement)
- Refresh (recompute Zone-2 outputs)
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional
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
DATA_DIR = PROJECT_ROOT.parent / "data" / "processed"
BUDGET_DIR = PROJECT_ROOT.parent / "data" / "budget"


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


@app.get("/budget_context")
def get_budget_context(service_type: Optional[str] = Query(None, description="Optional service type to filter budget context")):
    """
    Budget context for governance, not decision-making.
    
    Returns read-only budget data from precomputed files.
    Budget does NOT make decisions or act as an agent.
    
    Query Parameters:
    - service_type (optional): Filter by specific service type
    
    Returns:
    - If service_type provided: Budget context for that service's department
    - If no service_type: All department budget contexts
    """
    
    # Load required files
    dept_summary_file = DATA_DIR / "department_budget_summary.json"
    budget_metrics_file = DATA_DIR / "budget_metrics.json"
    service_mapping_file = BUDGET_DIR / "service_type_to_department.json"
    
    missing_files = [
        str(path)
        for path in (dept_summary_file, budget_metrics_file, service_mapping_file)
        if not path.exists()
    ]
    if missing_files:
        raise HTTPException(
            status_code=404,
            detail=(
                "Budget data files not found. Run budget pipeline to generate. "
                f"Missing: {missing_files}"
            ),
        )

    try:
        with open(dept_summary_file, 'r') as f:
            dept_summary = json.load(f)
        with open(budget_metrics_file, 'r') as f:
            budget_metrics = json.load(f)
        with open(service_mapping_file, 'r') as f:
            service_mapping = json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid JSON in budget data files: {e}",
        )
    
    # Budget constraints (hardcoded)
    budget_constraints = {
        "max_budget_stress_ratio": 0.15,
        "recommended_budget_stress_ratio": 0.05
    }
    
    # Assumptions
    assumptions = [
        "Budget is spending-only",
        "Latest fiscal year used",
        "Service-to-department mapping is static",
        "Costs are estimated, not allocated"
    ]
    
    if service_type:
        normalized_service = service_type.strip()
        if not normalized_service:
            raise HTTPException(
                status_code=400,
                detail="Service type cannot be empty or whitespace.",
            )
        mapping_lookup = {key.lower(): key for key in service_mapping.keys()}
        lookup_key = normalized_service.lower()
        if lookup_key in mapping_lookup:
            service_type = mapping_lookup[lookup_key]
        # Filter for specific service type
        if service_type not in service_mapping:
            raise HTTPException(
                status_code=400,
                detail=f"Service type '{service_type}' not found in mapping. Available: {list(service_mapping.keys())}"
            )
        
        department = service_mapping[service_type]
        
        # Find budget metrics for this service type
        service_budget = next((b for b in budget_metrics if b['service_type'] == service_type), None)
        
        if not service_budget:
            raise HTTPException(
                status_code=404,
                detail=f"Budget metrics not found for service type '{service_type}'"
            )
        
        return {
            "service_type": service_type,
            "department": department,
            "budget_year": service_budget['fiscal_year'],
            "annual_budget_usd": service_budget['department_annual_budget_usd'],
            "estimated_budget_per_incident_usd": service_budget['estimated_budget_per_incident_usd'],
            "budget_constraints": budget_constraints,
            "assumptions": assumptions
        }
    else:
        # Return all budget contexts
        budget_contexts = []
        
        for metric in budget_metrics:
            budget_contexts.append({
                "department": metric['department'],
                "budget_year": metric['fiscal_year'],
                "annual_budget_usd": metric['department_annual_budget_usd'],
                "estimated_budget_per_incident_usd": metric['estimated_budget_per_incident_usd']
            })
        
        return {
            "budget_contexts": budget_contexts
        }


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
