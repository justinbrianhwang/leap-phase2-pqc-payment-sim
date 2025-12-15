#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running without installing the package
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from leap_pqc_sim.sim import SimulationConfig, run_benchmark  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run a Project-Leap-Phase2-style PQC signature benchmark (toy).")
    p.add_argument("--mode", choices=["rsa", "pqc", "hybrid"], default="pqc")
    p.add_argument("--n", type=int, default=200)
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--pqc-backend", choices=["mock", "oqs"], default="mock")
    p.add_argument("--oqs-alg", type=str, default="Dilithium3")
    p.add_argument("--mock-level", type=int, choices=[2, 3, 5], default=3)
    p.add_argument("--fault", choices=["invalid_sig", "unknown_kid"], default=None)
    p.add_argument("--network-delay-ms", type=float, default=0.5)
    p.add_argument("--out", type=str, default="results/out.json")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    cfg = SimulationConfig(
        mode=args.mode,
        n=args.n,
        concurrency=args.concurrency,
        pqc_backend=args.pqc_backend,
        oqs_alg=args.oqs_alg,
        mock_level=args.mock_level,
        fault=args.fault,
        network_delay_ms=args.network_delay_ms,
    )

    result = run_benchmark(cfg)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    # concise console output
    s = result["summary"]
    print("=== Benchmark done ===")
    print(f"mode={args.mode}  pqc_backend={args.pqc_backend}  n={args.n}  concurrency={args.concurrency}")
    print(f"accepted={s['accepted']}  rejected={s['rejected']}")
    print(f"throughput={s['throughput_msg_per_s']:.2f} msg/s  wall={s['wall_time_s']:.2f}s")
    print(f"verify_mean={s['verification']['mean_ms']:.2f}ms  p95={s['verification']['p95_ms']:.2f}ms")
    print(f"size_mean={s['message_size']['mean_bytes']:.0f} bytes")
    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
