from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

BACKEND_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = Path(__file__).resolve().parents[4]

# Add backend root to path for imports like 'agents', 'api'
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

# Add project root to path for imports like 'backend.config'
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Import centralized configuration
from config.paths import PROCESSED_DIR
import logging

logger = logging.getLogger(__name__)

from agents.arbiter import build_memo_with_debug
from agents.city_state import build_city_state, get_services_from_fairness, load_json
from agents.proposer import propose_policies_with_debug
from agents.rag import retrieve_evidence_cards
from agents.redteam import redteam_review_with_debug
from api.runner import run_simulator, run_verifier, run_batch_simulator
from api.scoring import rank_policies


def _coerce_input(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        # Unwrap nested payload if present (due to nat integration wrapper)
        if "payload" in payload and isinstance(payload["payload"], dict):
            return payload["payload"]
        return payload
    if isinstance(payload, str):
        try:
            decoded = json.loads(payload)
            if isinstance(decoded, dict):
                return decoded
        except json.JSONDecodeError:
            return {"service": payload}
    return {}


def _ensure_city_state(payload: Dict[str, Any]) -> Dict[str, Any]:
    if payload.get("city_state"):
        return payload

    fairness = load_json(PROCESSED_DIR / "fairness_metrics.json")
    signals = load_json(PROCESSED_DIR / "neighborhood_signals.json")

    service = payload.get("service")
    if not service:
        services = get_services_from_fairness(fairness)
        if not services:
            raise ValueError("No services available in fairness metrics.")
        service = services[0]
    payload["service"] = service
    payload["city_state"] = build_city_state(service, fairness, signals)
    return payload


def _choose_policy(
    policies: List[Dict[str, Any]],
    verifier_outputs: List[Dict[str, Any]],
) -> Dict[str, Any] | None:
    passing = [v for v in verifier_outputs if v.get("pass")]
    chosen = passing[0] if passing else (verifier_outputs[0] if verifier_outputs else None)
    if not chosen:
        return None
    return next((p for p in policies if p.get("policy_id") == chosen.get("policy_id")), None)


def propose_step(payload: Any) -> Dict[str, Any]:
    state = _ensure_city_state(_coerce_input(payload))
    logger.info(f"PROPOSE_STEP input keys: {list(state.keys())}")
    propose = propose_policies_with_debug(state["city_state"])
    state["policies"] = propose["parsed_json"]
    state.setdefault("retrieved_cards", retrieve_evidence_cards(state["city_state"]))
    state["propose"] = {
        "raw_text": propose["raw_text"],
        "parsed_json": propose["parsed_json"],
        "validation_status": propose["validation_status"],
    }
    return state


def retrieve_step(payload: Any) -> Dict[str, Any]:
    state = _ensure_city_state(_coerce_input(payload))
    state["retrieved_cards"] = retrieve_evidence_cards(state["city_state"])
    return state


def simulate_step(payload: Any) -> Dict[str, Any]:
    state = _coerce_input(payload)
    logger.info(f"SIMULATE_STEP input keys: {list(state.keys())}")
    policies = state.get("policies") or []
    # Batch execution for performance
    scenario_results = run_batch_simulator(policies)
    state["scenario_results"] = scenario_results
    return state


def verify_step(payload: Any) -> Dict[str, Any]:
    state = _coerce_input(payload)
    scenario_results = state.get("scenario_results") or []
    verifier_outputs = [run_verifier(result) for result in scenario_results]
    state["verifier_outputs"] = verifier_outputs
    return state


def rank_step(payload: Any) -> Dict[str, Any]:
    state = _coerce_input(payload)
    ranked = rank_policies(
        state.get("scenario_results") or [],
        state.get("verifier_outputs") or [],
        state.get("city_state") or {},
    )
    state["ranked_policies"] = ranked
    if ranked:
        state["chosen_policy"] = ranked[0]["policy"]
    return state


def redteam_step(payload: Any) -> Dict[str, Any]:
    state = _coerce_input(payload)
    logger.info(f"REDTEAM_STEP input keys: {list(state.keys())}")
    payload_map = {
        "service": state.get("service", ""),
        "city_state": state.get("city_state"),
        "retrieved_cards": state.get("retrieved_cards"),
        "ranked_policies": state.get("ranked_policies"),
        "policies": state.get("policies"),
        "sim_results": state.get("scenario_results"),
        "verifier_results": state.get("verifier_outputs"),
    }
    result = redteam_review_with_debug(state.get("service", ""), payload_map)
    state["redteam"] = {
        "raw_text": result["raw_text"],
        "parsed_json": result["parsed_json"],
        "validation_status": result["validation_status"],
    }
    return state


def memo_step(payload: Any) -> Dict[str, Any]:
    state = _coerce_input(payload)
    logger.info(f"MEMO_STEP input keys: {list(state.keys())}")
    chosen_policy = state.get("chosen_policy") or _choose_policy(
        state.get("policies") or [],
        state.get("verifier_outputs") or [],
    )
    payload_map = {
        "service": state.get("service", ""),
        "city_state": state.get("city_state"),
        "chosen_policy": chosen_policy,
        "ranked_policies": state.get("ranked_policies"),
        "sim_results": state.get("scenario_results"),
        "verifier_results": state.get("verifier_outputs"),
        "redteam_report": state.get("redteam", {}).get("parsed_json"),
    }
    result = build_memo_with_debug(state.get("service", ""), payload_map)
    state["chosen_policy"] = chosen_policy
    state["memo"] = {
        "raw_text": result["raw_text"],
        "parsed_json": result["parsed_json"],
        "validation_status": result["validation_status"],
    }
    return state
