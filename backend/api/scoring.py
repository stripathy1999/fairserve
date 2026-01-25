from __future__ import annotations

from typing import Any, Dict, List


def _backlog_growth_risk(
    scenario: Dict[str, Any],
    worst_k: List[str],
) -> float:
    effects = scenario.get("neighborhood_effects", {}) or {}
    risks = []
    for n in worst_k:
        metrics = effects.get(n, {})
        value = metrics.get("delta_backlog_pct")
        if value is not None:
            risks.append(float(value))
    if not risks:
        # fallback to max backlog across all neighborhoods
        for metrics in effects.values():
            value = metrics.get("delta_backlog_pct")
            if value is not None:
                risks.append(float(value))
    return max(risks) if risks else 0.0


def score_policy(
    scenario: Dict[str, Any],
    verdict: Dict[str, Any],
    city_state: Dict[str, Any],
    weights: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    weights = weights or {"equity": 1.0, "citywide": 1.0, "backlog": 0.5}
    violations = verdict.get("violations") or []
    if violations:
        return {
            "policy_id": scenario.get("policy_id"),
            "score": -1e9,
            "hard_fail": True,
            "components": {
                "equity_improvement": scenario.get("equity_improvement", 0.0),
                "citywide_delta_p90": scenario.get("citywide_delta_p90", 0.0),
                "backlog_growth_risk": None,
                "violations": len(violations),
            },
        }

    worst_k = city_state.get("derived_insights", {}).get("worst_neighborhoods", []) or []
    backlog_risk = _backlog_growth_risk(scenario, worst_k)
    equity = float(scenario.get("equity_improvement", 0.0) or 0.0)
    citywide = float(scenario.get("citywide_delta_p90", 0.0) or 0.0)
    score = (
        weights["equity"] * equity
        - weights["citywide"] * citywide
        - weights["backlog"] * backlog_risk
    )

    return {
        "policy_id": scenario.get("policy_id"),
        "score": round(score, 6),
        "hard_fail": False,
        "components": {
            "equity_improvement": equity,
            "citywide_delta_p90": citywide,
            "backlog_growth_risk": backlog_risk,
            "violations": len(violations),
        },
    }


def rank_policies(
    scenarios: List[Dict[str, Any]],
    verdicts: List[Dict[str, Any]],
    city_state: Dict[str, Any],
    weights: Dict[str, float] | None = None,
) -> List[Dict[str, Any]]:
    verdict_map = {v.get("policy_id"): v for v in verdicts}
    ranked = []
    for scenario in scenarios:
        pid = scenario.get("policy_id")
        verdict = verdict_map.get(pid, {"violations": ["missing verdict"]})
        score = score_policy(scenario, verdict, city_state, weights)
        ranked.append(
            {
                "policy_id": pid,
                "score": score["score"],
                "hard_fail": score["hard_fail"],
                "components": score["components"],
                "policy": scenario,
            }
        )
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked
