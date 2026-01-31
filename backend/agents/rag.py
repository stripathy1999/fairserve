from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from config.paths import PROCESSED_DIR

PLAYBOOK_PATH = Path(__file__).parent / "policy_playbook.json"


def _load_optional_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def build_city_evidence_pack(city_state: Dict[str, Any], max_neighborhoods: int = 8) -> List[Dict[str, Any]]:
    neighborhoods = city_state.get("neighborhoods", [])
    sorted_by_ratio = sorted(
        neighborhoods,
        key=lambda n: (n.get("fairness_metrics", {}).get("ratio_p90") or 0),
        reverse=True,
    )
    top_neighborhoods = sorted_by_ratio[:max_neighborhoods]

    fairness_metrics = _load_optional_json(PROCESSED_DIR / "fairness_metrics.json")
    intake_summary = _load_optional_json(PROCESSED_DIR / "intake_summary.json")

    cards = [
        {
            "id": "EVID_CITY_CONTEXT",
            "title": "City context",
            "type": "city_state",
            "data": city_state.get("city_context", {}),
        },
        {
            "id": "EVID_WORST_NEIGHBORHOODS",
            "title": "Worst neighborhoods (by ratio_p90)",
            "type": "neighborhoods",
            "data": [
                {
                    "neighborhood": n.get("neighborhood"),
                    "fairness_metrics": n.get("fairness_metrics"),
                    "signals": n.get("signals"),
                    "severity_score": n.get("severity_score"),
                }
                for n in top_neighborhoods
            ],
        },
        {
            "id": "EVID_DERIVED_INSIGHTS",
            "title": "Derived insights",
            "type": "derived_insights",
            "data": city_state.get("derived_insights", {}),
        },
    ]

    if fairness_metrics is not None:
        cards.append(
            {
                "id": "EVID_FAIRNESS_METRICS",
                "title": "Fairness metrics (summary sample)",
                "type": "fairness_metrics",
                "data": fairness_metrics[: min(25, len(fairness_metrics))],
            }
        )
    if intake_summary is not None:
        cards.append(
            {
                "id": "EVID_INTAKE_SUMMARY",
                "title": "Intake summary",
                "type": "intake_summary",
                "data": intake_summary,
            }
        )

    return cards


