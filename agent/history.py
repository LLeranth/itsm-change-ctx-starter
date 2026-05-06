"""
History layer — Semaphore-Locking & Reliability Gating.
Answers: "Is this item currently locked by an in-flight request, 
and is its historical automation reliability at 100%?"
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

def recall_performance(item_id: str) -> dict:
    """
    Search historical events to calculate the success rate of the automation,
    and scan for 'in_progress' states to prevent Inventory Race Conditions.
    """
    file_path = DATA_DIR / "event_log.json"
    
    if not file_path.exists():
        return {"reliability": 1.0, "count": 0, "status": "no_history"}

    with open(file_path) as f:
        events = json.load(f).get("events", [])

    # 1. SEMAPHORE-LOCKING (In-Flight Check)
    # Scan for any events currently "in_progress" for this specific item
    in_flight = [e for e in events if e.get("template_id") == item_id and e.get("state") == "in_progress"]
    
    if in_flight:
        return {
            "status": "locked",
            "reliability": 1.0,
            "reason": "ERR-INVENTORY-RACE",
            "tier": "Tier 2" # Maps to Identity/Data Verify queue
        }

    # 2. STRICT RELIABILITY GATING (0% False Approval Mandate)
    relevant = [e for e in events if e.get("template_id") == item_id and e.get("state") != "in_progress"]
    
    if not relevant:
        return {"reliability": 1.0, "count": 0, "status": "no_history"}

    successes = [e for e in relevant if e.get("outcome") == "SUCCESS"]
    reliability = len(successes) / len(relevant)
    
    if reliability < 1.0:
        return {
            "status": "unreliable",
            "reliability": round(reliability, 2),
            "reason": "ERR-RELIABILITY-FAIL",
            "tier": "Tier 3" # Drops to standard Service Desk manual review
        }

    return {
        "status": "reliable", 
        "reliability": 1.0, 
        "count": len(relevant)
    }