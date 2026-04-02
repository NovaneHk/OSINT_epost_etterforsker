"""
Predictive lead scorer using TF-IDF cosine similarity against historically
converted/verified leads.  No heavy ML dependency — pure Python + math.
"""

import logging
import math
import re
import time
from collections import Counter
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TF-IDF helper (no sklearn needed)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _tfidf_vector(tokens: List[str], idf: Dict[str, float]) -> Dict[str, float]:
    tf = Counter(tokens)
    total = max(len(tokens), 1)
    return {t: (count / total) * idf.get(t, 0.0) for t, count in tf.items()}


def _cosine_sim(a: Dict[str, float], b: Dict[str, float]) -> float:
    shared = set(a) & set(b)
    if not shared:
        return 0.0
    dot = sum(a[k] * b[k] for k in shared)
    mag_a = math.sqrt(sum(v * v for v in a.values()))
    mag_b = math.sqrt(sum(v * v for v in b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ---------------------------------------------------------------------------
# Predictor
# ---------------------------------------------------------------------------

class LeadPredictor:
    """
    Scores a lead 0–100 by measuring cosine similarity against the centroid
    of historically converted/verified leads.

    Train on first call, retrain every ``retrain_interval`` seconds.
    """

    def __init__(self, retrain_interval: int = 3600):
        self._centroid: Optional[Dict[str, float]] = None
        self._idf: Dict[str, float] = {}
        self._trained_at: float = 0.0
        self._retrain_interval = retrain_interval
        self._corpus_size: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def train(self, db=None) -> None:
        """Load positive-class leads from the database and compute the centroid."""
        if db is None:
            # Lazy import to avoid circular dependencies at module level
            from backend.core.database import db_manager as _db
            db = _db

        try:
            rows = db.execute_query(
                """SELECT company, job_title, industry, domain, location
                   FROM leads
                   WHERE LOWER(verification_status) IN ('verified', 'converted', 'contacted')
                   LIMIT 2000"""
            )
        except Exception as exc:
            logger.warning("LeadPredictor: could not load training data: %s", exc)
            rows = []

        if not rows:
            logger.info("LeadPredictor: no positive-class leads found — scoring will return 50")
            self._centroid = None
            self._trained_at = time.time()
            return

        # Build corpus
        docs: List[List[str]] = [
            _tokenize(
                f"{r.get('company', '')} {r.get('job_title', '')} "
                f"{r.get('industry', '')} {r.get('domain', '')} {r.get('location', '')}"
            )
            for r in rows
        ]

        # Compute IDF
        df: Counter = Counter()
        for tokens in docs:
            df.update(set(tokens))
        n = len(docs)
        self._idf = {t: math.log((n + 1) / (cnt + 1)) + 1 for t, cnt in df.items()}
        self._corpus_size = n

        # Compute centroid of TF-IDF vectors
        centroid: Dict[str, float] = {}
        for tokens in docs:
            vec = _tfidf_vector(tokens, self._idf)
            for k, v in vec.items():
                centroid[k] = centroid.get(k, 0.0) + v / n
        self._centroid = centroid
        self._trained_at = time.time()
        logger.info("LeadPredictor: trained on %d positive leads", n)

    def predict(self, lead: Dict[str, Any], db=None) -> float:
        """Return a predicted quality score 0.0–100.0 for the given lead dict."""
        if time.time() - self._trained_at > self._retrain_interval:
            self.train(db)

        if self._centroid is None:
            return 50.0  # No training data — neutral score

        tokens = _tokenize(
            f"{lead.get('company', '')} {lead.get('job_title', '')} "
            f"{lead.get('industry', '')} {lead.get('domain', '')} {lead.get('location', '')}"
        )
        if not tokens:
            return 50.0

        vec = _tfidf_vector(tokens, self._idf)
        sim = _cosine_sim(vec, self._centroid)
        # Sigmoid calibration: maps [0,1] similarity to [5,95] score with smooth curve
        sigmoid_score = 1 / (1 + math.exp(-10 * (sim - 0.3))) * 90 + 5
        return max(10.0, min(98.0, round(sigmoid_score, 1)))


# Global singleton — trained lazily on first predict() call
lead_predictor = LeadPredictor()
