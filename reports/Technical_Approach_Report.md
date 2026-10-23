# Technical Approach Report: TenantEase Message Triage

**Applicant:** Anshi Agrawal | AI/ML Engineer Intern assessment | Cynbit

## 1. Problem framing
Given a free-text tenant message, predict **category** (5 classes) and **urgency** (4 ordered classes), extract **unit / issue / time**, and draft a **tenant reply** and **manager task**. Error costs are asymmetric: missing an emergency is far worse than over-escalating a low-priority message, so urgency is evaluated with emphasis on **emergency recall**.

## 2. Data (synthetic: please read)
- **No public dataset exists**, so I created **166 realistic messages** covering English, Hinglish, typos, shorthand and vague wording, as well as tricky cases (e.g. "water near the switchboard" is an emergency; "kids running upstairs" is low priority; "double amount deducted" is high priority in the payment category).
- Labels (category, urgency, unit, issue, time) were assigned and hand-checked by me. A **single annotator** labelled all rows, so no inter-annotator agreement exists. Urgency is partly subjective.
- Distribution: plumbing 42, general 37, electrical 35, payment_query 29, noise_complaint 23; emergency 24, high 32, normal 60, low 50.
- **Caveat:** the messages and labels were produced by the same author who wrote the keyword rules, which makes any rule-based number optimistic (see section 5).
- **What real data would replace this:** anonymised WhatsApp/call-note/in-app messages from TenantEase landlords, labelled by property managers, with urgency decisions and actual response times as ground truth. Names, phone numbers and addresses would be removed first.

Files: `data/messages.csv` (pipe-separated).

## 3. Approaches compared

| # | Approach | Details |
|---|---|---|
| 1 | **TF-IDF + Logistic Regression** | Word (1-2) + character (2-5) n-grams (robust to typos/Hinglish), class-weight balanced, separate models for category and urgency |
| 2 | **Baseline + emergency safety net** | Same model, but a keyword/regex layer forces `emergency` for gas, fire, smoke, sparks, burst pipes, shocks, flooding, stuck lift, etc. |
| 3 | **Rules only** | Keyword category/urgency + regex field extraction (also the offline fallback in the app) |
| 4 | **LLM, structured JSON** | Prompted LLM returns category, urgency, fields, tenant reply, manager task as JSON; output validated against allowed enums; unknown values escalate; retry once; falls back to rules if the API fails. Implemented in `src/triage/llm.py` |

**Evaluation protocol:** 5-fold stratified cross-validation (seed 42) with out-of-fold predictions, so the baseline is never scored on its training rows. Metrics: accuracy, per-class precision/recall/F1, macro-F1, confusion matrices, emergency recall, and **under-triage rate** (emergency/high messages predicted as less urgent).

## 4. Results (measured on the 166 synthetic messages)

| Approach | Category acc | Category macro-F1 | Urgency acc | Urgency macro-F1 | **Emergency recall** | Under-triage (emerg.+high) |
|---|---|---|---|---|---|---|
| TF-IDF + LR | 0.681 | 0.681 | 0.452 | 0.435 | 0.375 | 0.625 |
| TF-IDF + LR + safety net | 0.681 | 0.681 | 0.530 | 0.542 | **0.917** | 0.375 |
| Rules only (optimistic, see caveat) | 0.880 | 0.875 | 0.657 | 0.671 | 0.875 | 0.268 |
| LLM (JSON) | *not run in this build* | | | | | |

**Extraction (regex):** unit exact-match 0.855, time-phrase match 0.843. Issue-phrase extraction needs the LLM (regex does not produce one).

Per-class results are in `results/metrics.json`; confusion matrices in `reports/figures/`.

### The LLM row
The LLM could not be run when this build was produced because it needs an API key and network access. The evaluation script is ready: `python scripts/evaluate.py --llm` (with `ANTHROPIC_API_KEY` set) adds `llm` and `llm+safety_net` rows to `results/metrics.json`, the console table and the confusion matrices. **No LLM numbers are claimed in this report.** I treat these as hypotheses to test, not findings:
- H1: the LLM beats TF-IDF on **urgency** (needs world knowledge: gas smell > squeaky door) and on **issue extraction**.
- H2: TF-IDF is competitive for **category**.
(In my data the baseline's category accuracy is only 0.68, so H2 may fail at this small size; the result will show.)

## 5. Findings and error analysis (baseline family)
1. **Urgency is much harder than category** for a bag-of-words model (0.45 vs 0.68 accuracy). Urgency depends on semantics ("water near switchboard") rather than topic words.
2. **A cheap safety net matters most.** Adding keyword escalation raised emergency recall from **0.375 to 0.917** (22 of 24) and cut under-triage from 0.625 to 0.375. This is the single most useful design decision for the stated risk.
3. **Trade-off:** the safety net over-escalates. Emergency precision is 0.71, so some non-emergencies are escalated (e.g. a toilet overflowing into a hallway, labelled "high", was flagged as an emergency). This is acceptable for safety-critical triage but needs tracking for alert fatigue.
4. **The two missed emergencies** were "main water line leaking in parking, water gushing out like a fountain" and "meter is making buzzing sound and hot to touch". These are phrasings the keyword list does not cover, which shows why a language model (or more data) is needed for generalisation. I deliberately did **not** tune the rules on these misses so that the reported number stays honest.
5. **Weakest categories** for the baseline: general (F1 0.56) and electrical (0.58), classes with a diverse vocabulary and little training data. payment_query is easiest (0.85).
6. **Rules-only scored higher than the ML baseline**, but I wrote the rules after seeing this dataset, so this is not a fair generalisation estimate. A fair test needs messages the rule-writer never saw.

## 6. System design
```
tenant message -> [PII scrub] -> LLM JSON triage -> schema/enum validation
              -> emergency safety net (rules) -> needs_human_review flag
              -> manager inbox (task) + draft reply (sent only after review for emergency/high)
```
- **Streamlit prototype** (`app/streamlit_app.py`): paste a message, choose LLM or baseline, toggle the safety net, see category, urgency, fields, drafts and the human-review flag.
- **FastAPI** (`api/main.py`): `POST /triage` returns the same JSON, showing how TenantEase would call the service (include `property_id`/`tenant_id` for routing).
- **Prompt design:** message passed as data inside tags, explicit definitions of each urgency level, "choose the more urgent level when unsure for safety issues", reply must match the tenant's language and must not promise times or costs, JSON only, temperature 0.
- **Failure handling:** invalid JSON gets one retry; then rule-based fallback with urgency escalated and human review forced; unknown enum values map to `high`.

## 7. Limitations and next steps
- Small synthetic single-annotator dataset; accuracy numbers should not be extrapolated to production.
- LLM results are pending a run with an API key (one command).
- Next steps: (1) collect real labelled messages in shadow mode; (2) add a held-out test set written by someone other than the rule author; (3) measure per-language slices (English vs Hinglish); (4) calibrate/threshold for emergency recall >= 98%; (5) evaluate reply quality with manager ratings; (6) add PII scrubbing before the LLM call; (7) cost and latency monitoring.
