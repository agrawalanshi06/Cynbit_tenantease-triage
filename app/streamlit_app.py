"""TenantEase Triage demo.  Run:  streamlit run app/streamlit_app.py"""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.triage import llm  # noqa: E402
from src.triage.baseline import BaselineTriager  # noqa: E402

st.set_page_config(page_title="TenantEase Triage", page_icon="🏠", layout="wide")
st.title("🏠 TenantEase: Message Triage")
st.caption("Paste a tenant message. The AI classifies it, scores urgency, extracts details and drafts replies. "
           "Demo uses synthetic data only.")

EXAMPLES = [
    "pipe burst in room 204 water everywhere pls come fast",
    "A-203 mein bathroom ka pipe leak ho raha hai, subah se",
    "I paid rent via UPI on 3rd but app still shows pending. flat 204",
    "loud music from flat 305 at 2 am, cant sleep",
    "I can smell gas in the kitchen, please send someone right now. flat 42",
    "Tube light in the balcony is fused please change, 24B",
]
BADGE = {"emergency": "🔴 EMERGENCY", "high": "🟠 HIGH", "normal": "🟡 NORMAL", "low": "🟢 LOW"}


@st.cache_resource
def get_baseline():
    p = ROOT / "results" / "baseline_model.joblib"
    return BaselineTriager.load(p) if p.exists() else None


with st.sidebar:
    st.header("Settings")
    options = ["LLM (JSON output)", "Baseline (TF-IDF + LR)"]
    mode = st.radio("Approach", options)
    safety = st.toggle("Emergency safety net", value=True,
                       help="Keyword rules that force 'emergency' when e.g. gas/fire/sparks are mentioned.")
    st.write("LLM key detected: **" + ("yes" if llm.llm_available() else "no (rule-based fallback)") + "**")
    st.divider()
    ex = st.selectbox("Load example", ["(none)"] + EXAMPLES)

msg = st.text_area("Tenant message", value="" if ex == "(none)" else ex, height=110,
                   placeholder="e.g. tap leaking in room 204")

if st.button("Triage", type="primary") and msg.strip():
    if mode.startswith("LLM"):
        res = llm.triage(msg, safety_net=safety)
    else:
        model = get_baseline()
        if model is None:
            st.error("Run `python scripts/evaluate.py` first to train the baseline model.")
            st.stop()
        res = model.triage(msg, safety_net=safety)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Category", res.category)
    c2.metric("Urgency", BADGE[res.urgency])
    c3.metric("Unit", res.unit or "-")
    c4.metric("Time mentioned", res.time_mentioned or "-")
    if res.issue:
        st.write(f"**Issue:** {res.issue}")
    if res.needs_human_review:
        st.warning("👤 Flagged for human review: a manager must confirm before any automated reply is sent.")
    left, right = st.columns(2)
    left.subheader("✉️ Draft reply to tenant"); left.info(res.tenant_reply)
    right.subheader("📋 Task for manager"); right.success(res.manager_task)
    st.caption(f"Produced by: {res.source}")
