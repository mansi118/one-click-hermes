---
name: client-engagement
description: "How NeuralEDGE runs a client engagement end-to-end — discovery, audit, build, train, hand-off. Use when the operator is preparing for a client call, scoping a project, writing a proposal, or asking how a phase should be structured."
version: 1.0.0
author: NeuralEDGE
license: MIT
metadata:
  hermes:
    tags: [neuraledge, clients, process, proposals, scoping]
    related_skills: [neuraledge-context, neos-operations]
---

# The four phases

Every NeuralEDGE engagement moves through these four phases. Each phase has an explicit
artefact and a go/no-go gate to the next.

### 1. Discovery (1–2 weeks)
**Goal:** decide whether to engage at all and at what shape.
- **Inputs:** founder/COO conversation, light ops walkthrough, candidate workflow list.
- **Outputs:**
  - Engagement memo (1 page): the problem in their words, our framing, fit/no-fit call.
  - Indicative roadmap with 2-3 candidate Digital Employee scopes.
- **Gate:** mutual decision to proceed to Audit. If we say no, we say why and recommend
  an alternative. Never proceed for the sake of revenue.

### 2. AI Audit (2–4 weeks)
**Goal:** prove out the highest-confidence workflow and produce the build roadmap.
- **Inputs:** Discovery memo, access to a small operational sample (anonymised),
  workflow shadowing or recording.
- **Outputs:**
  - Audit report — workflow inventory with build/buy/skip per item, ROI shape, risk.
  - One **prototype** of the top candidate — not slides, an actual working artefact.
- **Gate:** client commits (or doesn't) to a Build engagement on a named workflow.

### 3. Build / Digital Employee (4–12 weeks per Neop)
**Goal:** ship a production Neop or fleet that takes over the named workflow.
- **Inputs:** Audit roadmap, signed scope, client SME access for integration questions.
- **Outputs:**
  - Neop(s) running in client environment or our hosted instance, integrated into
    their actual systems (CRM, helpdesk, ops DB, etc.).
  - Operations dashboard for the client team.
  - Runbook: how to observe, intervene, and extend.
- **Gate:** the Neop runs for a defined "shadow" period under human review, then
  graduates to autonomous with sampled oversight.

### 4. AI Training & Hand-off (1–3 weeks)
**Goal:** the client team can run, extend, and govern the system without us.
- **Inputs:** the shipped Neop(s), runbook, the client's intended operators.
- **Outputs:**
  - Operational training on **this stack** (not generic AI literacy).
  - Governance playbook — what to monitor, when to retrain, when to call us.
  - Retainer offer for ongoing support (optional, never bundled by default).
- **Gate:** training-completion sign-off; engagement closes or rolls into retainer.

# Scoping defaults

- **Phase pricing** is per phase, not bundled. Each gate is a real off-ramp.
- **One workflow at a time.** Pitch "let's automate operations" and you'll deliver
  nothing. Pitch "let's replace the L1 support tier for product X" and you'll ship.
- **Always include a prototype in Audit.** A working artefact converts dramatically
  better than a deck, and weeds out clients who only want consulting.
- **No multi-year contracts on first engagement.** Build trust with a discrete win.

# What to capture in CORTEX-PALACE during an engagement

Write into the `clients` wing as soon as the engagement starts:

- `clients/profiles/<slug>` — entity room with company facts, sector, ICP fit, contacts.
- `clients/decisions/<slug>` — every commercial/scope decision with date and reasoning.
- `clients/meetings/<slug>` — meeting outcomes + action items.
- `clients/incidents/<slug>` — anything that went wrong + how it was fixed.

Use `cortex_remember` from inside the engagement — don't wait for a postmortem.

# When the operator says "I'm about to hop on a call with <client>"

Default pre-call brief (run automatically if the operator says they're about to talk
to a client and CORTEX is up):

1. `cortex_search_entities(entity_type='client', filter={'slug': '<slug>'})`
2. `cortex_recall("decisions and recent activity", wing='clients', hall='decisions', k=8)`
3. `cortex_recall("last meeting outcomes", wing='clients', hall='meetings', k=5)`
4. Synthesise: who they are, where the engagement is, last decision, open actions.
   Three short bullets, not a report.

If CORTEX is degraded, say so and ask the operator if they want a generic prep checklist
instead.

# Counter-patterns (decline politely)

- *"We want to add AI somewhere — what do you recommend?"* → Audit only, no Build promise.
- *"Can we run a 6-month pilot with multiple Neops in parallel?"* → No. One workflow first.
- *"Can we just buy your platform?"* → NEOS isn't a SaaS product. Engagement-only today.
- *"Can you do it 30% cheaper if we sign for two years?"* → No discount for term length;
  scope is the lever, not duration.

These responses are intentional and defensible. Don't soften them on the operator's behalf.
