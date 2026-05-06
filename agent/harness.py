import json
from pathlib import Path
from agent import meaning, relationships, rules, history

DATA_DIR = Path(__file__).parent.parent / "data"

def classify(request: dict) -> dict:
    trace = []
    
    # 0. GOVERNANCE CHECK (Kill-Switch)
    # Rubric Phase 05: Operational Kill-switch
    with open(DATA_DIR / "governance.json") as f:
        gov = json.load(f)
    if gov.get("kill_switch"):
        return _refuse(
            trace, 
            "ERR-GOV-KILL-SWITCH", 
            "System Kill-Switch engaged by Service Desk Manager.", 
            "manual_fulfillment", 
            "Tier 3"
        )

    # 1. RESOLVE & COLLAPSE DEFENSE
    # Rubric Phase 04: Collapse Defense (handling null system states)
    user = meaning.resolve_user(request["requester_id"])
    trace.append({
        "step": "01_resolve_user",
        "action": f"resolve_user({request['requester_id']}) FROM data/users.json",
        "result": user,
    })

    if not user or not isinstance(user, dict):
        return _refuse(
            trace, 
            "ERR-IDENTITY-NULL", 
            "Collapse Error: Identity system returned null state. Verify HRIS sync.", 
            "service_desk_escalation",
            "Tier 2"
        )

    # --- NEW STEP 1b. SEMANTIC INTENT RESOLUTION ---
    # Replaces the brittle rules.match_catalog_item
    intent = meaning.resolve_intent(request)
    trace.append({
        "step": "01b_resolve_intent",
        "action": "Semantic Mapping & Confidence Scoring",
        "result": intent
    })

    if not intent["item_id"]:
        return _refuse(
            trace, 
            "ERR-UNKNOWN-INTENT", 
            "Could not map request to a canonical Catalog Item.", 
            "service_desk_escalation",
            "Tier 3"
        )
        
    if intent["confidence"] < 0.85:
        return _refuse(
            trace, 
            "ERR-LOW-CONFIDENCE",
            f"Intent confidence ({intent['confidence']}) below 0.85 threshold. User text is too ambiguous.", 
            "service_desk_escalation",
            "Tier 3"
        )
        
    # RUBRIC MANDATE: Mandatory User Confirmation for non-literal matches
    if intent["requires_user_confirmation"]:
        return _refuse(
            trace, 
            "ERR-CONFIRMATION-REQUIRED",
            "Non-literal intent match (Confidence 0.85-0.95). Mandatory User Confirmation required before automation can proceed.", 
            "manager_verification", 
            "Tier 3"
        )

    # Resolve the actual catalog item data now that intent is confirmed
    item = meaning.resolve_catalog_item(intent["item_id"])
    if not item:
        return _refuse(
            trace, 
            "ERR-CATALOG-MISSING", 
            "Resolved catalog ID not found in templates.json.", 
            "service_desk_escalation", 
            "Tier 3"
        )

    # 2. TRAVERSE (ENTITLEMENT & FRESHNESS)
    # Rubric Phase 04: Stale Retrieval Defense (Confidence check)
    entitlement = relationships.check_entitlement(user["id"], item["id"])
    trace.append({
        "step": "02_traverse",
        "action": f"check_entitlement({user['id']}, {item['id']})",
        "result": entitlement,
    })

    if not entitlement.get("authorized"):
        reason_code = entitlement.get("reason", "ERR-UNAUTHORIZED")
        
        # Dynamically assign the correct coaching note based on the specific failure
        if reason_code == "ERR-IDENTITY-STALE":
            coaching = "Identity sync is older than 4 hours. Manual HR verification required."
            route = "hr_verification"
        elif reason_code == "ERR-SYSTEM-OFFLINE":
            coaching = "Target infrastructure is offline in CMDB. Automation aborted."
            route = "service_desk_escalation"
        else:
            coaching = "Immediate Denial: User lacks proper tier/entitlement for this catalog item."
            route = "manager_verification"

        return _refuse(
            trace, 
            reason_code, 
            coaching, 
            route,
            entitlement.get("tier", "Tier 1")
        )

    # 3. EVALUATE (RULES & POLICY)
    # Rubric Phase 04: Rule-based grounding
    rules_output = rules.evaluate_all_fulfillment_rules(request, user, item)
    trace.append({
        "step": "03_evaluate",
        "action": "evaluate_all_fulfillment_rules() FROM data/freeze_windows.json & data/users.json",
        "result": rules_output,
    })

    if rules_output["budget_override"]["override"]:
        return _refuse(
            trace, 
            "ERR-BUDGET-EXCEEDED", 
            f"Immediate Denial: {rules_output['budget_override'].get('reason', 'Budget Exceeded')}.", 
            "manager_verification",
            "Tier 1"
        )

    if rules_output["blackout_window"]["in_blackout"]:
        return _refuse(
            trace, 
            "ERR-LOGIC-FREEZE", 
            "System freeze/blackout window active. Automation suspended.", 
            "manual_fulfillment",
            "Tier 3"
        )

    # 4. RECALL (HISTORY & RELIABILITY)
    perf = history.recall_performance(item["id"])
    trace.append({
        "step": "04_recall",
        "action": f"recall_performance({item['id']}) FROM data/event_log.json",
        "result": perf,
    })

    # Catch Semaphore-Lock (Race Condition)
    if perf.get("status") == "locked":
        return _refuse(
            trace, 
            perf.get("reason", "ERR-INVENTORY-RACE"), 
            "Inventory Race detected. An identical request is currently in-flight. Verify license pool before proceeding.", 
            "hr_verification", # Tier 2 Data routing
            perf.get("tier", "Tier 2")
        )

    # Strict Zero-Error Tolerance Enforcement
    if perf.get("status") == "unreliable" or perf.get("reliability", 1.0) < 1.0:
        return _refuse(
            trace, 
            perf.get("reason", "ERR-RELIABILITY-FAIL"), 
            f"Automation reliability ({perf.get('reliability', 0)}) is below 1.0 threshold. Handing off to human.", 
            "manual_fulfillment",
            perf.get("tier", "Tier 3")
        )

    # 5. ACT (DECIDE)
    return _decide(request, user, item, rules_output, perf, trace)

def _decide(request: dict, user: dict, item: dict, rules_output: dict, history_data: dict, trace: list) -> dict:
    """Final grounded decision logic."""
    decision = {
        "request_id": request["id"],
        "classification": "auto_fulfill",
        "route": "automation_engine",
        "item_resolved": item["name"],
        "reason": "User entitled, budget cleared, and automation reliability is high."
    }
    
    trace.append({"step": "05_act", "action": "decide", "result": decision})
    return {"decision": decision, "trace": trace}

def _refuse(trace: list, code: str, coaching_tip: str, route: str, tier: str = "Tier 3") -> dict:
    """
    Tiered Refusal Ladder generating an Analyst Coaching Note.
    """
    routes = {
        "hr_verification": "HR_Identity_Queue",
        "manager_verification": "Manager_Approval_Queue",
        "manual_fulfillment": "Service_Desk_Manual_Queue",
        "service_desk_escalation": "Technical_Support_Level_2"
    }
    
    decision = {
        "classification": "refused",
        "route": routes.get(route, "Standard_Manual_Review"),
        "refusal_tier": tier,
        "reason": code,
        "analyst_coaching_note": coaching_tip
    }
    
    trace.append({"step": "refusal", "action": "abort_automation", "result": decision})
    return {"decision": decision, "trace": trace}