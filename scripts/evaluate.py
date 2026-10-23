"""Evaluate all approaches on the labelled synthetic set.

  python scripts/evaluate.py            # baseline (5-fold CV) + rules + hybrid
  python scripts/evaluate.py --llm      # also runs the LLM (needs ANTHROPIC_API_KEY); cached in results/
"""
import argparse, json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.triage.baseline import BaselineTriager, make_pipeline  # noqa: E402
from src.triage.data import load_data  # noqa: E402
from src.triage.rules import rule_triage, is_emergency, extract_unit, extract_time  # noqa: E402
from src.triage.schemas import CATEGORIES, URGENCIES  # noqa: E402

RES, FIG = ROOT / "results", ROOT / "reports" / "figures"


def norm(x):
    return (x or "").strip().lower().replace(" ", "")


def time_match(pred, true):
    pred, true = (pred or "").lower().strip(), (true or "").lower().strip()
    if not true and not pred:
        return True
    if not true or not pred:
        return False
    return pred in true or true in pred


def metrics(y_true, y_pred, labels):
    rep = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)
    return {
        "accuracy": round(accuracy_score(y_true, y_pred), 3),
        "macro_f1": round(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0), 3),
        "per_class": {l: {k: round(rep[l][k], 3) for k in ("precision", "recall", "f1-score")} | {"support": int(rep[l]["support"])} for l in labels},
    }


def urgency_extras(y_true, y_pred):
    order = {u: i for i, u in enumerate(URGENCIES)}  # 0 = most urgent
    under = [order[p] > order[t] for t, p in zip(y_true, y_pred) if t in ("emergency", "high")]
    em = [(t, p) for t, p in zip(y_true, y_pred) if t == "emergency"]
    return {
        "emergency_recall": round(sum(p == "emergency" for _, p in em) / len(em), 3),
        "emergency_missed_as_low_or_normal": sum(p in ("normal", "low") for _, p in em),
        "under_triage_rate_(emergency+high)": round(float(np.mean(under)), 3),
    }


def extraction_scores(df, preds_unit, preds_time):
    unit_ok = [norm(p) == norm(t) for p, t in zip(preds_unit, df.unit)]
    time_ok = [time_match(p, t) for p, t in zip(preds_time, df.time_mentioned)]
    return {"unit_exact_match": round(float(np.mean(unit_ok)), 3), "time_match": round(float(np.mean(time_ok)), 3)}


def plot_cm(y_true, y_pred, labels, title, fname):
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    plt.figure(figsize=(5.2, 4.4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels, cbar=False)
    plt.xlabel("Predicted"); plt.ylabel("True"); plt.title(title, fontsize=10)
    plt.xticks(rotation=30, ha="right"); plt.tight_layout()
    plt.savefig(FIG / fname, dpi=150); plt.close()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--llm", action="store_true"); args = ap.parse_args()
    df = load_data(); X = df.message.tolist()
    skf = StratifiedKFold(5, shuffle=True, random_state=42)
    out = {"n_messages": len(df), "approaches": {}}
    preds = {}

    # 1. Baseline: TF-IDF + LR (cross-validated predictions, no leakage)
    cat_cv = cross_val_predict(make_pipeline(), X, df.category, cv=skf)
    urg_cv = cross_val_predict(make_pipeline(), X, df.urgency, cv=StratifiedKFold(5, shuffle=True, random_state=42))
    preds["tfidf_lr"] = (cat_cv, urg_cv)
    # 2. Baseline + emergency keyword safety net
    urg_hyb = np.array(["emergency" if is_emergency(t) else u for t, u in zip(X, urg_cv)])
    preds["tfidf_lr+safety_net"] = (cat_cv, urg_hyb)
    # 3. Pure rules/keywords
    rr = [rule_triage(t) for t in X]
    preds["rules_only"] = ([r.category for r in rr], [r.urgency for r in rr])
    extraction = {"regex": extraction_scores(df, [r.unit for r in rr], [r.time_mentioned for r in rr])}

    # 4. LLM (optional)
    if args.llm:
        from src.triage.llm import triage as llm_triage, llm_available
        if not llm_available():
            sys.exit("ANTHROPIC_API_KEY / anthropic SDK not available; cannot run --llm.")
        cache = RES / "llm_predictions.json"
        cached = json.loads(cache.read_text()) if cache.exists() else {}
        for t in X:
            if t not in cached:
                cached[t] = llm_triage(t, safety_net=False).to_dict()
        cache.write_text(json.dumps(cached, indent=1, ensure_ascii=False))
        lr_ = [cached[t] for t in X]
        preds["llm"] = ([r["category"] for r in lr_], [r["urgency"] for r in lr_])
        preds["llm+safety_net"] = (preds["llm"][0], ["emergency" if is_emergency(t) else u for t, u in zip(X, preds["llm"][1])])
        extraction["llm"] = extraction_scores(df, [r["unit"] for r in lr_], [r["time_mentioned"] for r in lr_])

    for name, (c, u) in preds.items():
        out["approaches"][name] = {
            "category": metrics(df.category, c, CATEGORIES),
            "urgency": metrics(df.urgency, u, URGENCIES) | urgency_extras(df.urgency, u),
        }
        plot_cm(df.category, c, CATEGORIES, f"Category - {name}", f"cm_category_{name.replace('+','_')}.png")
        plot_cm(df.urgency, u, URGENCIES, f"Urgency - {name}", f"cm_urgency_{name.replace('+','_')}.png")
    out["extraction"] = extraction
    (RES / "metrics.json").write_text(json.dumps(out, indent=2))

    print(f"\n{len(df)} messages\n")
    print(f"{'approach':24s} {'cat acc':>8s} {'cat F1':>7s} {'urg acc':>8s} {'urg F1':>7s} {'emerg recall':>13s} {'under-triage':>13s}")
    for n, v in out["approaches"].items():
        print(f"{n:24s} {v['category']['accuracy']:8.3f} {v['category']['macro_f1']:7.3f} {v['urgency']['accuracy']:8.3f} "
              f"{v['urgency']['macro_f1']:7.3f} {v['urgency']['emergency_recall']:13.3f} {v['urgency']['under_triage_rate_(emergency+high)']:13.3f}")
    print("\nextraction:", json.dumps(extraction))

    # final model for the app
    BaselineTriager().fit(X, df.category, df.urgency).save(RES / "baseline_model.joblib")


if __name__ == "__main__":
    main()
