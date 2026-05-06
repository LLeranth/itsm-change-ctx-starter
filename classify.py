"""
classify.py — run the agent against a Service Request and print a human-readable trace.

Usage:
    python classify.py SR-9812   # Standard Auto-Approve
    python classify.py SR-9847   # Semantic drift/Confirmation test
"""
import json
import sys
from pathlib import Path
from agent.harness import classify

DATA_DIR = Path(__file__).parent / "data"

def load_request(request_id: str) -> dict:
    """Load a request from the requests.json file."""
    file_path = DATA_DIR / "requests.json"
    if not file_path.exists():
        raise SystemExit(f"Error: {file_path} not found.")

    with open(file_path) as f:
        requests = json.load(f).get("requests", [])
    
    for r in requests:
        if r["id"] == request_id:
            return r
    raise SystemExit(f"Request {request_id} not found in {file_path.name}")

def _fmt(val) -> str:
    """Compact pretty-print for trace values."""
    s = json.dumps(val, default=str, indent=2)
    if len(s) <= 200:
        return s.replace("\n", " ").replace("  ", " ")
    return s

def print_trace(result: dict) -> None:
    print()
    print("=" * 90)
    print(f"  FULFILLMENT AGENT TRACE")
    print("=" * 90)
    for entry in result["trace"]:
        print(f"\n[{entry['step']}] {entry['action']}")
        print(f"  → {_fmt(entry['result'])}")

    print()
    print("=" * 90)
    print(f"  DECISION")
    print("=" * 90)
    d = result["decision"]
    
    print(f"  Classification : {d.get('classification', 'UNKNOWN').upper()}")
    print(f"  Route          : {d.get('route', 'n/a')}")
    
    # Step 5: Displaying the Refusal-First Tiered Ladder outputs
    if d.get('classification') == "refused":
        print(f"  Refusal Tier   : {d.get('refusal_tier', 'n/a')}")
        print(f"  Error Code     : {d.get('reason', 'n/a')}")
        print(f"  Coaching Note  : {d.get('analyst_coaching_note', 'n/a')}")
    else:
        print(f"  Reason         : {d.get('reason', 'n/a')}")
    
    if "item_resolved" in d:
        print(f"  Item Resolved  : {d['item_resolved']}")
    
    print("=" * 90)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python classify.py <REQUEST_ID>")
        sys.exit(1)
        
    req_id = sys.argv[1]
    req = load_request(req_id)
    result = classify(req)
    print_trace(result)