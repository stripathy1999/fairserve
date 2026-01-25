import json
import logging
from typing import Any, Dict, List, Tuple

from pydantic import ValidationError

try:
    from pydantic import TypeAdapter
except ImportError:  # pragma: no cover
    TypeAdapter = None

from api.nemotron_client import chat
from agents.rag import (
    build_city_evidence_pack,
    build_constitution_cards,
    retrieve_evidence_cards,
    retrieve_playbook,
)
from agents.schemas import PolicyParameters, PolicyProposal

logger = logging.getLogger(__name__)


def _extract_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None


def _validate_policies(payload) -> List[PolicyProposal]:
    if TypeAdapter is not None:
        adapter = TypeAdapter(List[PolicyProposal])
        return adapter.validate_python(payload)
    return [PolicyProposal.model_validate(item) for item in payload]


def _safe_baseline(policy_space: Dict[str, Any]) -> List[PolicyProposal]:
    params = policy_space or {}
    cap_min, cap_max = params.get("capacity_shift_pct", [0.0, 0.3])
    eff_min, eff_max = params.get("efficiency_bonus_pct", [0.0, 0.1])
    reas_min, reas_max = params.get("max_reassignments", [0, 3])

    baseline = PolicyParameters(
        capacity_shift_pct=float(cap_min),
        efficiency_bonus_pct=float(eff_min),
        max_reassignments=int(reas_min),
    )
    return [PolicyProposal(policy_id="baseline_policy", parameters=baseline, rationale="Safe baseline policy.")]


def _build_prompt(city_state: Dict[str, Any]) -> str:
    city_context = city_state.get("city_context", {})
    policy_space = city_state.get("policy_space", {})
    governance = city_state.get("governance", {})
    derived_insights = city_state.get("derived_insights", {})
    neighborhoods = city_state.get("neighborhoods", [])
    neighborhoods_subset = [
        {
            "neighborhood": n.get("neighborhood"),
            "fairness_metrics": n.get("fairness_metrics"),
            "signals": n.get("signals"),
            "severity_score": n.get("severity_score"),
        }
        for n in neighborhoods
    ]
    evidence_cards = build_city_evidence_pack(city_state)
    constitution_cards = build_constitution_cards(city_state)
    playbook_cards = retrieve_playbook(city_state)
    retrieved_cards = retrieve_evidence_cards(city_state)
    input_json = {
        "city_context": city_context,
        "policy_space": policy_space,
        "governance": governance,
        "derived_insights": derived_insights,
        "neighborhoods": neighborhoods_subset,
        "evidence_cards": evidence_cards,
        "constitution_cards": constitution_cards,
        "policy_playbook": playbook_cards,
        "retrieved_cards": retrieved_cards,
    }
    service = city_context.get("service_type", "unknown")

    return (
        "Create 3 to 5 policy candidates for service = "
        f"\"{service}\".\n"
        "Use ONLY the allowed parameter knobs and ranges from policy_space below.\n"
        "Respect governance constraints in governance.\n"
        "Use evidence_cards + policy_playbook for grounding and parameter choices.\n"
        "Output schema (JSON array):\n"
        "[{\"policy_id\": \"string\", \"parameters\": {\"capacity_shift_pct\": number, "
        "\"efficiency_bonus_pct\": number, \"max_reassignments\": integer}, \"rationale\": \"string\"}]\n"
        "Hard rules:\n"
        "- capacity_shift_pct in [0.0, 0.30]\n"
        "- efficiency_bonus_pct in [0.0, 0.20]\n"
        "- max_reassignments in {0,1,2,3}\n"
        "- Do NOT output any other fields.\n"
        "- If unsure, still output valid JSON that fits the schema.\n"
        "- Rationale must cite evidence ids from retrieved_cards (e.g., EVID_WORST_NEIGHBORHOODS, "
        "GOV_CONSTRAINTS, PLAYBOOK_BACKLOG_SHOCK_ABSORBER).\n"
        f"INPUT_JSON: {json.dumps(input_json, indent=2)}"
    )


def _attempt_generate(
    city_state: Dict[str, Any],
    history: List[Dict[str, str]] | None = None,
) -> Tuple[List[PolicyProposal] | None, str, Any]:
    prompt = _build_prompt(city_state)
    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are the Policy Proposer agent for a city ops system.\n"
                "Output must be ONLY valid JSON. No markdown. No commentary. No extra keys. No preamble."
            ),
        }
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})
    content = chat(messages=messages, temperature=0.3, max_tokens=1200)
    payload = _extract_json(content)
    if payload is None:
        return None, content, None
    try:
        return _validate_policies(payload), content, payload
    except ValidationError as exc:
        logger.warning("Nemotron output failed validation: %s", exc)
        return None, content, payload


def propose_policies_with_debug(
    city_state: Dict[str, Any],
    history: List[Dict[str, str]] | None = None,
) -> Dict[str, Any]:
    policy_space = city_state.get("policy_space", {})
    last_raw = ""
    last_payload = None
    for attempt in range(2):
        policies, raw_text, payload = _attempt_generate(city_state, history)
        last_raw = raw_text
        last_payload = payload
        if policies is not None:
            return {
                "policies": policies,
                "raw_text": raw_text,
                "parsed_json": [p.model_dump() for p in policies],
                "validation_status": "valid",
            }
        logger.warning("Nemotron output not valid JSON. Attempt %s.", attempt + 1)

    fallback = _safe_baseline(policy_space)
    return {
        "policies": fallback,
        "raw_text": last_raw,
        "parsed_json": [p.model_dump() for p in fallback],
        "validation_status": "fallback",
        "error_payload": last_payload,
    }


def propose_policies(
    city_state: Dict[str, Any],
    history: List[Dict[str, str]] | None = None,
) -> List[PolicyProposal]:
    result = propose_policies_with_debug(city_state, history)
    return result["policies"]
