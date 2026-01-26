
import datetime
import glob
import json
import logging
import os
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.models import SimulateRequest, SimulateResponse, VerifyRequest, VerifyResponse
from api.nemotron_client import chat, health_check as nemotron_health_check
from api.runner import run_refresh, run_simulator, run_verifier
from api.scoring import rank_policies
from agents.arbiter import build_memo, build_memo_with_debug
from agents.city_state import DATA_DIR, build_city_state, get_services_from_fairness, load_json
from agents.proposer import propose_policies, propose_policies_with_debug
from agents.rag import retrieve_evidence_cards
from agents.redteam import redteam_review, redteam_review_with_debug

try:
    from intake.process_live import run_scheduler
    from trigger.discord_bot import run_bot
except ImportError:
    # Fallback/Retry if direct import fails
    from backend.intake.process_live import run_scheduler
    from backend.trigger.discord_bot import run_bot
    
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="FairServe Zone-2 Gateway",
    description="Gateway API for FairServe Zone-2 outputs and agents",
    version="1.0.0",
)
zone2_app = app
LIVE_DATA_DIR = os.path.join(PROJECT_ROOT, "data/processed/live_stream")

cors_env = os.getenv("CORS_ORIGIN", "http://localhost:3000,http://localhost:8004,http://localhost:8005")
cors_origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EXPORTS_DIR = DATA_DIR / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

INCIDENT_FILES = [
    DATA_DIR / "incidents_historical.parquet",
    DATA_DIR / "incidents_live.parquet",
]

LIVE_DATA_DIR = DATA_DIR / "live_stream"


class SimRunRequest(BaseModel):
    policies: List[Dict[str, Any]]


class AgentProposeRequest(BaseModel):
    city_state: Dict[str, Any]


class AgentWorkflowRequest(BaseModel):
    service: Optional[str] = None
    city_state: Optional[Dict[str, Any]] = None


class AgentStreamRequest(BaseModel):
    service: Optional[str] = None


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


