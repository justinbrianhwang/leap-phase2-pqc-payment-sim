#!/usr/bin/env python3
from __future__ import annotations

"""Toy Shor period-finding demo with PennyLane.

This script is *educational* and only factors N=15, to illustrate the intuition behind
why RSA/ECDSA-style public-key cryptography is threatened by Shor's algorithm.

It is NOT a practical attack on real key sizes.
"""

import argparse
from fractions import Fraction
from math import gcd
from pathlib import Path
from typing import List, Tuple

import numpy as np

try:
    import pennylane as qml
except Exception as e:  # pragma: no cover
    raise SystemExit(
        "PennyLane is not installed. Install optional deps:
"
        "  pip install -r requirements-quantum.txt
"
    ) from e


def build_mul_unitary(a: int, N: int, n_work: int) -> np.ndarray:
    """Unitary that maps |y> -> |(a*y mod N)> for y < N, else identity.

    For N=15 with n_work=4, this is a 16x16 permutation matrix.
    """
    dim = 2**n_work
    U = np.zeros((dim, dim), dtype=complex)
    for y in range(dim):
        if y < N:
            y2 = (a * y) % N
        else:
            y2 = y
        U[y2, y] = 1.0
    return U


def inverse_qft(wires: List[int]) -> None:
    """In-place inverse QFT (QFT†) on `wires`."""
    n = len(wires)

    # Swap to reverse order
    for i in range(n // 2):
        qml.SWAP(wires=[wires[i], wires[n - 1 - i]])

    # QFT†
    for j in range(n):
        for m in range(j):
            angle = -np.pi / (2 ** (j - m))
            qml.ControlledPhaseShift(angle, wires=[wires[m], wires[j]])
        qml.Hadamard(wires=wires[j])


def continued_fraction_period(phase: float, max_den: int) -> int:
    """Approximate phase as a rational s/r and return r."""
    frac = Fraction(phase).limit_denominator(max_den)
    return frac.denominator


def run_shor(N: int = 15, a: int = 2, n_count: int = 4, shots: int = 2000) -> Tuple[dict, List[int]]:
    n_work = int(np.ceil(np.log2(N)))
    assert 2**n_work >= N

    U = build_mul_unitary(a, N, n_work)

    dev = qml.device("default.qubit", wires=n_count + n_work, shots=shots)

    count_wires = list(range(n_count))
    work_wires = list(range(n_count, n_count + n_work))

    @qml.qnode(dev)
    def circuit():
        # |1> in work register
        qml.PauliX(wires=work_wires[0])

        # Hadamards on counting register
        for w in count_wires:
            qml.Hadamard(wires=w)

        # Controlled-U^(2^j)
        for j, ctrl in enumerate(count_wires):
            power = 2**j
            U_pow = np.linalg.matrix_power(U, power)
            qml.ControlledQubitUnitary(U_pow, control_wires=ctrl, wires=work_wires)

        # Inverse QFT
        inverse_qft(count_wires)

        return qml.sample(wires=count_wires)

    samples = circuit()

    # samples shape: (shots, n_count) with bits
    # Convert bits to integer
    ints = []
    for bits in samples:
        v = 0
        for i, b in enumerate(bits):
            v |= (int(b) << i)
        ints.append(v)

    # Histogram
    hist = {}
    for v in ints:
        hist[v] = hist.get(v, 0) + 1

    # Candidate periods from observed phases
    periods = []
    for v, c in hist.items():
        phase = v / (2**n_count)
        r = continued_fraction_period(phase, max_den=N)
        if r > 1:
            periods.append(r)

    return hist, periods


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--N", type=int, default=15)
    p.add_argument("--a", type=int, default=2)
    p.add_argument("--n-count", type=int, default=4)
    p.add_argument("--shots", type=int, default=2000)
    p.add_argument("--out", type=str, default="figures/shor_n15_distribution.png")
    args = p.parse_args()

    hist, periods = run_shor(N=args.N, a=args.a, n_count=args.n_count, shots=args.shots)

    # Attempt to recover factors (toy)
    factors = set()
    for r in periods:
        if r % 2 != 0:
            continue
        x = pow(args.a, r // 2, args.N)
        f1 = gcd(x - 1, args.N)
        f2 = gcd(x + 1, args.N)
        if 1 < f1 < args.N:
            factors.add(f1)
        if 1 < f2 < args.N:
            factors.add(f2)

    print(f"Observed candidate periods: {sorted(periods)}")
    print(f"Recovered factors (may be empty depending on sampling): {sorted(factors)}")

    # Plot distribution
    import matplotlib.pyplot as plt

    keys = sorted(hist.keys())
    vals = [hist[k] for k in keys]

    plt.figure()
    plt.bar([str(k) for k in keys], vals)
    plt.xlabel("Measured value (counting register)")
    plt.ylabel("Counts")
    plt.title(f"Shor period-finding measurement distribution (N={args.N}, a={args.a})")
    plt.xticks(rotation=45, ha="right")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close()

    print(f"Wrote plot to: {out_path}")


if __name__ == "__main__":
    main()
