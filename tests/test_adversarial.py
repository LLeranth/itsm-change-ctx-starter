"""
Adversarial Tests — The "Stress Shapes" (Phase 05 Mandate)

These tests use synthetic data injections to validate the "Refusal-First" 
architecture against extreme edge cases (Stale Identities, Race Conditions, 
and Budget Violations) without permanently altering the base JSON files.

Run with: pytest tests/test_adversarial.py -v
"""
import pytest
import json
from unittest.mock import patch
from agent.harness import classify

def base_request():
    """Helper to generate a structurally valid synthetic request."""
    return {
        "id": "SR-SYNTH-99",
        "title": "Need software",
        "description": "Standard software request",
        "requester_id": "logan.student",
        "submitted_at": "2026-05-04T12:00:00Z"
    }

# ---------------------------------------------------------
# TEST A: THE "STALE IDENTITY" PROBE (Tier 2: Data Fail)
# ---------------------------------------------------------
@patch("agent.meaning.resolve_user")
def test_stale_identity_injection(mock_resolve_user):
    """
    Injects a user whose identity was last verified 6 years ago.
    Proves the < 4 Hour Freshness mandate is strictly enforced.
    """
    mock_resolve_user.return_value = {
        "id": "stale.user",
        "role": "Engineer",
        "tier": "critical",
        "last_verified": "2020-01-01T00:00:00Z" # Intentionally stale
    }
    
    req = base_request()
    req["item_id"] = "TPL-SOFT-REQ-STD"
    
    result = classify(req)
    d = result["decision"]
    
    assert d["classification"] == "refused"
    assert d["refusal_tier"] == "Tier 2"
    assert d["reason"] == "ERR-IDENTITY-STALE"

# ---------------------------------------------------------
# TEST B: THE "INVENTORY RACE" / SEMAPHORE-LOCK (Tier 2: Data Fail)
# ---------------------------------------------------------
@patch("agent.history.DATA_DIR")
def test_inventory_race_condition(mock_data_dir, tmp_path):
    """
    Simulates a concurrency attack (Double-Spend). Injects a synthetic 
    event_log where the requested item is currently 'in_progress'.
    Proves the History layer successfully applies Semaphore-Locking.
    """
    # Create a temporary synthetic event log
    log_file = tmp_path / "event_log.json"
    log_file.write_text(json.dumps({
        "events": [
            {
                "event_id": "E-SYNTH-1", 
                "state": "in_progress", 
                "template_id": "TPL-SOFT-REQ-STD"
            }
        ]
    }))
    mock_data_dir.__truediv__.return_value = log_file

    req = base_request()
    req["item_id"] = "TPL-SOFT-REQ-STD"
    
    result = classify(req)
    d = result["decision"]
    
    assert d["classification"] == "refused"
    assert d["refusal_tier"] == "Tier 2"
    assert d["reason"] == "ERR-INVENTORY-RACE"

# ---------------------------------------------------------
# TEST C: THE "DOUBLE-SPEND" BUDGET VIOLATION (Tier 1: Auth Fail)
# ---------------------------------------------------------
def test_double_spend_budget_violation():
    """
    No mocking needed. Uses real data: 'bob.intern' has a $100 limit. 
    'TPL-CERT-ROTATE-STD' costs $250. 
    Proves financial guardrails trigger an Immediate Denial.
    """
    req = base_request()
    req["requester_id"] = "bob.intern"
    req["item_id"] = "TPL-CERT-ROTATE-STD" 
    
    result = classify(req)
    d = result["decision"]
    
    assert d["classification"] == "refused"
    assert d["refusal_tier"] == "Tier 1"
    assert d["reason"] == "ERR-BUDGET-EXCEEDED"

# ---------------------------------------------------------
# TEST D: SYSTEM HEARTBEAT / INFRASTRUCTURE FAIL (Tier 3: Logic Fail)
# ---------------------------------------------------------
@patch("agent.relationships._check_system_heartbeat")
def test_system_heartbeat_offline(mock_heartbeat):
    """
    Simulates the CMDB returning an 'offline' status for a target CI.
    Proves the engine refuses to automate against dead infrastructure.
    """
    mock_heartbeat.return_value = False
    
    req = base_request()
    req["item_id"] = "TPL-SOFT-REQ-STD"
    
    result = classify(req)
    d = result["decision"]
    
    assert d["classification"] == "refused"
    assert d["refusal_tier"] == "Tier 3"
    assert d["reason"] == "ERR-SYSTEM-OFFLINE"

# ---------------------------------------------------------
# TEST E: PERSONA DRIFT / SEMANTIC AMBIGUITY (Tier 3: Logic Fail)
# ---------------------------------------------------------
def test_persona_drift_semantic_ambiguity():
    """
    Tests the Meaning Layer. Submits a fuzzy natural language string 
    that yields a confidence between 0.85 and 0.95.
    Proves the Mandatory User Confirmation constraint.
    """
    req = base_request()
    req["title"] = "I need some diagramming thing"
    req["description"] = "I don't know the exact name of the license."
    # Omit item_id to force semantic resolution
    
    result = classify(req)
    d = result["decision"]
    
    assert d["classification"] == "refused"
    assert d["refusal_tier"] == "Tier 3"
    assert d["reason"] == "ERR-CONFIRMATION-REQUIRED"