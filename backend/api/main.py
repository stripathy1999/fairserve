"""
FairServe Zone-2 Gateway API (port 8004).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.models import SimulateRequest, SimulateResponse, VerifyRequest, VerifyResponse
from api.nemotron_client import chat
from api.runner import run_refresh, run_simulator, run_verifier
from agents.proposer import propose_policies
from agents.redteam import redteam_review
from agents.arbiter import build_memo

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="FairServe Zone-2 Gateway",
    description="Gateway API for FairServe Zone-2 outputs and agents",
    version="1.0.0",
)
zone2_app = app

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"
EXPORTS_DIR = DATA_DIR / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

INCIDENT_FILES = [
    DATA_DIR / "incidents_historical.parquet",
    DATA_DIR / "incidents_live.parquet",
]

GOVERNANCE = {
    "worst_k": 3,
    "constraints": {
        "min_worst_k_improvement": 0.15,
        "max_neighborhood_harm": 0.05,
        "max_backlog_growth": 0.10,
        "citywide_p90_must_not_worsen": True,
    },
}
POLICY_SPACE = {
    "capacity_shift_pct": [0.0, 0.3],
    "efficiency_bonus_pct": [0.0, 0.1],
    "max_reassignments": [0, 3],
}


class SimRunRequest(BaseModel):
    policies: List[Dict[str, Any]]


class AgentProposeRequest(BaseModel):
    city_state: Dict[str, Any]


class AgentWorkflowRequest(BaseModel):
    service: Optional[str] = None
    city_state: Optional[Dict[str, Any]] = None


class AgentStreamRequest(BaseModel):
    service: Optional[str] = None


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    with open(path, "r") as f:
        return json.load(f)


def _get_services_from_fairness(fairness_data: List[Dict[str, Any]]) -> List[str]:
    services = {row.get("service_type") for row in fairness_data if row.get("service_type")}
    return sorted(services)


def _load_incidents() -> pd.DataFrame:
    frames = []
    for path in INCIDENT_FILES:
        if path.exists():
            frames.append(pd.read_parquet(path))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _count_redactions(series: pd.Series) -> int:
    count = 0
    for value in series:
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            count += len(value) > 0
            continue
        try:
            count += len(value) > 0
        except TypeError:
            count += bool(value)
    return int(count)


def _build_city_state(
    service: str,
    fairness_data: List[Dict[str, Any]],
    signals_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    f_df = [row for row in fairness_data if row.get("service_type") == service]
    s_df = [row for row in signals_data if row.get("service_type") == service]

    if not f_df:
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found in fairness metrics")

    city_p50 = sorted(row["p50_hr"] for row in f_df)[len(f_df) // 2]
    city_p90 = f_df[0].get("city_p90_hr", 0)
    total_incidents = sum(int(row.get("N", 0)) for row in f_df)

    city_context = {
        "service_type": service,
        "time_window": {"historical": "last_6_months", "live": "last_7_days"},
        "city_baselines": {"p50_hr": float(city_p50), "p90_hr": float(city_p90)},
        "service_volume": int(total_incidents),
    }

    signals_by_neighborhood = {row.get("neighborhood"): row for row in s_df}
    neighborhoods_list = []
    severities = []

    for row in f_df:
        neighborhood = row.get("neighborhood")
        signals = signals_by_neighborhood.get(neighborhood, {})
        backlog_p = signals.get("backlog_pressure", 0.0) or 0.0
        ratio_p90 = row.get("ratio_p90", 0.0) or 0.0
        severity = ratio_p90 * (1 + backlog_p)
        severities.append(severity)

        neighborhoods_list.append(
            {
                "neighborhood": neighborhood,
                "fairness_metrics": {
                    "p50_hr": row.get("p50_hr"),
                    "p90_hr": row.get("p90_hr"),
                    "ratio_p90": ratio_p90,
                    "rank": int(row.get("rank", 0)),
                    "worst_k_flag": bool(row.get("worst_k_flag", False)),
                },
                "signals": {
                    "backlog_pressure": backlog_p,
                    "aging_tail_14d": signals.get("aging_tail_14d", 0.0),
                    "duplicate_rate": signals.get("duplicate_rate", 0.0),
                    "mislabel_rate": signals.get("mislabel_rate", 0.0),
                    "agency_fragmentation": signals.get("agency_fragmentation"),
                },
                "severity_score": float(severity),
            }
        )

    worst_neighborhoods = [n["neighborhood"] for n in neighborhoods_list if n["fairness_metrics"]["worst_k_flag"]]
    median_severity = sorted(severities)[len(severities) // 2] if severities else 0
    priority_neighborhoods = [n["neighborhood"] for n in neighborhoods_list if n["severity_score"] > median_severity]

    max_severity = max(severities) if severities else 0
    if max_severity < 1.5:
        overall = "low"
    elif max_severity <= 3.0:
        overall = "medium"
    else:
        overall = "high"

    derived_insights = {
        "worst_neighborhoods": worst_neighborhoods,
        "priority_neighborhoods": priority_neighborhoods,
        "overall_severity": overall,
    }

    return {
        "city_context": city_context,
        "neighborhoods": neighborhoods_list,
        "governance": GOVERNANCE,
        "policy_space": POLICY_SPACE,
        "derived_insights": derived_insights,
    }


def _sse_event(event: str, payload: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _agent_message(agent: str, content: str, turn: int, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "agent": agent,
        "content": content,
        "turn": turn,
        "payload": payload,
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/services")
async def list_services():
    fairness = _load_json(DATA_DIR / "fairness_metrics.json")
    services = _get_services_from_fairness(fairness)
    return {"services": services}


@app.get("/intake/summary")
async def intake_summary():
    df = _load_incidents()
    if df.empty:
        return {"totals": {}, "by_service": []}

    total_tickets = len(df)
    canonical = df["canonical_incident_id"].nunique() if "canonical_incident_id" in df else df["incident_id"].nunique()
    duplicates = df["is_duplicate"].mean() * 100 if "is_duplicate" in df else 0.0
    mislabels_fixed = int((df.get("service_type_confidence", pd.Series([])) < 1.0).sum())
    redactions = _count_redactions(df.get("pii_flags", pd.Series([])))

    by_service = (
        df.groupby("service_type")
        .agg(
            total_tickets=("incident_id", "count"),
            canonical_incidents=("canonical_incident_id", "nunique"),
            duplicates=("is_duplicate", "mean"),
        )
        .reset_index()
    )
    by_service["duplicates"] = (by_service["duplicates"].fillna(0) * 100).round(2)

    return {
        "totals": {
            "total_tickets": int(total_tickets),
            "canonical_incidents": int(canonical),
            "duplicate_pct": float(round(duplicates, 2)),
            "mislabels_fixed": int(mislabels_fixed),
            "redactions": int(redactions),
        },
        "by_service": by_service.to_dict(orient="records"),
    }


@app.get("/metrics/fairness")
async def get_fairness(service: Optional[str] = Query(default=None)):
    fairness = _load_json(DATA_DIR / "fairness_metrics.json")
    if service:
        fairness = [row for row in fairness if row.get("service_type") == service]
    return {"service": service, "metrics": fairness}


@app.get("/fairness_metrics")
async def get_fairness_legacy(service: Optional[str] = Query(default=None)):
    return await get_fairness(service)


@app.get("/state/city")
async def get_city_state_for_service(service: Optional[str] = Query(default=None)):
    fairness = _load_json(DATA_DIR / "fairness_metrics.json")
    signals = _load_json(DATA_DIR / "neighborhood_signals.json")
    services = _get_services_from_fairness(fairness)
    if not services:
        raise HTTPException(status_code=404, detail="No services available in fairness metrics")
    service = service or services[0]
    return _build_city_state(service, fairness, signals)


@app.get("/city_state")
async def get_city_state_legacy(service: Optional[str] = Query(default=None)):
    return await get_city_state_for_service(service)


@app.post("/simulate", response_model=SimulateResponse)
async def simulate_policy(request: SimulateRequest):
    try:
        result = run_simulator(
            {"policy_id": request.policy_id, "parameters": request.parameters.model_dump()}
        )
        return SimulateResponse(**result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {exc}")


@app.post("/verify", response_model=VerifyResponse)
async def verify_policy(request: VerifyRequest):
    try:
        verdict = run_verifier(request.policy_result.model_dump())
        return VerifyResponse(**verdict)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=f"Verification failed: {exc}")


@app.post("/refresh")
async def refresh_zone2():
    try:
        return run_refresh()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {exc}")


@app.post("/sim/run")
async def run_sim_and_verify(request: SimRunRequest, service: str = Query(...)):
    scenario_results = []
    verifier_outputs = []

    for policy in request.policies:
        if "policy_id" not in policy or "parameters" not in policy:
            raise HTTPException(status_code=400, detail="Each policy requires policy_id and parameters")
        sim_result = run_simulator(policy)
        scenario_results.append(sim_result)
        verdict = run_verifier(sim_result)
        verifier_outputs.append(verdict)

    return {"service": service, "scenario_results": scenario_results, "verifier_outputs": verifier_outputs}


@app.post("/agents/propose")
async def agent_propose(request: AgentProposeRequest):
    policies = propose_policies(request.city_state)
    return {"policies": [p.model_dump() for p in policies]}


@app.post("/agents/redteam")
async def agent_redteam(payload: Dict[str, Any]):
    service = payload.get("service", "")
    result = redteam_review(service, payload)
    policy_id = payload.get("policy_id") or payload.get("policy", {}).get("policy_id")
    if policy_id:
        (EXPORTS_DIR / f"{policy_id}.redteam.json").write_text(result.model_dump_json(indent=2))
    return {"result": result.model_dump()}


@app.post("/agents/memo")
async def agent_memo(payload: Dict[str, Any]):
    service = payload.get("service", "")
    result = build_memo(service, payload)
    policy_id = payload.get("policy_id") or payload.get("policy", {}).get("policy_id")
    if policy_id:
        (EXPORTS_DIR / f"{policy_id}.memo.json").write_text(result.model_dump_json(indent=2))
    return {"result": result.model_dump()}


@app.post("/agents/workflow")
async def agent_workflow(request: AgentWorkflowRequest):
    """
    End-to-end agentic workflow:
    city_state -> propose -> sim -> verify -> pick best -> redteam -> memo.
    """
    if request.city_state:
        city_state = request.city_state
        service = request.service or city_state.get("city_context", {}).get("service_type", "")
    else:
        service = request.service
        if not service:
            raise HTTPException(status_code=400, detail="Provide service or city_state")
        fairness = _load_json(DATA_DIR / "fairness_metrics.json")
        signals = _load_json(DATA_DIR / "neighborhood_signals.json")
        city_state = _build_city_state(service, fairness, signals)

    policies = propose_policies(city_state)
    policy_payloads = [p.model_dump() for p in policies]

    scenario_results = []
    verifier_outputs = []
    for policy in policy_payloads:
        sim_result = run_simulator(policy)
        scenario_results.append(sim_result)
        verifier_outputs.append(run_verifier(sim_result))

    passing = [v for v in verifier_outputs if v.get("pass")]
    chosen = passing[0] if passing else (verifier_outputs[0] if verifier_outputs else None)
    chosen_policy = None
    if chosen:
        chosen_policy = next(
            (p for p in policy_payloads if p.get("policy_id") == chosen.get("policy_id")),
            None,
        )

    redteam_payload = {
        "service": service,
        "city_state": city_state,
        "sim_results": scenario_results,
        "verifier_results": verifier_outputs,
    }
    redteam = redteam_review(service, redteam_payload)

    memo_payload = {
        "service": service,
        "city_state": city_state,
        "chosen_policy": chosen_policy,
        "sim_results": scenario_results,
        "verifier_results": verifier_outputs,
        "redteam_report": redteam.model_dump(),
    }
    memo = build_memo(service, memo_payload)

    return {
        "service": service,
        "policies": policy_payloads,
        "scenario_results": scenario_results,
        "verifier_outputs": verifier_outputs,
        "chosen_policy": chosen_policy,
        "redteam": redteam.model_dump(),
        "memo": memo.model_dump(),
    }


@app.get("/agents/stream")
async def agents_stream(service: Optional[str] = Query(default=None)):
    """
    Stream multi-agent dialogue over SSE.
    """
    def event_stream():
        turn = 1
        try:
            if not service:
                fairness = _load_json(DATA_DIR / "fairness_metrics.json")
                services = _get_services_from_fairness(fairness)
                if not services:
                    raise RuntimeError("No services available")
                active_service = services[0]
            else:
                active_service = service

            yield _sse_event(
                "message",
                _agent_message(
                    "System",
                    f"Launching agentic workflow for service '{active_service}'.",
                    turn,
                ),
            )
            turn += 1

            fairness = _load_json(DATA_DIR / "fairness_metrics.json")
            signals = _load_json(DATA_DIR / "neighborhood_signals.json")
            city_state = _build_city_state(active_service, fairness, signals)

            proposer_prompt = (
                "You are the Proposer agent. Generate 3-5 policy candidates for the city service. "
                "Return a short conversational summary of the ideas you are considering. "
                "Then output a JSON array in a separate paragraph labelled POLICIES_JSON. "
                f"City state:\n{json.dumps(city_state, indent=2)}"
            )
            proposer_text = chat(
                messages=[
                    {"role": "system", "content": "You are an expert policy strategist."},
                    {"role": "user", "content": proposer_prompt},
                ],
                temperature=0.35,
                max_tokens=1200,
            )
            yield _sse_event(
                "message",
                _agent_message("Proposer", proposer_text, turn, {"city_state": city_state}),
            )
            turn += 1

            policies = propose_policies(city_state)
            policy_payloads = [p.model_dump() for p in policies]
            yield _sse_event(
                "message",
                _agent_message(
                    "System",
                    f"Proposer produced {len(policy_payloads)} policies. Running simulation + verification.",
                    turn,
                    {"policies": policy_payloads},
                ),
            )
            turn += 1

            scenario_results = []
            verifier_outputs = []
            for policy in policy_payloads:
                sim_result = run_simulator(policy)
                scenario_results.append(sim_result)
                verifier_outputs.append(run_verifier(sim_result))

            checker_prompt = (
                "You are the Constitution Checker agent. Review the verification results and summarize which "
                "policies pass or fail and why. Provide 2-3 bullet observations in a conversational tone. "
                f"Verification results:\n{json.dumps(verifier_outputs, indent=2)}"
            )
            checker_text = chat(
                messages=[
                    {"role": "system", "content": "You enforce policy constraints."},
                    {"role": "user", "content": checker_prompt},
                ],
                temperature=0.2,
                max_tokens=900,
            )
            yield _sse_event(
                "message",
                _agent_message(
                    "Constitution Checker",
                    checker_text,
                    turn,
                    {"verifier_outputs": verifier_outputs},
                ),
            )
            turn += 1

            refinement_prompt = (
                "You are the Proposer agent. Based on the constitution feedback, "
                "suggest one refinement or alternative policy direction in 2-3 bullets. "
                f"Verification feedback:\n{json.dumps(verifier_outputs, indent=2)}"
            )
            refinement_text = chat(
                messages=[
                    {"role": "system", "content": "You iterate on policy proposals."},
                    {"role": "user", "content": refinement_prompt},
                ],
                temperature=0.3,
                max_tokens=600,
            )
            yield _sse_event(
                "message",
                _agent_message(
                    "Proposer",
                    refinement_text,
                    turn,
                    {"policies": policy_payloads},
                ),
            )
            turn += 1

            checker_round2 = chat(
                messages=[
                    {"role": "system", "content": "You enforce policy constraints."},
                    {
                        "role": "user",
                        "content": (
                            "Respond to the proposer refinement in 2-3 bullets. "
                            "Flag any remaining constitutional risks."
                        ),
                    },
                ],
                temperature=0.2,
                max_tokens=500,
            )
            yield _sse_event(
                "message",
                _agent_message(
                    "Constitution Checker",
                    checker_round2,
                    turn,
                ),
            )
            turn += 1

            passing = [v for v in verifier_outputs if v.get("pass")]
            chosen = passing[0] if passing else (verifier_outputs[0] if verifier_outputs else None)
            chosen_policy = None
            if chosen:
                chosen_policy = next(
                    (p for p in policy_payloads if p.get("policy_id") == chosen.get("policy_id")),
                    None,
                )

            redteam_payload = {
                "service": active_service,
                "city_state": city_state,
                "sim_results": scenario_results,
                "verifier_results": verifier_outputs,
                "chosen_policy": chosen_policy,
            }
            redteam = redteam_review(active_service, redteam_payload)
            redteam_text = chat(
                messages=[
                    {"role": "system", "content": "You are a skeptical red-team auditor."},
                    {
                        "role": "user",
                        "content": (
                            "Summarize red-team risks and mitigations in 3-5 bullets. "
                            f"Red-team report:\n{redteam.model_dump_json(indent=2)}"
                        ),
                    },
                ],
                temperature=0.25,
                max_tokens=700,
            )
            yield _sse_event(
                "message",
                _agent_message(
                    "Red Team",
                    redteam_text,
                    turn,
                    {"redteam": redteam.model_dump()},
                ),
            )
            turn += 1

            memo_payload = {
                "service": active_service,
                "city_state": city_state,
                "chosen_policy": chosen_policy,
                "sim_results": scenario_results,
                "verifier_results": verifier_outputs,
                "redteam_report": redteam.model_dump(),
            }
            memo = build_memo(active_service, memo_payload)
            memo_text = chat(
                messages=[
                    {"role": "system", "content": "You write concise executive memos."},
                    {
                        "role": "user",
                        "content": (
                            "Write a short conversational wrap-up of the final memo. "
                            f"Memo:\n{memo.model_dump_json(indent=2)}"
                        ),
                    },
                ],
                temperature=0.2,
                max_tokens=700,
            )
            yield _sse_event(
                "message",
                _agent_message(
                    "System",
                    memo_text,
                    turn,
                    {"memo": memo.model_dump(), "chosen_policy": chosen_policy},
                ),
            )
            turn += 1

            yield _sse_event(
                "done",
                {
                    "service": active_service,
                    "policies": policy_payloads,
                    "scenario_results": scenario_results,
                    "verifier_outputs": verifier_outputs,
                    "chosen_policy": chosen_policy,
                    "redteam": redteam.model_dump(),
                    "memo": memo.model_dump(),
                },
            )
        except Exception as exc:
            yield _sse_event(
                "error",
                {"message": str(exc)},
            )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/exports/policy-package")
async def export_policy_package(service: str = Query(...), policy_id: str = Query(...)):
    package: Dict[str, Any] = {"service": service, "policy_id": policy_id}
    try:
        package["scenario_results"] = _load_json(DATA_DIR / "scenario_results.json")
    except FileNotFoundError:
        package["scenario_results"] = []
    try:
        package["verifier_outputs"] = _load_json(DATA_DIR / "verifier_outputs.json")
    except FileNotFoundError:
        package["verifier_outputs"] = []

    memo_path = EXPORTS_DIR / f"{policy_id}.memo.json"
    redteam_path = EXPORTS_DIR / f"{policy_id}.redteam.json"
    package["memo"] = json.loads(memo_path.read_text()) if memo_path.exists() else None
    package["redteam"] = json.loads(redteam_path.read_text()) if redteam_path.exists() else None

    payload = json.dumps(package, indent=2)
    headers = {"Content-Disposition": f"attachment; filename=policy_{policy_id}.json"}
    return StreamingResponse(iter([payload]), media_type="application/json", headers=headers)


@app.get("/exports/memo")
async def export_memo(service: str = Query(...), policy_id: str = Query(...)):
    memo_path = EXPORTS_DIR / f"{policy_id}.memo.json"
    if not memo_path.exists():
        raise HTTPException(status_code=404, detail="Memo not found for policy")
    headers = {"Content-Disposition": f"attachment; filename=memo_{policy_id}.json"}
    return StreamingResponse(iter([memo_path.read_text()]), media_type="application/json", headers=headers)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
