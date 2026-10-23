"""Minimal FastAPI service showing how triage would plug into TenantEase.
Run:  uvicorn api.main:app --reload     then POST /triage
"""
import sys
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.triage import llm  # noqa: E402

app = FastAPI(title="TenantEase Triage API", version="0.1")


class TriageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    property_id: str | None = None
    tenant_id: str | None = None


@app.get("/health")
def health():
    return {"status": "ok", "llm_available": llm.llm_available()}


@app.post("/triage")
def triage(req: TriageRequest):
    res = llm.triage(req.message).to_dict()
    return {"property_id": req.property_id, "tenant_id": req.tenant_id, **res}
