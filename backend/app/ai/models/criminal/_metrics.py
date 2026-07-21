"""Shared metric helpers for criminal AI models."""
from __future__ import annotations

import numpy as np


def binary_auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Approximate ROC-AUC via Mann-Whitney U statistic (no sklearn needed)."""
    scores = np.asarray(scores, dtype=np.float64)
    labels = np.asarray(labels, dtype=bool)
    pos = scores[labels]
    neg = scores[~labels]
    if pos.size == 0 or neg.size == 0:
        return 0.5
    u = float(sum(1 for p in pos for n in neg if p > n))
    return u / (pos.size * neg.size)
