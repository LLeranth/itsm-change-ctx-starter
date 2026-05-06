# Usage Guide: Extending the Context Engine

Welcome to the Service Request Fulfillment: High-Assurance Context Engine! This guide walks through how to add new features, components, and Service Requests (SRs) to the system — no prior experience with Context Layers or Agentic Architectures required.

---

## What Is a Context Layer?

Think of a Context Layer as a series of highly paranoid security checkpoints at an airport. Rather than glancing at a ticket and waving someone through, each checkpoint independently interrogates the request:

| Layer | Question Asked |
|---|---|
| **Meaning** | Did you ask for the right thing, or are you confused? |
| **Relationships** | Is your ID real? Is the airplane actually at the gate? |
| **Rules** | Do you have enough money? Is the airport currently closed? |
| **History** | Has this flight crashed recently? Are two people assigned to this seat? |

If any checkpoint fails, the engine refuses to automate and hands the ticket to a human operator with a detailed **Analyst Coaching Note** explaining exactly what went wrong.

---

## Tutorial 1: Adding a New Service Request

Let's automate a new catalog item: **"Provision AWS EC2 Instance"**.

### Step 1 — Define the Catalog Item (`data/templates.json`)

Add a new template entry. This tells the engine the item's cost, who can request it, and the natural language phrases that map to it.

```json
{
    "id": "TPL-CLOUD-EC2-PROD",
    "name": "Standard AWS EC2 Provisioning",
    "canonical_sku": "SKU_AWS_EC2_T3_MICRO",
    "allowed_service_tiers": ["critical", "standard"],
    "estimated_cost": 500,
    "match_patterns": ["ec2", "aws server", "cloud instance", "virtual machine"]
}
```

### Step 2 — Update the Meaning Layer (`agent/meaning.py`)

To support fuzzy matching — where a user says "server" instead of "EC2" — add a fallback rule inside `resolve_intent()`.

> **Note:** Setting `highest_score` below 0.95 forces a mandatory **User Confirmation** step before the engine proceeds. This is intentional.

```python
# Inside agent/meaning.py -> resolve_intent()
if not best_match and ("server" in text or "compute" in text):
    best_match = next((i for i in items if i["id"] == "TPL-CLOUD-EC2-PROD"), None)
    highest_score = 0.90  # Forces mandatory user confirmation!
```

### Step 3 — Create a Test Request (`data/requests.json`)

Simulate a user submitting a ticket:

```json
{
    "id": "SR-NEW-001",
    "title": "Need a new AWS server",
    "description": "Please provision a t3.micro for the backend team.",
    "requester_id": "logan.student",
    "submitted_at": "2026-05-10T14:00:00Z"
}
```

### Step 4 — Run the Engine

```bash
python classify.py SR-NEW-001
```

The engine will resolve the EC2 template, validate Logan's identity freshness, check the $500 cost against his budget, and output a decision with a full trace.

---

## Tutorial 2: Adding a New Defensive Rule

Let's add a new security constraint: **"Interns may not provision cloud infrastructure."**

### Step 1 — Add the Rule Logic (`agent/rules.py`)

Create a new check function. Note that the function **defaults to `False`** (no override) and only activates on a specific, explicit condition.

```python
def _check_intern_restrictions(user: dict, item: dict) -> dict:
    if user.get("role") == "Intern" and "CLOUD" in item.get("id", ""):
        return {
            "override": True,
            "reason": "ERR-INTERN-CLOUD-RESTRICTION",
            "coaching": "Interns are not permitted to provision cloud infrastructure."
        }
    return {"override": False}
```

Register your new function in the `evaluate_all_fulfillment_rules` dictionary at the top of `rules.py`.

### Step 2 — Handle the Refusal (`agent/harness.py`)

In `harness.py`, scroll to **Step 3: EVALUATE** and add a handler that routes the failure to the appropriate queue.

```python
# Inside agent/harness.py -> Step 3
if rules_output["intern_restriction"]["override"]:
    return _refuse(
        trace,
        rules_output["intern_restriction"]["reason"],
        rules_output["intern_restriction"]["coaching"],
        "manager_verification",  # Route to their manager
        "Tier 1"                 # Immediate Denial
    )
```

---

## Best Practices

**Always default to refusal.** New functions should return `False` or a failure state. The engine only proceeds when data is provably correct — not when it merely lacks evidence of a problem.

**Never return a bare failure.** Every refusal must include an **Error Code** and an **Analyst Coaching Note**. Without these, the human operator receiving the ticket has no path to resolution.

**Use the right tier.** Routing failures to the correct queue keeps the Service Desk from becoming a dumping ground for misrouted tickets.

| Tier | Trigger | Route To |
|---|---|---|
| **Tier 1** | Hard policy violations (budget exceeded, security block) | Immediate denial — no queue |
| **Tier 2** | Data sync issues (stale identity, race conditions) | HR / Identity & Data teams |
| **Tier 3** | Logic or ambiguity issues (fuzzy text, system offline) | IT Helpdesk manual fulfillment |