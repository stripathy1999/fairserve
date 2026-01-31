"""
Helper functions to safely invoke existing Zone-2 scripts via subprocess.
"""

import subprocess
import json
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


# Project root (assuming api/ is at project root)
# Project root (assuming api/ is at backend root, and data is sibling of backend)
BACKEND_ROOT = Path(__file__).parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"


def run_simulator(policy_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run simulator.py with a custom policy and return only that policy's result.
    
    Strategy:
    1. Temporarily modify sim/policies.py to include only the requested policy
    2. Run simulator.py
    3. Extract and return only the requested policy result from scenario_results.json
    4. Restore original policies.py
    
    Args:
        policy_dict: Dictionary with 'policy_id' and 'parameters'
        
    Returns:
        Single policy result dictionary
        
    Raises:
        RuntimeError: If simulation fails
        FileNotFoundError: If required input files are missing
    """
    
    # Backup original policies.py
    policies_file = BACKEND_ROOT / "sim" / "policies.py"
    backup_file = BACKEND_ROOT / "sim" / "policies.py.bak"
    
    try:
        # Create backup
        with open(policies_file, 'r') as f:
            original_content = f.read()
        
        # Create temporary policies.py with only the requested policy
        temp_policies_content = f'''"""
Temporary policy file for API simulation.
"""

def get_default_policies():
    """Returns a list with only the requested policy."""
    return [{json.dumps(policy_dict, indent=8)}]

def validate_policy(policy):
    """Minimal validation for API usage."""
    return True, []
'''
        
        with open(policies_file, 'w') as f:
            f.write(temp_policies_content)
        
        # Run simulator
        result = subprocess.run(
            ["python", "sim/simulator.py"],
            cwd=BACKEND_ROOT,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Simulator failed: {result.stderr}")
        
        # Read results
        results_file = DATA_DIR / "scenario_results.json"
        if not results_file.exists():
            print(f"Simulator stdout: {result.stdout}")
            print(f"Simulator stderr: {result.stderr}")
            raise FileNotFoundError(f"Simulator did not produce {results_file}. Output: {result.stdout}")
        
        with open(results_file, 'r') as f:
            all_results = json.load(f)
        
        # Extract only our policy result
        policy_id = policy_dict['policy_id']
        policy_result = next((r for r in all_results if r['policy_id'] == policy_id), None)
        
        if not policy_result:
            raise RuntimeError(f"Policy {policy_id} not found in simulation results")
        
        return policy_result
        
    finally:
        # Restore original policies.py
        with open(policies_file, 'w') as f:
            f.write(original_content)


def run_batch_simulator(policies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Run simulator.py for a batch of policies efficiently.
    
    Args:
        policies: List of policy dictionaries
        
    Returns:
        List of simulation result dictionaries
    """
    if not policies:
        return []

    # Create temporary policies input file
    temp_policies_file = BACKEND_ROOT / "temp_policies_input.json"
    
    try:
        with open(temp_policies_file, 'w') as f:
            json.dump(policies, f, indent=2)
        
        # Run simulator with --policies argument
        result = subprocess.run(
            ["python", "sim/simulator.py", "--policies", str(temp_policies_file)],
            cwd=BACKEND_ROOT,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            print(f"Simulator stdout: {result.stdout}")
            print(f"Simulator stderr: {result.stderr}")
            raise RuntimeError(f"Simulator batch failed: {result.stderr}")
        
        # Read results
        results_file = DATA_DIR / "scenario_results.json"
        if not results_file.exists():
            raise FileNotFoundError(f"Simulator did not produce {results_file} from batch run. Output: {result.stdout}")
        
        with open(results_file, 'r') as f:
            all_results = json.load(f)
            
        return all_results
        
    finally:
        # Cleanup temp file
        if temp_policies_file.exists():
            try:
                os.remove(temp_policies_file)
            except OSError:
                pass


def run_verifier(policy_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run verifier.py on a single policy result and return the verdict.
    
    Strategy:
    1. Write policy_result to scenario_results.json (temporarily)
    2. Run verifier.py
    3. Extract and return verdict for this policy
    4. Restore original scenario_results.json
    
    Args:
        policy_result: Single policy simulation result
        
    Returns:
        Verification verdict dictionary
        
    Raises:
        RuntimeError: If verification fails
    """
    
    scenario_file = DATA_DIR / "scenario_results.json"
    backup_file = DATA_DIR / "scenario_results.json.bak"
    
    try:
        # Backup original scenario_results.json if it exists
        original_content = None
        if scenario_file.exists():
            with open(scenario_file, 'r') as f:
                original_content = f.read()
        
        # Write temporary scenario_results.json with only this policy
        with open(scenario_file, 'w') as f:
            json.dump([policy_result], f, indent=2)
        
        # Run verifier
        result = subprocess.run(
            ["python", "sim/verifier.py"],
            cwd=BACKEND_ROOT,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Verifier failed: {result.stderr}")
        
        # Read verdict
        verifier_file = DATA_DIR / "verifier_outputs.json"
        if not verifier_file.exists():
            raise FileNotFoundError(f"Verifier did not produce {verifier_file}")
        
        with open(verifier_file, 'r') as f:
            verdicts = json.load(f)
        
        # Extract verdict for our policy
        policy_id = policy_result['policy_id']
        verdict = next((v for v in verdicts if v['policy_id'] == policy_id), None)
        
        if not verdict:
            raise RuntimeError(f"Verdict for policy {policy_id} not found")
        
        return verdict
        
    finally:
        # Restore original scenario_results.json
        if original_content:
            with open(scenario_file, 'w') as f:
                f.write(original_content)


def run_refresh() -> Dict[str, Any]:
    """
    Refresh all Zone-2 outputs by running the pipeline sequentially.
    
    Pipeline:
    1. compute_fairness_metrics.py
    2. compute_neighborhood_signals.py
    3. build_city_state.py
    
    Returns:
        Status dictionary with timestamp and steps completed
        
    Raises:
        RuntimeError: If any step fails
    """
    
    steps = [
        ("metrics/compute_fairness_metrics.py", "Fairness Metrics"),
        ("metrics/compute_neighborhood_signals.py", "Neighborhood Signals"),
        ("state/build_city_state.py", "City State")
    ]
    
    completed = []
    
    for script_path, step_name in steps:
        result = subprocess.run(
            ["python", script_path],
            cwd=BACKEND_ROOT,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"{step_name} failed: {result.stderr}")
        
        completed.append(step_name)
    
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "steps_completed": completed,
        "message": f"Successfully refreshed {len(completed)} Zone-2 outputs"
    }


def check_required_files() -> tuple[bool, List[str]]:
    """
    Check if all required Zone-2 output files exist.
    
    Returns:
        Tuple of (all_exist: bool, missing_files: List[str])
    """
    
    required_files = [
        "fairness_metrics.json",
        "neighborhood_signals.json",
        "city_state.json"
    ]
    
    missing = []
    for filename in required_files:
        filepath = DATA_DIR / filename
        if not filepath.exists():
            missing.append(str(filepath))
    
    return len(missing) == 0, missing
