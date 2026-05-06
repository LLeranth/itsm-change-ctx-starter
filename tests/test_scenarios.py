"""
Tests that reproduce the scenarios from the Worked Example (Phase 5).
Updated to test Semantic Meaning Resolution and Tiered Refusals.
Run with: pytest -v
"""
import json
from pathlib import Path
import pytest
from agent.harness import classify

DATA_DIR = Path(__file__).parent.parent / "data"

def _load_request(request_id: str) -> dict:
    with open(DATA_DIR / "requests.json") as f:
        # Step 1 Fix: Look for 'requests' instead of 'rfcs'
        for r in json.load(f).get("requests", []):
            if r["id"] == request_id:
                return r
    pytest.fail(f"Request {request_id} not found")

def test_scenario_1_standard_autoapproved():
    """
    Scenario 1: High confidence, literal semantic match for cert rotation.
    Expected: auto_fulfill.
    """
    req = _load_request("SR-9812")
    result = classify(req)
    assert result["decision"]["classification"] == "auto_fulfill"
    assert result["decision"]["route"] == "automation_engine"

def test_scenario_2_semantic_drift_refusal():
    """
    Scenario 2: Semantic meaning resolution failure or intent drift.
    Expected: Tier 3 Refusal for low confidence or confirmation requirement.
    """
    # Using SR-9999 assuming it's a badly formatted or ambiguous request
    # If SR-9999 doesn't exist, this will fail safely. Let's test standard refusal.
    req = _load_request("SR-9847")
    
    # We will artificially change the title to trigger the Semantic Drift (< 0.85 confidence)
    req["title"] = "I need a random obscure tool"
    req["description"] = "Not sure what it is called."
    
    result = classify(req)
    assert result["decision"]["classification"] == "refused"
    assert result["decision"]["refusal_tier"] == "Tier 3"
    assert result["decision"]["reason"] in ["ERR-UNKNOWN-INTENT", "ERR-LOW-CONFIDENCE"]

def test_every_decision_has_a_trace():
    """
    The agent must never return a decision without a trace.
    Groundedness is non-negotiable.
    """
    req = _load_request("SR-9812")
    result = classify(req)
    assert "trace" in result
    assert len(result["trace"]) > 0
    # Verify the Meaning Layer trace exists
    assert any(t["step"] == "01b_resolve_intent" for t in result["trace"])