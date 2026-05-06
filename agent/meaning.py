"""
Meaning layer — canonical entity resolution for Service Requests.

This module answers: "What specific catalog item or person is this referring to?"
It resolves strings into canonical Catalog Items or User entities.
"""
import json
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"

def _load_users() -> list[dict]:
    # We will need a users.json for entitlement checks later
    with open(DATA_DIR / "users.json") as f:
        return json.load(f)["users"]

def _load_catalog_items() -> list[dict]:
    # We are repurposing the templates.json as our Service Catalog
    with open(DATA_DIR / "templates.json") as f:
        return json.load(f)["templates"]

def resolve_user(user_ref: str) -> Optional[dict]:
    """
    Resolve a user reference (by username or email) to a canonical User entity.
    This is critical for Service Requests because fulfillment depends on identity.
    """
    try:
        users = _load_users()
        ref = user_ref.strip().lower()
        for user in users:
            if user["id"].lower() == ref or user["email"].lower() == ref:
                return user
    except FileNotFoundError:
        return None
    return None

def resolve_catalog_item(item_id: str) -> Optional[dict]:
    """
    Resolve a catalog item ID to its canonical definition.
    (Repurposed from the original resolve_template).
    """
    items = _load_catalog_items()
    for item in items:
        if item["id"] == item_id:
            return item
    return None

def all_catalog_items() -> list[dict]:
    """Return the entire service catalog for matching."""
    return _load_catalog_items()

def resolve_intent(request: dict) -> dict:
    """
    Semantic resolution mapping natural language to canonical SKUs/Templates.
    Implements the >0.95 confidence threshold and Mandatory User Confirmation logic.
    """
    items = _load_catalog_items()
    text = (request.get("title", "") + " " + request.get("description", "")).lower()
    
    best_match = None
    highest_score = 0.0

    # 1. Attempt literal pattern matching (High Confidence)
    for item in items:
        patterns = item.get("match_patterns", [])
        for pattern in patterns:
            if pattern.lower() in text:
                highest_score = 0.98  # Literal match gets > 0.95
                best_match = item
                break
        if best_match:
            break
            
    # 2. Simulate Semantic/Fuzzy Match (Medium Confidence)
    # In a production system, this would be an LLM or embedding similarity check.
    # We simulate "Persona/Semantic Drift" (e.g., mapping "diagramming tool" to Visio).
    if not best_match and ("diagram" in text or "ide" in text):
        best_match = next((i for i in items if i["id"] == "TPL-SOFT-REQ-STD"), None)
        highest_score = 0.90  # Semantic mapping gets 0.90
        
    # 3. Fallback to explicit item_id if provided (for standard testing)
    if not best_match and "item_id" in request:
        best_match = next((i for i in items if i["id"] == request["item_id"]), None)
        highest_score = 0.98 if best_match else 0.0

    if not best_match:
        return {
            "item_id": None, 
            "confidence": 0.0, 
            "requires_user_confirmation": False
        }

    # MANDATORY USER CONFIRMATION RULE
    # If confidence is between 0.85 and 0.95, it is a non-literal match.
    requires_confirmation = 0.85 <= highest_score <= 0.95

    return {
        "item_id": best_match["id"],
        "canonical_sku": best_match["name"], # Proving JSON-LD aliasing
        "confidence": highest_score,
        "requires_user_confirmation": requires_confirmation
    }