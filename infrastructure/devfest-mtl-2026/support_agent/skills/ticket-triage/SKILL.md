---
name: ticket-triage
description: >-
  Enforces Montréal TechGear enterprise support SLA policies, refund/credit
  limits, and AlloyDB query verification rules before resolving or escalating
  customer support tickets. Load this skill before triaging any ticket or order.
---

# Ticket Triage & SLA Policy Skill

Follow these mandatory workflow steps whenever a user asks to inspect, triage,
escalate, or resolve customer tickets or delayed orders:

## 1. Ground Every Fact in AlloyDB First
- Never guess customer tiers, order amounts, or ticket statuses.
- If running with **Local MCP Toolbox**, call `find_customer_tickets`,
  `list_open_high_priority_tickets`, or `get_order_details`.
- If running with **AlloyDB Remote MCP**, load `references/schema_guide.md` via
  `load_skill_resource` first so you know the exact table/column names before
  calling `execute_sql_read_only` or `execute_sql`.

## 2. Apply Tier & SLA Escalation Rules
- **ENTERPRISE Tier**:
  - Any `DELAYED` order older than **3 days** constitutes an **SLA Breach**.
  - Action: Set status to `ESCALATED`, note priority replacement dispatch, and
    recommend a **10% SLA shipping credit** (capped at **$250 CAD** without VP approval).
- **PRO Tier**:
  - Delayed orders older than **5 days** qualify for expedited carrier trace and
    a **$25 CAD** courtesy credit.
- **STANDARD Tier**:
  - Provide live tracking status and check `search_past_resolutions` (or query
    `RESOLVED` tickets) for known self-service fixes before escalating.

## 3. Check Historical Resolutions for Technical Issues
- For hardware/firmware symptoms (e.g., wake-from-sleep disconnects), search
  resolved tickets first and cite the matching `ticket_id` in your answer.

## 4. Safe Write Guardrail
- Never mutate `support_tickets` unless the user explicitly asks you to update,
  escalate, or resolve a ticket.
- Always include a clear, auditable `resolution_note` summarizing the policy applied.
