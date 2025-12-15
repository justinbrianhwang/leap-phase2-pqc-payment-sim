from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Dict, Any, List

import numpy as np


def _to_np(xs: Iterable[float]) -> np.ndarray:
    arr = np.array(list(xs), dtype=float)
    if arr.size == 0:
        return np.array([float("nan")], dtype=float)
    return arr


def summary_stats_ms(values_ms: Iterable[float]) -> Dict[str, Any]:
    a = _to_np(values_ms)
    return {
        "count": int(a.size),
        "mean_ms": float(np.mean(a)),
        "p50_ms": float(np.percentile(a, 50)),
        "p90_ms": float(np.percentile(a, 90)),
        "p95_ms": float(np.percentile(a, 95)),
        "p99_ms": float(np.percentile(a, 99)),
        "max_ms": float(np.max(a)),
    }


def summary_stats_bytes(values: Iterable[int]) -> Dict[str, Any]:
    a = np.array(list(values), dtype=float)
    if a.size == 0:
        a = np.array([float("nan")], dtype=float)
    return {
        "count": int(a.size),
        "mean_bytes": float(np.mean(a)),
        "p50_bytes": float(np.percentile(a, 50)),
        "p95_bytes": float(np.percentile(a, 95)),
        "max_bytes": float(np.max(a)),
    }
