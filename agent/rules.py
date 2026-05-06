"""
Rules layer — Policy-as-Code.
Evaluates fulfillment-specific constraints like budget and maintenance windows.
Simulates an Open Policy Agent (OPA) / Rego evaluation layer by decoupling 
hardcoded logic and strictly relying on the declarative JSON configurations.
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

def evaluate_all_fulfillment_rules(request: dict, user: dict, item: dict) -> dict:
    """
    The main entry point called by harness.py.
    Checks blackout windows (using request time, not system time) and spending limits.
    """
    return {
        "blackout_window": _check_blackouts(request),
        "budget_override": _check_budget(user, item)
    }

def _check_blackouts(request: dict) -> dict:
    """
    Dynamic Freeze Windows: Checks if the request's submitted_at time 
    falls within a restricted window.
    
    Fixes the 'Race Condition' vulnerability of checking datetime.utcnow()
    which would allow users to 'beat the clock' or bypass freezes due to timezone delays.
    """
    with open(DATA_DIR / "freeze_windows.json") as f:
        windows = json.load(f).get("freeze_windows", [])
    
    # Use the immutable submitted_at timestamp from the request itself
    submitted_at = request.get("submitted_at")
    
    if not submitted_at:
        # Failsafe if request is malformed
        return {"in_blackout": False}
        
    for window in windows:
        if window["start"] <= submitted_at <= window["end"]:
            return {
                "in_blackout": True, 
                "reason": f"System freeze/blackout active: {window.get('name')} - {window.get('reason')}"
            }
            
    return {"in_blackout": False}

def _check_budget(user: dict, item: dict) -> dict:
    """
    Multi-Attribute Budget Check: Compares item cost against user spending limit.
    Enforces the Tier 1 Immediate Denial guardrail.
    """
    cost = item.get("estimated_cost", 0)
    limit = user.get("spending_limit", 0)
    
    if cost > limit:
        return {
            "override": True, 
            "reason": f"Cost (${cost}) exceeds user's allocated limit (${limit})",
            "tier": "Tier 1" # Enforces the Immediate Denial requirement
        }
    return {"override": False}