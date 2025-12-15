#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

# This script creates *synthetic* results that roughly match the Project Leap Phase 2
# headline verification-time gap (PQC >> traditional). It's meant for README visuals.

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def summarize_ms(xs: List[float]) -> Dict[str, float]:
    a = np.array(xs, dtype=float)
    return {
        "count": int(a.size),
        "mean_ms": float(a.mean()),
        "p50_ms": float(np.percentile(a, 50)),
        "p90_ms": float(np.percentile(a, 90)),
        "p95_ms": float(np.percentile(a, 95)),
        "p99_ms": float(np.percentile(a, 99)),
        "max_ms": float(a.max()),
    }


def summarize_bytes(xs: List[int]) -> Dict[str, float]:
    a = np.array(xs, dtype=float)
    return {
        "count": int(a.size),
        "mean_bytes": float(a.mean()),
        "p50_bytes": float(np.percentile(a, 50)),
        "p95_bytes": float(np.percentile(a, 95)),
        "max_bytes": float(a.max()),
    }


def make_dist(mean: float, std: float, n: int, seed: int) -> List[float]:
    rng = np.random.default_rng(seed)
    xs = rng.normal(loc=mean, scale=std, size=n)
    xs = np.clip(xs, a_min=0.1, a_max=None)
    return xs.tolist()


def make_result(mode: str, n: int, verify_ms: List[float], sign_ms: List[float], size_b: List[int]) -> Dict[str, object]:
    wall_time_s = float(sum(verify_ms) / 1000.0)  # toy
    throughput = float(n / wall_time_s) if wall_time_s > 0 else float("inf")
    total_ms = [v + s + 2.0 for v, s in zip(verify_ms, sign_ms)]  # add tiny network
    return {
        "meta": {
            "timestamp": now_iso(),
            "mode": mode,
            "n": n,
            "concurrency": 8,
            "pqc_backend": "mock",
            "oqs_alg": None,
            "mock_level": 3,
            "fault": None,
        },
        "summary": {
            "accepted": n,
            "rejected": 0,
            "wall_time_s": wall_time_s,
            "throughput_msg_per_s": throughput,
            "signing": summarize_ms(sign_ms),
            "verification": summarize_ms(verify_ms),
            "end_to_end": summarize_ms(total_ms),
            "message_size": summarize_bytes(size_b),
        },
        "raw": {
            "sign_times_ms": sign_ms,
            "verify_times_ms": verify_ms,
            "total_times_ms": total_ms,
            "sizes_bytes": size_b,
        },
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    n = 200

    # Roughly aligned to the Phase-2 report headline numbers:
    # - traditional verification ~28 ms
    # - PQC verification ~210 ms
    verify_rsa = make_dist(mean=28.1, std=6.0, n=n, seed=1)
    verify_pqc = make_dist(mean=209.9, std=35.0, n=n, seed=2)
    verify_hyb = [(a + b) for a, b in zip(verify_rsa, verify_pqc)]

    sign_rsa = make_dist(mean=6.0, std=2.0, n=n, seed=3)
    sign_pqc = make_dist(mean=45.0, std=10.0, n=n, seed=4)
    sign_hyb = [(a + b) for a, b in zip(sign_rsa, sign_pqc)]

    # Base message size (without signatures), then add signature overhead.
    base = 850
    sig_rsa = 256
    sig_pqc = 3293
    size_rsa = [base + sig_rsa for _ in range(n)]
    size_pqc = [base + sig_pqc for _ in range(n)]
    size_hyb = [base + sig_rsa + sig_pqc for _ in range(n)]

    (RESULTS_DIR / "example_rsa.json").write_text(json.dumps(make_result("rsa", n, verify_rsa, sign_rsa, size_rsa), indent=2), encoding="utf-8")
    (RESULTS_DIR / "example_pqc.json").write_text(json.dumps(make_result("pqc", n, verify_pqc, sign_pqc, size_pqc), indent=2), encoding="utf-8")
    (RESULTS_DIR / "example_hybrid.json").write_text(json.dumps(make_result("hybrid", n, verify_hyb, sign_hyb, size_hyb), indent=2), encoding="utf-8")

    print("Wrote example results to results/example_*.json")


if __name__ == "__main__":
    main()
