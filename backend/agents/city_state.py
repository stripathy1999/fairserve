from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import HTTPException
from config.paths import DATA_DIR

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


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    with open(path, "r") as f:
        return json.load(f)


def get_services_from_fairness(fairness_data: List[Dict[str, Any]]) -> List[str]:
    services = {row.get("service_type") for row in fairness_data if row.get("service_type")}
    return sorted(services)


def build_city_state(
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

    worst_neighborhoods = [
        n["neighborhood"] for n in neighborhoods_list if n["fairness_metrics"]["worst_k_flag"]
    ]
    median_severity = sorted(severities)[len(severities) // 2] if severities else 0
    priority_neighborhoods = [
        n["neighborhood"] for n in neighborhoods_list if n["severity_score"] > median_severity
    ]

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
