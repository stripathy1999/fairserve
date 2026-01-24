
import json

# --- Configuration ---
SCENARIO_RESULTS_FILE = "data/processed/scenario_results.json"
CITY_STATE_FILE = "data/processed/city_state.json"
OUTPUT_FILE = "data/processed/verifier_outputs.json"

def main():
    # 1. Load Inputs
    try:
        with open(SCENARIO_RESULTS_FILE, 'r') as f:
            scenarios = json.load(f)
        with open(CITY_STATE_FILE, 'r') as f:
            city_state = json.load(f)
    except FileNotFoundError as e:
        print(f"Error loading inputs: {e}")
        return
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return

    # Extract Constitution
    governance = city_state.get('governance', {})
    constraints = governance.get('constraints', {})
    
    # Thresholds
    MIN_IMPROVEMENT = constraints.get('min_worst_k_improvement', 0.15)
    MAX_HARM = constraints.get('max_neighborhood_harm', 0.05)
    MAX_BACKLOG = constraints.get('max_backlog_growth', 0.10)
    NO_CITY_WORSEN = constraints.get('citywide_p90_must_not_worsen', True)
    
    # Identify Worst-K Neighborhoods
    worst_k_list = city_state.get('derived_insights', {}).get('worst_neighborhoods', [])
    
    verdicts = []
    
    for policy in scenarios:
        pid = policy.get('policy_id', 'unknown')
        effects = policy.get('neighborhood_effects', {})
        city_delta = policy.get('citywide_delta_p90', 0.0)
        
        violations = []
        
        # A. Worst-off Improvement Rule
        # delta_p90 <= -MIN_IMPROVEMENT (i.e. improvement of at least X%)
        for n in worst_k_list:
            if n in effects:
                delta = effects[n].get('delta_p90', 0.0)
                # Improvement means negative delta. 
                # e.g. -0.2 <= -0.15 (True, passed)
                target = -MIN_IMPROVEMENT
                if delta > target:
                    violations.append({
                        "constraint": "min_worst_k_improvement",
                        "neighborhood": n,
                        "observed": delta,
                        "allowed": target
                    })
        
        # B. No Excessive Harm Rule
        # delta_p90 <= MAX_HARM
        for n, metrics in effects.items():
            delta = metrics.get('delta_p90', 0.0)
            if delta > MAX_HARM:
                violations.append({
                    "constraint": "max_neighborhood_harm",
                    "neighborhood": n,
                    "observed": delta,
                    "allowed": MAX_HARM
                })
        
        # C. Backlog Growth Rule
        # delta_backlog_pct <= MAX_BACKLOG
        for n, metrics in effects.items():
            delta_b = metrics.get('delta_backlog_pct', 0.0)
            if delta_b > MAX_BACKLOG:
                violations.append({
                    "constraint": "max_backlog_growth",
                    "neighborhood": n,
                    "observed": delta_b,
                    "allowed": MAX_BACKLOG
                })

        # D. Citywide Performance Rule
        # citywide_delta_p90 <= 0
        if NO_CITY_WORSEN and city_delta > 0:
             violations.append({
                "constraint": "citywide_p90_must_not_worsen",
                "neighborhood": "CITYWIDE",
                "observed": city_delta,
                "allowed": 0.0
            })
            
        # Verdict
        passed = len(violations) == 0
        
        verdicts.append({
            "policy_id": pid,
            "pass": passed,
            "violations": violations
        })

    # Output
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(verdicts, f, indent=2)

    # Summary
    passed_count = sum(1 for v in verdicts if v['pass'])
    total = len(verdicts)
    print(f"Evaluated {total} policies. {passed_count} passed, {total - passed_count} failed.")
    print(f"Verdicts saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
