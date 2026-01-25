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
from agents.schemas import RedTeamOutput

logger = logging.getLogger(__name__)


def _extract_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None


def _validate(payload) -> RedTeamOutput:
    if TypeAdapter is not None:
        return TypeAdapter(RedTeamOutput).validate_python(payload)
    return RedTeamOutput.model_validate(payload)


def _build_prompt(service: str, payload: Dict[str, Any]) -> str:
    city_state = payload.get("city_state") or {}
    evidence_cards = build_city_evidence_pack(city_state) if city_state else []
    constitution_cards = build_constitution_cards(city_state) if city_state else []
    playbook_cards = retrieve_playbook(city_state) if city_state else []
    retrieved_cards = retrieve_evidence_cards(city_state) if city_state else []
    return (
        f"Service: \"{service}\"\n"
        "Evaluate the proposed policies and their sim+verify results.\n"
        "Focus on: fairness regressions, backlog growth, constraint gaming, operational risks.\n"
        "Output schema:\n"
        "{\"risks\":[...], \"recommendations\":[...]}\n"
        "Rules:\n"
        "- Risks must cite at least one concrete signal/constraint name "
        "(e.g., \"max_backlog_growth\", \"min_worst_k_improvement\").\n"
        "- Recommendations must be actionable changes to parameters or process.\n"
        f"EVIDENCE_CARDS: {json.dumps(evidence_cards, indent=2)}\n"
        f"CONSTITUTION_CARDS: {json.dumps(constitution_cards, indent=2)}\n"
        f"PLAYBOOK_CARDS: {json.dumps(playbook_cards, indent=2)}\n"
        f"RETRIEVED_CARDS: {json.dumps(retrieved_cards, indent=2)}\n"
        f"INPUT_JSON: {json.dumps(payload, indent=2)}"
    )


def _attempt_generate(
    service: str,
    payload: Dict[str, Any],
    history: List[Dict[str, str]] | None = None,
) -> Tuple[RedTeamOutput | None, str, Any]:
    prompt = _build_prompt(service, payload)
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": "You are the Red Team agent. Output ONLY JSON."},
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})
    content = chat(messages=messages, temperature=0.2, max_tokens=1000)
    payload_json = _extract_json(content)
    if payload_json is None:
        return None, content, None
    try:
        return _validate(payload_json), content, payload_json
    except ValidationError as exc:
        logger.warning("Redteam output failed validation: %s", exc)
        return None, content, payload_json


def redteam_review_with_debug(
    service: str,
    payload: Dict[str, Any],
    history: List[Dict[str, str]] | None = None,
) -> Dict[str, Any]:
    last_raw = ""
    last_payload = None
    for attempt in range(2):
        result, raw_text, parsed_payload = _attempt_generate(service, payload, history)
        last_raw = raw_text
        last_payload = parsed_payload
        if result is not None:
            return {
                "result": result,
                "raw_text": raw_text,
                "parsed_json": result.model_dump(),
                "validation_status": "valid",
            }
        logger.warning("Redteam output not valid JSON. Attempt %s.", attempt + 1)

    fallback = RedTeamOutput(
        risks=["Model output invalid; fallback applied."],
        recommendations=["Re-run redteam after fixing Nemotron output."],
    )
    return {
        "result": fallback,
        "raw_text": last_raw,
        "parsed_json": fallback.model_dump(),
        "validation_status": "fallback",
        "error_payload": last_payload,
    }


def redteam_review(
    service: str,
    payload: Dict,
    history: List[Dict[str, str]] | None = None,
) -> RedTeamOutput:
    result = redteam_review_with_debug(service, payload, history)
    return result["result"]
