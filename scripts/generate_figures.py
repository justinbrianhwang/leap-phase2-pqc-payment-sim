#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate plots from results/*.json files.")
    p.add_argument("--inputs", nargs="+", required=True, help="One or more result JSON files.")
    p.add_argument("--outdir", default="figures", help="Output directory for PNG files.")
    return p.parse_args()


def _label(meta: Dict[str, object]) -> str:
    mode = meta.get("mode")
    backend = meta.get("pqc_backend")
    if mode == "rsa":
        return "RSA"
    if mode == "pqc":
        if backend == "oqs":
            return f"PQC({meta.get('oqs_alg')})"
        return "PQC(mock)"
    if mode == "hybrid":
        if backend == "oqs":
            return f"Hybrid(RSA+{meta.get('oqs_alg')})"
        return "Hybrid(RSA+mock)"
    return str(mode)


def _load(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def plot_verification_cdf(results: List[Dict[str, object]], outdir: Path) -> None:
    plt.figure()
    for r in results:
        meta = r["meta"]
        xs = np.array(r["raw"]["verify_times_ms"], dtype=float)
        xs = np.sort(xs)
        ys = np.arange(1, len(xs) + 1) / len(xs)
        plt.plot(xs, ys, label=_label(meta))

    plt.xlabel("Gateway signature verification time (ms)")
    plt.ylabel("CDF")
    plt.title("Verification time distribution (CDF)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    out_path = outdir / "verification_cdf.png"
    plt.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close()


def plot_message_size_bar(results: List[Dict[str, object]], outdir: Path) -> None:
    labels = [_label(r["meta"]) for r in results]
    means = [r["summary"]["message_size"]["mean_bytes"] for r in results]

    plt.figure()
    x = np.arange(len(labels))
    plt.bar(x, means)
    plt.xticks(x, labels, rotation=20, ha="right")
    plt.ylabel("Mean serialized message size (bytes)")
    plt.title("Message size impact")
    plt.grid(True, axis="y", alpha=0.3)
    out_path = outdir / "message_size_bar.png"
    plt.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close()


def plot_throughput_bar(results: List[Dict[str, object]], outdir: Path) -> None:
    labels = [_label(r["meta"]) for r in results]
    thr = [r["summary"]["throughput_msg_per_s"] for r in results]

    plt.figure()
    x = np.arange(len(labels))
    plt.bar(x, thr)
    plt.xticks(x, labels, rotation=20, ha="right")
    plt.ylabel("Throughput (messages / second)")
    plt.title("End-to-end throughput")
    plt.grid(True, axis="y", alpha=0.3)
    out_path = outdir / "throughput_bar.png"
    plt.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close()


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    results = [_load(Path(p)) for p in args.inputs]

    plot_verification_cdf(results, outdir)
    plot_message_size_bar(results, outdir)
    plot_throughput_bar(results, outdir)

    print(f"Wrote plots to: {outdir}")


if __name__ == "__main__":
    main()
