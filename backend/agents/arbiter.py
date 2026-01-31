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
from agents.schemas import MemoOutput

logger = logging.getLogger(__name__)


def _extract_json(text: str):
    if text is None:
        return None
    # Strip markdown code blocks
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

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


def _validate(payload) -> MemoOutput:
    if TypeAdapter is not None:
        return TypeAdapter(MemoOutput).validate_python(payload)
    return MemoOutput.model_validate(payload)


def _build_prompt(service: str, payload: Dict[str, Any]) -> str:
    city_state = payload.get("city_state") or {}
    evidence_cards = build_city_evidence_pack(city_state) if city_state else []
    constitution_cards = build_constitution_cards(city_state) if city_state else []
    playbook_cards = retrieve_playbook(city_state) if city_state else []
    retrieved_cards = retrieve_evidence_cards(city_state) if city_state else []
    return (
        f"Write an exec memo for service \"{service}\". Use the selected policy + evidence.\n"
        "Output schema:\n"
        "{\"summary\":[\"bullet\",...], \"memo\":\"string\"}\n"
        "Memo must include:\n"
        "- what changed (parameters)\n"
        "- expected equity impact (worst-k)\n"
        "- citywide impact\n"
        "- whether constitution passed; if fail, top blockers + next iteration\n"
        "- 1 sentence on operational feasibility\n"
        f"EVIDENCE_CARDS: {json.dumps(evidence_cards, indent=2)}\n"
        f"CONSTITUTION_CARDS: {json.dumps(constitution_cards, indent=2)}\n"
        f"PLAYBOOK_CARDS: {json.dumps(playbook_cards, indent=2)}\n"
        f"RETRIEVED_CARDS: {json.dumps(retrieved_cards, indent=2)}\n"
        f"INPUT_JSON: {json.dumps(payload, indent=2)}\n"
        "REMEMBER: Output ONLY valid JSON. No markdown."
    )


def _attempt_generate(
    service: str,
    payload: Dict[str, Any],
    history: List[Dict[str, str]] | None = None,
) -> Tuple[MemoOutput | None, str, Any]:
    prompt = _build_prompt(service, payload)
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": "You are an executive policy writer. CRITICAL: Output must be ONLY valid JSON. Do NOT use markdown code blocks. No intro or outro."},
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})
    content = chat(messages=messages, temperature=0.2, max_tokens=4096)
    payload_json = _extract_json(content)
    if payload_json is None:
        return None, content, None
    try:
        return _validate(payload_json), content, payload_json
    except ValidationError as exc:
        logger.warning("Memo output failed validation: %s", exc)
        return None, content, payload_json


def build_memo_with_debug(
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
        logger.warning("Memo output not valid JSON. Attempt %s.", attempt + 1)

    fallback = MemoOutput(
        summary=["Model output invalid; fallback applied."],
        memo="Re-run memo after fixing Nemotron output.",
    )
    return {
        "result": fallback,
        "raw_text": last_raw,
        "parsed_json": fallback.model_dump(),
        "validation_status": "fallback",
        "error_payload": last_payload,
    }


def build_memo(
    service: str,
    payload: Dict,
    history: List[Dict[str, str]] | None = None,
) -> MemoOutput:
    result = build_memo_with_debug(service, payload, history)
    return result["result"]