def build_constitution_cards(city_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    governance = city_state.get("governance", {})
    policy_space = city_state.get("policy_space", {})
    return [
        {
            "id": "GOV_CONSTRAINTS",
            "title": "Governance constraints",
            "type": "governance",
            "data": governance,
        },
        {
            "id": "GOV_POLICY_SPACE",
            "title": "Policy space",
            "type": "policy_space",
            "data": policy_space,
        },
        {
            "id": "GOV_INTERPRETATION",
            "title": "Constraint interpretation",
            "type": "explain",
            "data": {
                "min_worst_k_improvement": "Worst-k neighborhoods must improve by the minimum threshold.",
                "max_neighborhood_harm": "No neighborhood can worsen beyond the harm threshold.",
                "max_backlog_growth": "Backlog growth must stay below the cap.",
                "citywide_p90_must_not_worsen": "Citywide p90 must not increase.",
            },
        },
    ]


def load_policy_playbook() -> List[Dict[str, Any]]:
    if not PLAYBOOK_PATH.exists():
        return []
    return json.loads(PLAYBOOK_PATH.read_text())


def _collect_signal_summary(city_state: Dict[str, Any]) -> Dict[str, float]:
    neighborhoods = city_state.get("neighborhoods", [])
    ratios = []
    backlog = []
    aging = []
    dupes = []
    mislabels = []
    worst_k = 0

    for n in neighborhoods:
        fm = n.get("fairness_metrics", {})
        sig = n.get("signals", {})
        ratios.append(fm.get("ratio_p90", 0.0) or 0.0)
        backlog.append(sig.get("backlog_pressure", 0.0) or 0.0)
        aging.append(sig.get("aging_tail_14d", 0.0) or 0.0)
        dupes.append(sig.get("duplicate_rate", 0.0) or 0.0)
        mislabels.append(sig.get("mislabel_rate", 0.0) or 0.0)
        if fm.get("worst_k_flag"):
            worst_k += 1

    city_baselines = city_state.get("city_context", {}).get("city_baselines", {})
    return {
        "worst_k_count": float(worst_k),
        "worst_k_ratio_p90": max(ratios) if ratios else 0.0,
        "avg_ratio_p90": sum(ratios) / len(ratios) if ratios else 0.0,
        "max_backlog_pressure": max(backlog) if backlog else 0.0,
        "avg_backlog_pressure": sum(backlog) / len(backlog) if backlog else 0.0,
        "max_aging_tail_14d": max(aging) if aging else 0.0,
        "avg_duplicate_rate": sum(dupes) / len(dupes) if dupes else 0.0,
        "avg_mislabel_rate": sum(mislabels) / len(mislabels) if mislabels else 0.0,
        "citywide_p90": float(city_baselines.get("p90_hr", 0.0) or 0.0),
    }


def _rule_match(value: float, op: str, threshold: float) -> bool:
    if op == ">=":
        return value >= threshold
    if op == ">":
        return value > threshold
    if op == "<=":
        return value <= threshold
    if op == "<":
        return value < threshold
    if op == "==":
        return value == threshold
    return False


def retrieve_playbook(city_state: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    playbook = load_policy_playbook()
    if not playbook:
        return []
    signals = _collect_signal_summary(city_state)

    scored = []
    for entry in playbook:
        rules = entry.get("signal_rules", [])
        score = 0
        for rule in rules:
            signal_name = rule.get("signal")
            if signal_name not in signals:
                continue
            value = signals[signal_name]
            if _rule_match(value, rule.get("op", ">="), float(rule.get("value", 0))):
                score += 1
        scored.append((score, entry))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [entry for score, entry in scored[:limit] if score > 0] or [
        entry for _, entry in scored[:limit]
    ]


def _cards_to_documents(cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    docs = []
    for card in cards:
        text = f"{card.get('title')}\n{json.dumps(card.get('data', {}), indent=2)}"
        docs.append(
            {
                "id": card.get("id", card.get("title", "card")),
                "text": text,
                "type": card.get("type", "evidence"),
            }
        )
    return docs


def _playbook_to_documents(playbook: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    docs = []
    for entry in playbook:
        entry_id = entry.get("id") or entry.get("name", "playbook").upper().replace(" ", "_")
        docs.append(
            {
                "id": f"PLAYBOOK_{entry_id}",
                "text": json.dumps(entry, indent=2),
                "type": "playbook",
            }
        )
    return docs


def _simple_embed(text: str) -> Dict[str, int]:
    tokens = []
    for raw in text.lower().replace("/", " ").replace("_", " ").split():
        token = "".join(ch for ch in raw if ch.isalnum())
        if token:
            tokens.append(token)
    vec: Dict[str, int] = {}
    for token in tokens:
        vec[token] = vec.get(token, 0) + 1
    return vec


def _cosine(a: Dict[str, int], b: Dict[str, int]) -> float:
    if not a or not b:
        return 0.0
    dot = 0.0
    a_norm = 0.0
    b_norm = 0.0
    for key, value in a.items():
        a_norm += value * value
        if key in b:
            dot += value * b[key]
    for value in b.values():
        b_norm += value * value
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return dot / ((a_norm ** 0.5) * (b_norm ** 0.5))


def _build_queries(signal_summary: Dict[str, float]) -> List[str]:
    queries = [
        "What patterns address max_backlog_growth violations without killing equity?",
        "Given worst_k neighborhoods and backlog_pressure signals, which playbook patterns apply?",
        "What parameter regimes reduce backlog growth while preserving worst-k improvement?",
    ]
    if signal_summary.get("max_backlog_pressure", 0) >= 1.0:
        queries.append("How to reduce backlog pressure in worst-k neighborhoods?")
    if signal_summary.get("worst_k_ratio_p90", 0) >= 1.5:
        queries.append("What policies improve worst-k ratio_p90 without violating harm constraints?")
    return queries


def retrieve_evidence_cards(city_state: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    evidence_cards = build_city_evidence_pack(city_state)
    constitution_cards = build_constitution_cards(city_state)
    playbook_cards = retrieve_playbook(city_state, limit=10)

    documents = (
        _cards_to_documents(evidence_cards)
        + _cards_to_documents(constitution_cards)
        + _playbook_to_documents(playbook_cards)
    )
    signal_summary = _collect_signal_summary(city_state)
    queries = _build_queries(signal_summary)

    scored: Dict[str, Dict[str, Any]] = {}
    for query in queries:
        q_vec = _simple_embed(query)
        for doc in documents:
            d_vec = _simple_embed(doc["text"])
            score = _cosine(q_vec, d_vec)
            if doc["id"] not in scored or score > scored[doc["id"]]["score"]:
                scored[doc["id"]] = {
                    "id": doc["id"],
                    "snippet": doc["text"][:240],
                    "why_retrieved": query,
                    "score": score,
                    "type": doc.get("type"),
                }

    ranked = sorted(scored.values(), key=lambda item: item["score"], reverse=True)
    return ranked[:limit]
