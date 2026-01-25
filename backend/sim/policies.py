"""
Temporary policy file for API simulation.
"""

def get_default_policies():
    """Returns a list with only the requested policy."""
    return [{
        "policy_id": "baseline_policy",
        "parameters": {
                "capacity_shift_pct": 0.0,
                "efficiency_bonus_pct": 0.0,
                "max_reassignments": 0
        },
        "rationale": "Safe baseline policy."
}]

def validate_policy(policy):
    """Minimal validation for API usage."""
    return True, []
