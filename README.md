# Service Request Fulfillment: High-Assurance Context Engine

A working reference implementation of a high-assurance agentic context layer for IT Service Management. The engine handles **Autonomous Fulfillment Decisions** for standard IT service requests — such as TLS Certificate Rotations and Software License Grants — through a strict, defense-in-depth architecture.

---

## Philosophy

This engine is built on two core principles:

**Refusal-First Philosophy** — The system actively searches for reasons *not* to automate. Automation is a privilege granted only when every defensive gate has been cleared, not a default behavior.

**Zero-Error Mandate** — When a failure state is reached, the engine produces detailed **Analyst Coaching Notes** to ensure human operators understand the policy violation, preserving institutional knowledge and preventing skill atrophy.

---

## Architecture Overview

Requests are evaluated through a strict, four-layer context model orchestrated by a central harness. Each layer acts as an independent defensive gate. All layers must pass before automation is permitted.

```
Request
   │
   ▼
┌─────────────────────┐
│   Meaning Layer     │  Semantic intent resolution (>0.95 confidence threshold)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Relationships Layer │  Identity freshness (<4hr sync) + CMDB heartbeat checks
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│    Rules Layer      │  Policy-as-Code: budget limits, freeze windows
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   History Layer     │  100% success rate gate + semaphore-locking
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Harness / Router   │  Kill-switch check → Auto-Fulfill or Tiered Refusal
└─────────────────────┘
```

### Layer Details

| Layer | Role | Key Constraint |
|---|---|---|
| **Meaning** | Semantic intent resolution | >0.95 confidence threshold; ambiguous requests trigger a User Confirmation step |
| **Relationships** | Identity & infrastructure health | HR identity sync must be <4 hours old; CMDB System Heartbeat must be active |
| **Rules** | Policy-as-Code guardrails | Enforces financial spend limits and timezone-aware system freeze windows at exact request timestamp |
| **History** | Concurrency & reliability | Demands 100% historical automation success rate; semaphore-locking blocks concurrent in-flight tasks |

### Harness Orchestrator

The central execution loop evaluates layers sequentially, applies the **Operational Kill-Switch** if engaged by governance, and routes any failure to the appropriate tier of the Refusal Ladder.

---

## Tiered Refusal Ladder

Failures are not dumped to a generic queue. Each failure shape routes to a specific human team for rapid remediation.

| Tier | Trigger | Outcome |
|---|---|---|
| **Tier 1 — Auth Fail** | Budget exceeded or role mismatch | Immediate denial. No manual queue required. |
| **Tier 2 — Data Fail** | Stale identity sync or inventory race condition | Fast-tracked to the Identity Verification Queue. |
| **Tier 3 — Logic Fail** | Semantic ambiguity or active system freeze window | Routed to Standard Service Desk Manual Fulfillment Queue. |

---

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Running a Classification

```bash
python classify.py SR-9812
```

### Running the Adversarial Test Suite

```bash
pytest tests/test_adversarial.py -v
```

---

## Test Scenarios

The test suite mathematically proves the engine's defenses by injecting specific scenarios.

### The Happy Path
Submits a request where the user's identity is perfectly fresh, they are fully entitled to the item, their budget clears, and the historical automation success rate is 100%. A successful **Auto-Fulfill** result proves the engine automates when it is provably safe to do so.

### The Double-Spend
Simulates two users attempting to claim the same software license at the exact same millisecond. This proves the History Layer's **Semaphore-Locking** mechanism detects the first request as in-flight, locks the inventory, and actively refuses the second request to prevent over-subscription.

---

## Production Deployment

The reference implementation uses local JSON files to simulate data layers. A production deployment would replace these with enterprise-grade systems:

| Component | Reference Implementation | Production Replacement |
|---|---|---|
| **Rules Layer** | Local JSON policies | [Open Policy Agent (OPA) / Rego](https://www.openpolicyagent.org/) |
| **Relationships Layer** | Local JSON identity store | Labeled Property Graph (LPG / Neo4j) for n-hop dependency mapping |
| **Meaning Layer** | Keyword matching | LLM Embeddings for secure natural language intent resolution |

---
