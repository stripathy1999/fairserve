"""
FairServe Zone 2 Policy Definition Module.

This module defines the allowed search space for policies, provides default
policy templates, and includes validation logic to enforce constraints.
"""

# 1. Define Policy Knobs
# Allowed parameter ranges and descriptions
POLICY_KNOBS = {
<<<<<<< HEAD
    "capacity_shift_pct": { #How much capacity can we reallocate from well-served neighborhoods to under-served ones?
=======
    "capacity_shift_pct": {
>>>>>>> c9de744 (Refactor fairness metrics and simulator for strict historical/live data separation and robustness)
        "type": float,
        "min": 0.0,
        "max": 0.30,
        "description": "Fraction of capacity shifted from best-off to worst-off neighborhoods."
    },
<<<<<<< HEAD
    "efficiency_bonus_pct": { #How much efficiency can we realistically gain without adding staff?
=======
    "efficiency_bonus_pct": {
>>>>>>> c9de744 (Refactor fairness metrics and simulator for strict historical/live data separation and robustness)
        "type": float,
        "min": 0.0,
        "max": 0.20,
        "description": "System-wide efficiency gain from batching and routing improvements."
    },
<<<<<<< HEAD
    "max_reassignments": { #How many times can a ticket bounce before we stop moving it?
=======
    "max_reassignments": {
>>>>>>> c9de744 (Refactor fairness metrics and simulator for strict historical/live data separation and robustness)
        "type": int,
        "min": 0,
        "max": 3,
        "description": "Limit on ticket reassignments to prevent aging loops."
    }
}

def get_default_policies():
    """Returns a list of default policy dictionaries."""
    return [
        {
            "policy_id": "Baseline",
            "parameters": {
                "capacity_shift_pct": 0.0,
                "efficiency_bonus_pct": 0.0,
                "max_reassignments": 0
            }
        },
        {
            "policy_id": "Efficiency_Boost",
            "parameters": {
                "capacity_shift_pct": 0.0,
                "efficiency_bonus_pct": 0.16,
                "max_reassignments": 0
            }
        },
        {
            "policy_id": "Equity_Shift",
            "parameters": {
                "capacity_shift_pct": 0.2,
                "efficiency_bonus_pct": 0.0,
                "max_reassignments": 1
            }
        },
        {
            "policy_id": "Balanced_Reform",
            "parameters": {
                "capacity_shift_pct": 0.04,
                "efficiency_bonus_pct": 0.12,
                "max_reassignments": 2
            }
        }
    ]

def validate_policy(policy):
    """
    Validates a policy dictionary against POLICY_KNOBS constraints.
    
    Args:
        policy (dict): The policy dictionary containing 'parameters'.
        
    Returns:
        tuple: (bool, list of str) -> (is_valid, error_messages)
    """
    errors = []
    
    if "parameters" not in policy:
        return False, ["Missing 'parameters' key in policy."]
        
    params = policy["parameters"]
    
    # Check for unknown parameters
    for key in params:
        if key not in POLICY_KNOBS:
            errors.append(f"Unknown parameter: {key}")
            
    # Check each defined knob
    for knob, rules in POLICY_KNOBS.items():
        if knob not in params:
            errors.append(f"Missing required parameter: {knob}")
            continue
            
        value = params[knob]
        expected_type = rules["type"]
        
        # Type check (handle float/int overlap if necessary, but strict is safer)
        if not isinstance(value, expected_type):
            # Allow int for float, but clean it up if needed? 
            # Standard Python isinstance check:
            if expected_type == float and isinstance(value, int):
                pass # Int is acceptable for float parameter
            else:
                errors.append(f"Parameter '{knob}' has wrong type. Expected {expected_type.__name__}, got {type(value).__name__}.")
                continue
        
        # Range check
        if value < rules["min"] or value > rules["max"]:
            errors.append(f"Parameter '{knob}' value {value} out of range. Allowed: [{rules['min']}, {rules['max']}].")
            
    return len(errors) == 0, errors
