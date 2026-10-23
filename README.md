# TenantEase Triage: AI for maintenance and tenant-message triage

AI/ML Engineer Intern assessment for Cynbit: *Identify an AI Opportunity for Cynbit*.
Every incoming tenant message is **classified**, **urgency-scored**, **parsed for details** (unit, issue, time) and gets a **drafted tenant reply and manager task**. Emergencies are designed for high recall with a human in the loop.

> **All data is synthetic** (166 messages written for this project; see the Technical Approach Report for what real data would replace it).

## Deliverables
| Deliverable | File |
|---|---|
| AI Opportunity Report | [`reports/AI_Opportunity_Report.md`](reports/AI_Opportunity_Report.md) |
| AI/ML Proof of Concept | Streamlit app `app/streamlit_app.py`, API `api/main.py`, pipeline `src/triage/` |
| Technical Approach Report | [`reports/Technical_Approach_Report.md`](reports/Technical_Approach_Report.md) |

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python scripts/evaluate.py          # baseline + rules, trains results/baseline_model.joblib
streamlit run app/streamlit_app.py  # demo app
uvicorn api.main:app --reload       # optional API -> POST /triage
python -m pytest -q                 # tests
```

### Enable the LLM approach
```bash
export ANTHROPIC_API_KEY=...        # Windows PowerShell: $env:ANTHROPIC_API_KEY="..."
# optional: export TENANTEASE_LLM_MODEL=claude-sonnet-5-5
python scripts/evaluate.py --llm    # adds LLM rows to results/metrics.json (cached)
```
Without a key, the app transparently falls back to the rule-based triager and says so in the "Produced by" line.

## Results so far (5-fold CV, 166 synthetic messages)
| Approach | Category acc | Urgency acc | Emergency recall |
|---|---|---|---|
| TF-IDF + LR | 0.681 | 0.452 | 0.375 |
| TF-IDF + LR + safety net | 0.681 | 0.530 | **0.917** |
| Rules only* | 0.880 | 0.657 | 0.875 |
| LLM | run `--llm` | | |

\*optimistic: rules were written after seeing the data. Details and error analysis are in the Technical Approach Report.

## Layout
```
data/messages.csv          synthetic labelled set (pipe-separated)
src/triage/                schemas, rules (regex + safety net), baseline, llm, replies
scripts/evaluate.py        metrics, confusion matrices, trains app model
app/streamlit_app.py       demo UI
api/main.py                FastAPI /triage
reports/                   the two reports + confusion-matrix figures
results/metrics.json       measured results
tests/                     unit tests
```

## Safety design
Emergency keyword safety net on top of any model, LLM output validated against allowed values with unknown urgency escalated, a human-review flag on emergency/high messages, drafts never auto-sent for those, message treated as data in the prompt. See the reports for privacy notes (DPDP Act 2023).
