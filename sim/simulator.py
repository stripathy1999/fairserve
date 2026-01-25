import pandas as pd
import json
import numpy as np
import policies

# --- Configuration ---
HISTORICAL_FILE = "data/processed/historical"
LIVE_FILE = "data/processed/live_stream"
CITY_STATE_FILE = "data/processed/city_state.json"
OUTPUT_FILE = "data/processed/scenario_results.json"

def main():
    # 1. Load Inputs
    try:
        hist_df = pd.read_parquet(HISTORICAL_FILE)
        with open(CITY_STATE_FILE, 'r') as f:
            city_state = json.load(f)
            
        # Optional Live Data
        try:
            live_df = pd.read_parquet(LIVE_FILE)
        except (FileNotFoundError, Exception):
            print("Live data not found or empty. Simulating with 0 initial backlog.")
            live_df = pd.DataFrame(columns=hist_df.columns)
            
    except Exception as e:
        print(f"Error loading inputs: {e}")
        return

    # Check for empty historical data
    if hist_df.empty:
        print("Historical data is empty. Cannot simulate.")
        return

    service_type = city_state['city_context']['service_type']
    neighborhoods_data = city_state['neighborhoods']
    
    # Extract budget context if available
    budget_context = city_state.get('budget_context', {})
    budget_per_incident = budget_context.get('budget_per_incident_estimate', 0.0)
    annual_budget = budget_context.get('annual_budget_usd', 0.0)
    
    print(f"Simulating for service: {service_type}")
    if budget_per_incident > 0:
        print(f"Budget per incident: ${budget_per_incident:,.2f}")

    # Parameters Estimation
    # Filter for service type
    hist_sv = hist_df[hist_df['service_type'] == service_type]
    live_sv = live_df[live_df['service_type'] == service_type] if not live_df.empty else pd.DataFrame(columns=hist_df.columns)
    
    # 2. Estimate baselines per neighborhood
    # arrival_rate (incidents/day) - HISTORICAL ONLY
    # capacity (closed/day) - HISTORICAL ONLY
    
    neighborhood_params = {}
    
    # Helper to get day span
    def get_span(df, date_col='opened_at'):
        if date_col not in df.columns: return 30
        if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
            df[date_col] = pd.to_datetime(df[date_col])
        span = (df[date_col].max() - df[date_col].min()).days
        return max(span, 1)

    hist_span = get_span(hist_sv, 'opened_at')
    
    # Get initial backlog from live data if available
    if not live_sv.empty:
        live_open = live_sv[live_sv['status'] == 'open']
        current_backlogs = live_open['neighborhood'].value_counts().to_dict()
    else:
        current_backlogs = {}

    for n_data in neighborhoods_data:
        name = n_data['neighborhood']
        
        # Arrival rate from historical ONLY
        n_hist = hist_sv[hist_sv['neighborhood'] == name]
        arrival_rate = len(n_hist) / hist_span
        
        # Capacity from closed historical ONLY
        n_closed = n_hist[n_hist['status'] == 'closed']
        capacity = len(n_closed) / hist_span
        
        neighborhood_params[name] = {
            "arrival_rate": arrival_rate,
            "baseline_capacity": capacity,
            "initial_backlog": current_backlogs.get(name, 0),
            "baseline_p90": n_data['fairness_metrics']['p90_hr'],
            "baseline_ratio": n_data['fairness_metrics']['ratio_p90']
        }

    # 3. Define Policies
    # Retrieve allowed policies from the policies module
    policies_list = policies.get_default_policies()

    results = []

    # 4. Simulation Loop
    HORIZON_DAYS = 30
    
    neighborhood_names = list(neighborhood_params.keys())
    
    # Identify "worst" and "best" for capacity shifting
    # Sort by baseline_ratio (ratio_p90)
    sorted_neighborhoods = sorted(neighborhood_names, key=lambda n: neighborhood_params[n]['baseline_ratio'], reverse=True)
    
    # Logic adjustment: Ensure we cover "Worst K" (3 of 5). 
    # Taking top ~60% as recipients to align with Worst K=3 protection.
    mid_point = int(np.ceil(len(sorted_neighborhoods) * 0.6))
    worst_half = sorted_neighborhoods[:mid_point]
    best_half = sorted_neighborhoods[mid_point:]

    for pol in policies_list:
        pid = pol['policy_id']
        params = pol['parameters']
        shift_pct = params['capacity_shift_pct']
        eff_bonus = params['efficiency_bonus_pct']
        
        # Calculate effective capacities
        # Total capacity in system
        total_capacity = sum(p['baseline_capacity'] for p in neighborhood_params.values())
        
        # Pool capacity to shift
        # We can implement shift as: reduce capacity of donors by X%, redistribute that pool to recipients
        capacity_pool = 0.0
        new_capacities = {}
        
        # 1. Apply efficiency bonus first
        base_caps = {n: p['baseline_capacity'] * (1 + eff_bonus) for n, p in neighborhood_params.items()}
        
        # 2. Collect pool from best half
        for n in best_half:
            contribution = base_caps[n] * shift_pct
            new_capacities[n] = base_caps[n] - contribution
            capacity_pool += contribution
            
        # 3. Redistribute to worst half (equally or weighted? Let's do equally for simplicity)
        if worst_half:
            share = capacity_pool / len(worst_half)
            for n in worst_half:
                new_capacities[n] = base_caps[n] + share
        else:
             # If no split possible, no shift
             for n in neighborhood_names:
                 new_capacities[n] = base_caps[n]

        # Simulator
        sim_effects = {}
        
        for n in neighborhood_names:
            p = neighborhood_params[n]
            # Baseline dynamics
            # backlog_t = backlog_{t-1} + arrival - capacity
            # integrated over 30 days:
            # final_backlog = initial + (arrival - capacity) * 30
            # Ensure backlog >= 0
            
            # Simple linear projection
            net_flow = p['arrival_rate'] - new_capacities[n]
            final_backlog = max(0, p['initial_backlog'] + net_flow * HORIZON_DAYS)
            
            # Compute backlog change
            baseline_backlog = p['initial_backlog']
            if baseline_backlog > 0:
                delta_backlog_pct = (final_backlog - baseline_backlog) / baseline_backlog
            else:
                delta_backlog_pct = 0.0 if final_backlog == 0 else 1.0 # 100% increase if started at 0
            
            # Response Time Proxy
            # proxy ~ backlog / capacity
            epsilon = 0.01
            # We want to map this to p90 change.
            # Relation: if backlog doubles, p90 roughly doubles (Little's Law proxy)
            # new_p90 = baseline_p90 * (new_rt_proxy / old_rt_proxy)
            
            old_rt_proxy = p['initial_backlog'] / (p['baseline_capacity'] + epsilon)
            new_rt_proxy = final_backlog / (new_capacities[n] + epsilon)
            
            if old_rt_proxy > 0:
                rt_change_ratio = new_rt_proxy / old_rt_proxy
            else:
                rt_change_ratio = 1.0
            
            new_p90 = p['baseline_p90'] * rt_change_ratio
            delta_p90 = (new_p90 - p['baseline_p90']) / p['baseline_p90'] if p['baseline_p90'] > 0 else 0.0
            
            # new ratio for equity calc
            # We need city_p90 for this... assume it changes similarly? 
            # Or keep city baseline fixed to see relative equity improvement?
            # Let's keep city baseline fixed for equity metric to see if gap closes.
            city_p90_baseline = city_state['city_context']['city_baselines']['p90_hr']
            new_ratio = new_p90 / city_p90_baseline if city_p90_baseline > 0 else 0.0
            
            sim_effects[n] = {
                "delta_p90": round(delta_p90, 4),
                "delta_backlog_pct": round(delta_backlog_pct, 4),
                "new_ratio": new_ratio
            }

        # Aggregated Metrics
        # Citywide delta p90 (avg of neighborhoods weighted? or just avg delta?)
        # Prompt says: citywide_delta_p90
        avg_delta = np.mean([e['delta_p90'] for e in sim_effects.values()])
        
        # Equity Improvement
        # (avg old ratio - avg new ratio) / avg old ratio 
        # Wait, if ratio drops it's good (gap closing).
        # Actually equity is often variance, but prompt defines it via ratio_p90
        # "avg old ratio" - "avg new ratio" -> positive means ratios got smaller (good)
        
        avg_old_ratio = np.mean([p['baseline_ratio'] for p in neighborhood_params.values()])
        avg_new_ratio = np.mean([e['new_ratio'] for e in sim_effects.values()])
        
        equity_imp = (avg_old_ratio - avg_new_ratio) / avg_old_ratio if avg_old_ratio > 0 else 0.0
        
        # Cleanup neighborhood effects for output
        clean_effects = {}
        for n, eff in sim_effects.items():
            clean_effects[n] = {k: v for k, v in eff.items() if k != "new_ratio"}
        
        # Budget Cost Metrics
        # estimated_policy_cost = capacity changes * budget_per_incident * horizon
        # Approximate: sum of absolute backlog changes * budget_per_incident
        total_backlog_change = sum(abs(neighborhood_params[n]['initial_backlog'] * sim_effects[n]['delta_backlog_pct']) 
                                   for n in neighborhood_names)
        estimated_cost = total_backlog_change * budget_per_incident if budget_per_incident > 0 else 0.0
        
        # equity_per_million
        equity_per_million = (equity_imp / (estimated_cost / 1_000_000)) if estimated_cost > 0 else 0.0
        
        # budget_stress_ratio
        budget_stress_ratio = (estimated_cost / annual_budget) if annual_budget > 0 else 0.0

        results.append({
            "policy_id": pid,
            "parameters": params,
            "neighborhood_effects": clean_effects,
            "citywide_delta_p90": round(avg_delta, 4),
            "equity_improvement": round(equity_imp, 4),
            "estimated_policy_cost": round(estimated_cost, 2),
            "equity_per_million": round(equity_per_million, 4),
            "budget_stress_ratio": round(budget_stress_ratio, 4)
        })

    # Output
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Simulation completed. {len(policies_list)} policies tested across {len(neighborhood_names)} neighborhoods.")
    print(f"Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