def _sse_event(event: str, payload: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _agent_message(agent: str, content: str, turn: int, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "agent": agent,
        "content": content,
        "turn": turn,
        "payload": payload,
    }

def _append_history(
    history: Dict[str, List[Dict[str, str]]],
    agent: str,
    role: str,
    content: str,
) -> None:
    history.setdefault(agent, []).append({"role": role, "content": content})


def _messages_for_agent(
    history: Dict[str, List[Dict[str, str]]],
    agent: str,
    system_prompt: str,
    user_prompt: str,
) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    messages.extend(history.get(agent, []))
    messages.append({"role": "user", "content": user_prompt})
    return messages


def _record_turn(
    history: Dict[str, List[Dict[str, str]]],
    agent: str,
    user_prompt: str,
    assistant_reply: str,
) -> None:
    _append_history(history, agent, "user", user_prompt)
    _append_history(history, agent, "assistant", assistant_reply)


@app.get("/health")
async def api_health_check():
    return {"status": "ok"}

@app.post("/visual-incident")
async def create_visual_incident(file: UploadFile = File(...)):
    """
    Generate an incident from an uploaded image/video using Nemotron VL.
    """
    if not process_visual_upload:
        return {"error": "Image processing module not available."}
        
    try:
        content = await file.read()
        result = process_visual_upload(content, file.filename)
        
        if "incident" in result:
            incident_data = result["incident"]
            print(incident_data)
            
            # Persist to Queue (JSON)
            QUEUE_DIR = os.path.join(PROJECT_ROOT, "data/queue")
            if not os.path.exists(QUEUE_DIR):
                os.makedirs(QUEUE_DIR, exist_ok=True)
                
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            import uuid
            unique_id = uuid.uuid4().hex[:6]
            file_name = f"visual_{timestamp}_{unique_id}.json"
            file_path = os.path.join(QUEUE_DIR, file_name)
            
            with open(file_path, 'w') as f:
                json.dump(incident_data, f)
            
            # Return path for debug/confirmation
            result["storage_path"] = file_path
            result["status"] = "Queued for processing"
            
        return result
            
        return result
    except Exception as e:
        return {"error": f"Failed to process upload: {str(e)}"}


@app.get("/live")
async def get_live_data(limit: int = 50, minutes_back: int = 60):
    """
    Retrieve recent live incident batches.

    - **limit**: Max number of records to return.
    - **minutes_back**: Look back this many minutes for data files.
    """
    if not LIVE_DATA_DIR.exists():
        return {"data": [], "message": "No live data directory found."}

    files = list(LIVE_DATA_DIR.glob("*.parquet"))
    cutoff_time = datetime.datetime.now() - datetime.timedelta(minutes=minutes_back)
    relevant_files = [
        f for f in files if datetime.datetime.fromtimestamp(f.stat().st_mtime) >= cutoff_time
    ]

    if not relevant_files:
        return {"data": [], "message": f"No data found in the last {minutes_back} minutes."}

    dfs = []
    for path in relevant_files:
        try:
            dfs.append(pd.read_parquet(path))
        except Exception as exc:
            logger.warning("Error reading %s: %s", path, exc)
            continue

    if not dfs:
        return {"data": []}

    full_df = pd.concat(dfs, ignore_index=True)
    if "opened_at" in full_df.columns:
        full_df["opened_at"] = pd.to_datetime(full_df["opened_at"])
        full_df = full_df.sort_values(by="opened_at", ascending=False)

    result_df = full_df.head(limit)
    data = result_df.to_dict(orient="records")
    return {"data": data, "count": len(data), "total_available": len(full_df)}


@app.get("/services")
async def list_services():
    fairness = load_json(DATA_DIR / "fairness_metrics.json")
    services = get_services_from_fairness(fairness)
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
    fairness = load_json(DATA_DIR / "fairness_metrics.json")
    if service:
        fairness = [row for row in fairness if row.get("service_type") == service]
    return {"service": service, "metrics": fairness}


@app.get("/fairness_metrics")
async def get_fairness_legacy(service: Optional[str] = Query(default=None)):
    return await get_fairness(service)


@app.get("/state/city")
async def get_city_state_for_service(service: Optional[str] = Query(default=None)):
    fairness = load_json(DATA_DIR / "fairness_metrics.json")
    signals = load_json(DATA_DIR / "neighborhood_signals.json")
    services = get_services_from_fairness(fairness)
    if not services:
        raise HTTPException(status_code=404, detail="No services available in fairness metrics")
    service = service or services[0]
    return build_city_state(service, fairness, signals)


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
    result = propose_policies_with_debug(request.city_state)
    return {
        "raw_text": result["raw_text"],
        "parsed_json": result["parsed_json"],
        "validation_status": result["validation_status"],
    }


@app.get("/agents/evidence")
async def agent_evidence(service: Optional[str] = Query(default=None)):
    fairness = load_json(DATA_DIR / "fairness_metrics.json")
    signals = load_json(DATA_DIR / "neighborhood_signals.json")
    services = get_services_from_fairness(fairness)
    if not services:
        raise HTTPException(status_code=404, detail="No services available in fairness metrics")
    active_service = service or services[0]
    city_state = build_city_state(active_service, fairness, signals)
    return {
        "service": active_service,
        "retrieved_cards": retrieve_evidence_cards(city_state),
    }


@app.post("/agents/redteam")
async def agent_redteam(payload: Dict[str, Any]):
    service = payload.get("service", "")
    result = redteam_review_with_debug(service, payload)
    redteam = result["result"]
    policy_id = payload.get("policy_id") or payload.get("policy", {}).get("policy_id")
    if policy_id:
        (EXPORTS_DIR / f"{policy_id}.redteam.json").write_text(redteam.model_dump_json(indent=2))
    return {
        "raw_text": result["raw_text"],
        "parsed_json": result["parsed_json"],
        "validation_status": result["validation_status"],
    }


@app.post("/agents/memo")
async def agent_memo(payload: Dict[str, Any]):
    service = payload.get("service", "")
    result = build_memo_with_debug(service, payload)
    memo = result["result"]
    policy_id = payload.get("policy_id") or payload.get("policy", {}).get("policy_id")
    if policy_id:
        (EXPORTS_DIR / f"{policy_id}.memo.json").write_text(memo.model_dump_json(indent=2))
    return {
        "raw_text": result["raw_text"],
        "parsed_json": result["parsed_json"],
        "validation_status": result["validation_status"],
    }


@app.get("/agents/health")
async def agent_health():
    ok = nemotron_health_check()
    return {"ok": ok}


@app.post("/agents/workflow")
async def agent_workflow(request: AgentWorkflowRequest):
    if request.city_state:
        city_state = request.city_state
        service = request.service or city_state.get("city_context", {}).get("service_type", "")
    else:
        service = request.service
        if not service:
            raise HTTPException(status_code=400, detail="Provide service or city_state")
        fairness = load_json(DATA_DIR / "fairness_metrics.json")
        signals = load_json(DATA_DIR / "neighborhood_signals.json")
        city_state = build_city_state(service, fairness, signals)

    policies = propose_policies(city_state)
    policy_payloads = [p.model_dump() for p in policies]

    scenario_results = []
    verifier_outputs = []
    for policy in policy_payloads:
        sim_result = run_simulator(policy)
        scenario_results.append(sim_result)
        verifier_outputs.append(run_verifier(sim_result))

    ranked = rank_policies(scenario_results, verifier_outputs, city_state)
    chosen_policy = ranked[0]["policy"] if ranked else None

    redteam_payload = {
        "service": service,
        "city_state": city_state,
        "retrieved_cards": retrieve_evidence_cards(city_state),
        "ranked_policies": ranked,
        "sim_results": scenario_results,
        "verifier_results": verifier_outputs,
    }
    redteam = redteam_review(service, redteam_payload)

    memo_payload = {
        "service": service,
        "city_state": city_state,
        "chosen_policy": chosen_policy,
        "ranked_policies": ranked,
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
        "ranked_policies": ranked,
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
        history: Dict[str, List[Dict[str, str]]] = {}
        try:
            if not service:
                fairness = load_json(DATA_DIR / "fairness_metrics.json")
                services = get_services_from_fairness(fairness)
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

            fairness = load_json(DATA_DIR / "fairness_metrics.json")
            signals = load_json(DATA_DIR / "neighborhood_signals.json")
            city_state = build_city_state(active_service, fairness, signals)

            proposer_prompt = (
                "You are the Proposer agent. Generate 3-5 policy candidates for the city service. "
                "Return a short conversational summary of the ideas you are considering. "
                "Then output a JSON array in a separate paragraph labelled POLICIES_JSON. "
                f"City state:\n{json.dumps(city_state, indent=2)}"
            )
            proposer_text = chat(
                messages=_messages_for_agent(
                    history,
                    "Proposer",
                    "You are an expert policy strategist.",
                    proposer_prompt,
                ),
                temperature=0.35,
                max_tokens=1200,
            )
            _record_turn(history, "Proposer", proposer_prompt, proposer_text)
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
                messages=_messages_for_agent(
                    history,
                    "Constitution Checker",
                    "You enforce policy constraints.",
                    checker_prompt,
                ),
                temperature=0.2,
                max_tokens=900,
            )
            _record_turn(history, "Constitution Checker", checker_prompt, checker_text)
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
                messages=_messages_for_agent(
                    history,
                    "Proposer",
                    "You iterate on policy proposals.",
                    refinement_prompt,
                ),
                temperature=0.3,
                max_tokens=600,
            )
            _record_turn(history, "Proposer", refinement_prompt, refinement_text)
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

            checker_round2_prompt = (
                "Respond to the proposer refinement in 2-3 bullets. "
                "Flag any remaining constitutional risks."
            )
            checker_round2 = chat(
                messages=_messages_for_agent(
                    history,
                    "Constitution Checker",
                    "You enforce policy constraints.",
                    checker_round2_prompt,
                ),
                temperature=0.2,
                max_tokens=500,
            )
            _record_turn(history, "Constitution Checker", checker_round2_prompt, checker_round2)
            yield _sse_event(
                "message",
                _agent_message(
                    "Constitution Checker",
                    checker_round2,
                    turn,
                ),
            )
            turn += 1

            ranked = rank_policies(scenario_results, verifier_outputs, city_state)
            chosen_policy = ranked[0]["policy"] if ranked else None

            redteam_payload = {
                "service": active_service,
                "city_state": city_state,
                "retrieved_cards": retrieve_evidence_cards(city_state),
                "ranked_policies": ranked,
                "sim_results": scenario_results,
                "verifier_results": verifier_outputs,
                "chosen_policy": chosen_policy,
            }
            redteam = redteam_review(active_service, redteam_payload, history.get("Red Team"))
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
            _record_turn(
                history,
                "Red Team",
                f"Review payload:\n{json.dumps(redteam_payload, indent=2)}",
                redteam_text,
            )
            turn += 1

            memo_payload = {
                "service": active_service,
                "city_state": city_state,
                "chosen_policy": chosen_policy,
                "ranked_policies": ranked,
                "sim_results": scenario_results,
                "verifier_results": verifier_outputs,
                "redteam_report": redteam.model_dump(),
            }
            memo = build_memo(active_service, memo_payload, history.get("Memo"))
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
            _record_turn(
                history,
                "Memo",
                f"Memo payload:\n{json.dumps(memo_payload, indent=2)}",
                memo_text,
            )
            turn += 1

            yield _sse_event(
                "done",
                {
                    "service": active_service,
                    "policies": policy_payloads,
                    "scenario_results": scenario_results,
                    "verifier_outputs": verifier_outputs,
                    "ranked_policies": ranked,
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
        package["scenario_results"] = load_json(DATA_DIR / "scenario_results.json")
    except FileNotFoundError:
        package["scenario_results"] = []
    try:
        package["verifier_outputs"] = load_json(DATA_DIR / "verifier_outputs.json")
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
    uvicorn.run(app, host="0.0.0.0", port=8083)
