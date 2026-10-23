# AI Opportunity Report: AI Triage for TenantEase

**Applicant:** Anshi Agrawal  |  **Role:** AI/ML Engineer Intern  |  **Task:** Identify an AI Opportunity for Cynbit
**Chosen opportunity:** TenantEase, AI triage of maintenance and tenant messages

> **Scope note.** The product description of TenantEase comes from the assessment brief (properties, tenants, rent reminders). I could not independently verify TenantEase's public feature set, so product claims below are limited to what the brief states. All data in this project is **synthetic**.

---

## 1. Why this opportunity (and why now)

Cynbit builds scalable digital platforms, AI automation systems and high-performance engineering products. TenantEase already digitises the structured side of renting (properties, tenants, rent reminders). The **unstructured side is still manual**: tenants raise issues over WhatsApp, calls and notes ("tap leaking in room 204", "no power since morning"). A person must read each message, decide what it is, judge urgency, and route it. This is the manual chaos TenantEase exists to remove, and it is a natural fit for language models because:

- Inputs are short, noisy, multilingual text (English, Hinglish, typos, vague wording).
- The outputs are a small, well-defined set (category, urgency, fields, drafts).
- A human can cheaply review the result, so mistakes are catchable.

## 2. What the AI does

For each incoming message the system:

| Step | Output | Example for "pipe burst in room 204 water everywhere pls come fast" |
|---|---|---|
| Classify | plumbing / electrical / payment_query / noise_complaint / general | plumbing |
| Score urgency | emergency / high / normal / low | emergency |
| Extract details | unit, issue, time mentioned | unit 204, "pipe burst" |
| Draft | tenant reply + manager task | Calm safety-first reply; `[EMERGENCY] plumbing, 204, respond immediately` |

## 3. Business impact

**Value to landlords/managers:** faster response to emergencies, less time reading and routing messages, a consistent audit trail.
**Value to Cynbit:** a differentiating premium feature (e.g. an "AI Inbox" add-on) on top of an existing product, plus a reusable triage engine for other Cynbit property or support products.

### Estimated hours saved (assumption-based, not measured)

| Assumption | Value |
|---|---|
| Units managed by a small landlord | 20 |
| Messages per unit per month | 6 (so 120 messages/month) |
| Manual handling per message (read, classify, decide urgency, reply, create task) | ~3 min |
| AI-assisted handling per message (review a pre-filled card, edit if needed) | ~0.75 min |

- Manual: 120 x 3 min = **6.0 h/month**
- AI-assisted: 120 x 0.75 min = **1.5 h/month**
- **Saved: about 4.5 h per landlord per month (~75%)**; for a 50-unit manager about 11 h/month.

These numbers are illustrative inputs to be replaced by timing studies from real TenantEase users. The bigger benefit is not the hours but **time-to-first-response on emergencies**, which cannot be priced as easily.

### Suggested success metrics for a pilot
Emergency recall (target >= 98%), median time-to-acknowledge emergencies, manager edit rate on drafted replies, share of messages needing manual re-categorisation, and landlord satisfaction.

## 4. Risks and mitigations

| Risk | Why it matters | Mitigation (implemented or planned) |
|---|---|---|
| **Emergency labelled low priority** (the big one) | Safety and liability | Rule-based emergency safety net on top of any model (implemented); LLM told to pick the *more urgent* level when unsure; unknown LLM output escalates to "high" (implemented); optimise for emergency **recall**, accept false alarms |
| Over-escalation (alert fatigue) | Managers stop trusting alerts | Track emergency precision; tune with real data; show *why* it was flagged |
| Wrong/over-promising auto replies | Trust, legal | Drafts only; **human in the loop** for emergency/high (implemented as `needs_human_review`); prompt forbids promising times or costs |
| Tenant privacy (names, phone numbers, addresses, possibly distress content) | Legal (India's DPDP Act 2023) and trust | Minimise data sent to the LLM (strip names and phone numbers), vendor with no-training/zero-retention terms, encryption at rest, retention limits, consent notice to tenants, access control per property |
| Prompt injection via tenant text | A message could try to alter behaviour | Message wrapped as data, strict JSON schema validation, enum checks, no tool access for the model |
| Bias across languages/dialects | Hinglish and regional spellings may perform worse | Evaluate per language slice on real data before launch |
| Domestic-violence or distress messages hidden in "noise complaints" | Sensitive | Keyword flag plus human review; never auto-reply |

## 5. Rollout plan

1. **Shadow mode (weeks 1-4):** triage runs silently on real messages; compare with managers' decisions; measure emergency recall.
2. **Assisted mode:** show suggestions and drafts to managers; track edits.
3. **Selective automation:** auto-send only low-risk replies (e.g. rent due-date questions) with opt-in.
4. Continuous evaluation: log corrections as new labelled data; re-test monthly.

## 6. Limitations of this assessment

- Dataset is small (166) and synthetic, written by one author, so results are indicative, not production estimates.
- See the Technical Approach Report for measured results and exact caveats.
