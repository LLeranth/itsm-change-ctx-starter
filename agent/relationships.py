"""
Relationships layer — Identity, Entitlement & Heartbeat.

Answers: "Is this user legally entitled to this item right now, 
and is the target infrastructure healthy enough to receive it?"
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from agent.meaning import resolve_user, resolve_catalog_item

DATA_DIR = Path(__file__).parent.parent / "data"

# Phase 01 Mandate: Identity sync must be less than 4 hours old.
MAX_DATA_AGE_HOURS = 4  

def _check_system_heartbeat() -> bool:
    """
    Simulates an LPG (Labeled Property Graph) 'System Heartbeat' check.
    Scans cmdb.json to ensure the target CI is online before allowing fulfillment.
    Prevents "Operational Blindness" (Phase 01 risk).
    """
    try:
        with open(DATA_DIR / "cmdb.json") as f:
            cmdb = json.load(f)
            # If any CI in the infrastructure path is explicitly marked offline, fail the heartbeat
            for ci in cmdb.get("cis", []):
                if ci.get("status") == "offline":
                    return False
    except FileNotFoundError:
        pass # If CMDB is missing, we fail open for testing, but in production this would fail closed.
    return True

def check_entitlement(user_id: str, item_id: str) -> dict:
    """
    Evaluates the 'Relationship' edges between User, Item, and Target CI.
    Enforces strict Tier constraints, the 4-hour freshness rule, and CI health.
    """
    user = resolve_user(user_id)
    item = resolve_catalog_item(item_id)
    now = datetime.now(timezone.utc)

    # 1. Entity Resolution Verification
    if not user:
        return {"authorized": False, "reason": "ERR-USER-NOT-FOUND", "tier": "Tier 2"}
    if not item:
        return {"authorized": False, "reason": "ERR-CATALOG-MISSING", "tier": "Tier 3"}

    # 2. Hard Freshness Check (The < 4 Hour Mandate)
    last_verified_str = user.get("last_verified", "1970-01-01T00:00:00Z")
    last_verified = datetime.fromisoformat(last_verified_str.replace("Z", "+00:00"))
    
    # Calculate age strictly in hours
    age_hours = (now - last_verified).total_seconds() / 3600
    
    if age_hours > MAX_DATA_AGE_HOURS:
        return {
            "authorized": False, 
            "confidence": 0.0, 
            "reason": "ERR-IDENTITY-STALE", 
            "tier": "Tier 2" # Identity fails route to HR verification
        }

    # 3. System Heartbeat (CI Health Verification)
    if not _check_system_heartbeat():
        return {
            "authorized": False,
            "confidence": 1.0,
            "reason": "ERR-SYSTEM-OFFLINE",
            "tier": "Tier 3" # Infrastructure fails route to Tech Support
        }

    # 4. Strict Entitlement (Tier Matching)
    user_tier = user.get("tier", "non-critical")
    allowed_tiers = item.get("allowed_service_tiers", [])
    has_entitlement = user_tier in allowed_tiers

    if not has_entitlement:
        return {
            "authorized": False, 
            "confidence": 1.0, 
            "reason": "ERR-TIER-MISMATCH", 
            "tier": "Tier 1" # Entitlement Auth fails are Immediate Denials
        }

    # 5. Role-Based Confidence Scoring (Persona Drift Defense)
    user_role = user.get("role", "unknown")
    confidence = 1.0
    
    # If the user is in a high-turnover or ambiguous role, lower confidence 
    # to trigger mandatory human oversight in the harness.
    if user_role == "Intern":
        confidence *= 0.75  

    return {
        "authorized": True,
        "confidence": round(confidence, 2),
        "fresh": True,
        "context": {
            "department": user.get("department", "unknown"),
            "role": user_role
        }
    }