import json
import logging
from typing import Dict

from pydantic import ValidationError

try:
    from pydantic import TypeAdapter
except ImportError:  # pragma: no cover
    TypeAdapter = None

from api.nemotron_client import chat
from agents.schemas import MemoOutput

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


def _validate(payload) -> MemoOutput:
    if TypeAdapter is not None:
        return TypeAdapter(MemoOutput).validate_python(payload)
    return MemoOutput.model_validate(payload)


def build_memo(service: str, payload: Dict) -> MemoOutput:
    prompt = (
        "Return JSON only with keys summary (array of bullets) and memo (string). "
        f"Service: {service}. Payload:\n{json.dumps(payload, indent=2)}"
    )
    for attempt in range(2):
        content = chat(
            messages=[
                {"role": "system", "content": "Strict JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1200,
        )
        payload_json = _extract_json(content)
        if payload_json is None:
            logger.warning("Memo output not JSON. Attempt %s.", attempt + 1)
            continue
        try:
            return _validate(payload_json)
        except ValidationError as exc:
            logger.warning("Memo output failed validation: %s", exc)

    return MemoOutput(
        summary=["Model output invalid; fallback applied."],
        memo="Re-run memo after fixing Nemotron output.",
    )
