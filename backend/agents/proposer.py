import json
import logging
from typing import Any, Dict, List

from pydantic import ValidationError

try:
    from pydantic import TypeAdapter
except ImportError:  # pragma: no cover
    TypeAdapter = None

from api.nemotron_client import chat
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


def propose_policies(city_state: Dict[str, Any]) -> List[PolicyProposal]:
    policy_space = city_state.get("policy_space", {})
    prompt = (
        "Return a JSON array of policy objects, nothing else. "
        "Each item must include policy_id and parameters "
        "(capacity_shift_pct, efficiency_bonus_pct, max_reassignments), plus a short rationale. "
        "Use the policy_space and governance constraints. City state:\n"
        f"{json.dumps(city_state, indent=2)}"
    )

    for attempt in range(2):
        content = chat(
            messages=[
                {"role": "system", "content": "Strict JSON only. Output a JSON array and nothing else."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1200,
        )
        payload = _extract_json(content)
        if payload is None:
            logger.warning("Nemotron output not JSON. Attempt %s.", attempt + 1)
            continue
        try:
            return _validate_policies(payload)
        except ValidationError as exc:
            logger.warning("Nemotron output failed validation: %s", exc)

    return _safe_baseline(policy_space)
