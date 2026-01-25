"""
Pydantic models for FairServe Zone-2 API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


class PolicyParameters(BaseModel):
    """Policy parameters matching the knobs defined in sim/policies.py"""
    capacity_shift_pct: float = Field(..., ge=0.0, le=0.30, description="Fraction of capacity shifted from best-off to worst-off neighborhoods")
    efficiency_bonus_pct: float = Field(..., ge=0.0, le=0.20, description="System-wide efficiency gain from batching and routing improvements")
    max_reassignments: int = Field(..., ge=0, le=3, description="Limit on ticket reassignments to prevent aging loops")


class SimulateRequest(BaseModel):
    """Request to simulate a single policy"""
    policy_id: str = Field(..., description="Unique identifier for this policy")
    parameters: PolicyParameters


class NeighborhoodEffect(BaseModel):
    """Simulation effects for a single neighborhood"""
    delta_p90: float
    delta_backlog_pct: float


class SimulateResponse(BaseModel):
    """Response from policy simulation"""
    policy_id: str
    parameters: Dict[str, Any]
    neighborhood_effects: Dict[str, NeighborhoodEffect]
    citywide_delta_p90: float
    equity_improvement: float


class Violation(BaseModel):
    """Constitution violation details"""
    constraint: str
    neighborhood: str
    observed: float
    allowed: float


class VerifyRequest(BaseModel):
    """Request to verify a policy result against constitution"""
    policy_result: SimulateResponse


class VerifyResponse(BaseModel):
    """Verification verdict for a policy"""
    policy_id: str
    pass_: bool = Field(..., alias="pass", description="Whether policy passed all constraints")
    violations: List[Violation]

    class Config:
        populate_by_name = True


class RefreshResponse(BaseModel):
    """Response from refresh operation"""
    status: str
    timestamp: str
    steps_completed: List[str]
    message: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    missing_files: List[str] = []
    message: str
