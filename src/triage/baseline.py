"""Classic-ML baseline: TF-IDF (word + char n-grams) -> logistic regression.

Char n-grams help with typos, Hinglish and creative spelling.
Two independent models: one for category, one for urgency.
"""
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from .rules import is_emergency, extract_unit, extract_time
from .schemas import TriageResult


def make_pipeline() -> Pipeline:
    feats = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), lowercase=True, sublinear_tf=True, min_df=1)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), lowercase=True, sublinear_tf=True, min_df=2)),
    ])
    clf = LogisticRegression(C=10, max_iter=2000, class_weight="balanced")
    return Pipeline([("tfidf", feats), ("clf", clf)])


class BaselineTriager:
    def __init__(self):
        self.cat_model = make_pipeline()
        self.urg_model = make_pipeline()

    def fit(self, texts, categories, urgencies):
        self.cat_model.fit(texts, categories)
        self.urg_model.fit(texts, urgencies)
        return self

    def save(self, path):
        joblib.dump(self, path)

    @staticmethod
    def load(path):
        return joblib.load(path)

    def triage(self, text: str, safety_net: bool = True) -> TriageResult:
        from .replies import build_reply, build_task
        cat = self.cat_model.predict([text])[0]
        urg = self.urg_model.predict([text])[0]
        if safety_net and is_emergency(text):
            urg = "emergency"
        r = TriageResult(category=cat, urgency=urg, unit=extract_unit(text),
                         time_mentioned=extract_time(text), source="baseline+rules")
        r.tenant_reply, r.manager_task = build_reply(r), build_task(r, text)
        r.needs_human_review = urg in ("emergency", "high")
        return r
