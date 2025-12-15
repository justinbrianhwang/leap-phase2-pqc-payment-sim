from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, List, Literal, Optional, Tuple

from ..canonical import canonical_json_bytes
from ..models import BusinessApplicationHeader, LiquidityTransfer, PaymentMessage, SignatureEnvelope
from ..crypto import (
    KeyStore,
    RSAPSSSigner,
    MockDilithiumSigner,
    OQSDilithiumSigner,
    b64e,
    b64d,
    oqs_verify,
)

VerifyFn = Callable[[bytes, bytes, bytes], bool]


@dataclass
class SimulationConfig:
    mode: Literal["rsa", "pqc", "hybrid"] = "pqc"
    n: int = 200
    concurrency: int = 8

    # PQC settings
    pqc_backend: Literal["mock", "oqs"] = "mock"
    oqs_alg: str = "Dilithium3"
    mock_level: Literal[2, 3, 5] = 3

    # fault injection
    fault: Optional[Literal["invalid_sig", "unknown_kid"]] = None

    # networking (toy)
    network_delay_ms: float = 0.5  # constant delay per hop, for visibility


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize_message(msg: PaymentMessage) -> bytes:
    # Canonical JSON for size measurement
    s = json.dumps(msg.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return s.encode("utf-8")


def _build_transfer(i: int) -> Tuple[BusinessApplicationHeader, LiquidityTransfer]:
    bah = BusinessApplicationHeader(
        msg_id=str(uuid.uuid4()),
        from_party="BICDEFFXXX",  # toy identifiers
        to_party="BICITRRXXX",
        msg_def_id="head.001",
        creation_dt=_now_iso(),
    )
    doc = LiquidityTransfer(
        amount=float(1000 + i),
        currency="EUR",
        sender_account="CB-DE:RTGS:MAIN",
        receiver_account="CB-IT:RTGS:MAIN",
        reference=f"LEAP2-TOY-{i:06d}",
        requested_dt=_now_iso(),
    )
    return bah, doc


def _bah_bytes_for_signing(bah: BusinessApplicationHeader) -> bytes:
    # Phase-2 focus: signing the Business Application Header (BAH)
    return canonical_json_bytes(bah)


def _make_verify_registry(config: SimulationConfig) -> Dict[str, VerifyFn]:
    reg: Dict[str, VerifyFn] = {}

    # Traditional baseline
    reg["RSA-PSS-SHA256"] = RSAPSSSigner.verify

    # Mock PQC
    reg[f"MOCK-DILITHIUM{config.mock_level}"] = MockDilithiumSigner.verify

    # OQS PQC (if installed)
    reg[f"OQS-{config.oqs_alg}"] = lambda msg, sig, pk: oqs_verify(config.oqs_alg, msg, sig, pk)

    return reg


def _gateway_verify(
    msg: PaymentMessage,
    *,
    keystore: KeyStore,
    verify_registry: Dict[str, VerifyFn],
) -> Tuple[bool, float]:
    start = time.perf_counter()
    bah_bytes = _bah_bytes_for_signing(msg.bah)

    for env in msg.signatures:
        rec = keystore.get(env.kid)
        if rec.alg != env.alg:
            return False, (time.perf_counter() - start) * 1000

        if env.alg not in verify_registry:
            return False, (time.perf_counter() - start) * 1000

        ok = verify_registry[env.alg](bah_bytes, b64d(env.sig_b64), rec.public_key)
        if not ok:
            return False, (time.perf_counter() - start) * 1000

    return True, (time.perf_counter() - start) * 1000


def run_benchmark(config: SimulationConfig) -> Dict[str, object]:
    """Run a synthetic end-to-end benchmark.

    Returns a dict suitable for JSON serialization.
    """

    if config.n <= 0:
        raise ValueError("--n must be > 0")
    if config.concurrency <= 0:
        raise ValueError("--concurrency must be > 0")

    keystore = KeyStore()

    # Create signers
    rsa_signer = RSAPSSSigner.generate(kid="cbA-rsa-001")

    if config.pqc_backend == "mock":
        pqc_signer = MockDilithiumSigner.generate(kid="cbA-pqc-001", level=config.mock_level)
        pqc_alg = pqc_signer.alg
    else:
        pqc_signer = OQSDilithiumSigner.generate(kid="cbA-pqc-001", oqs_alg=config.oqs_alg)
        pqc_alg = pqc_signer.alg

    # Register public keys (mimics "static data" / certificate store)
    keystore.register(kid=rsa_signer.kid, alg=rsa_signer.alg, public_key=rsa_signer.public_key_bytes())
    keystore.register(kid=pqc_signer.kid, alg=pqc_alg, public_key=pqc_signer.public_key_bytes())

    verify_registry = _make_verify_registry(config)

    def process_one(i: int) -> Tuple[float, float, float, int, bool]:
        t0 = time.perf_counter()

        bah, doc = _build_transfer(i)
        bah_bytes = _bah_bytes_for_signing(bah)

        # signing
        t_sign0 = time.perf_counter()

        sigs: List[SignatureEnvelope] = []

        if config.mode in ("rsa", "hybrid"):
            sig = rsa_signer.sign(bah_bytes)
            kid = rsa_signer.kid
            alg = rsa_signer.alg

            if config.fault == "unknown_kid":
                kid = "does-not-exist"
            if config.fault == "invalid_sig":
                sig = sig[:-1] + bytes([sig[-1] ^ 0x01])

            sigs.append(SignatureEnvelope(alg=alg, kid=kid, sig_b64=b64e(sig)))

        if config.mode in ("pqc", "hybrid"):
            sig = pqc_signer.sign(bah_bytes)
            kid = pqc_signer.kid
            alg = pqc_alg

            if config.fault == "unknown_kid":
                kid = "does-not-exist"
            if config.fault == "invalid_sig":
                sig = sig[:-1] + bytes([sig[-1] ^ 0x01])

            sigs.append(SignatureEnvelope(alg=alg, kid=kid, sig_b64=b64e(sig)))

        sign_ms = (time.perf_counter() - t_sign0) * 1000

        msg = PaymentMessage(bah=bah, document=doc, signatures=sigs)

        # simplistic network delay (CB->NSP->GW->RTGS and back)
        if config.network_delay_ms > 0:
            time.sleep(config.network_delay_ms / 1000.0)

        ok, verify_ms = _gateway_verify(msg, keystore=keystore, verify_registry=verify_registry)

        if config.network_delay_ms > 0:
            time.sleep(config.network_delay_ms / 1000.0)

        total_ms = (time.perf_counter() - t0) * 1000
        size_b = len(_serialize_message(msg))

        return sign_ms, verify_ms, total_ms, size_b, ok

    # Run with threads and aggregate safely
    from concurrent.futures import ThreadPoolExecutor

    wall0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=config.concurrency) as ex:
        rows = list(ex.map(process_one, range(config.n)))
    wall_s = time.perf_counter() - wall0

    sign_times_ms: List[float] = [r[0] for r in rows]
    verify_times_ms: List[float] = [r[1] for r in rows]
    total_times_ms: List[float] = [r[2] for r in rows]
    sizes_bytes: List[int] = [r[3] for r in rows]
    accepted = sum(1 for r in rows if r[4])
    rejected = config.n - accepted

    # Build result object
    from .stats import summary_stats_ms, summary_stats_bytes

    out = {
        "meta": {
            "timestamp": _now_iso(),
            "mode": config.mode,
            "n": config.n,
            "concurrency": config.concurrency,
            "pqc_backend": config.pqc_backend,
            "oqs_alg": config.oqs_alg if config.pqc_backend == "oqs" else None,
            "mock_level": config.mock_level if config.pqc_backend == "mock" else None,
            "fault": config.fault,
        },
        "summary": {
            "accepted": accepted,
            "rejected": rejected,
            "wall_time_s": wall_s,
            "throughput_msg_per_s": float(config.n / wall_s) if wall_s > 0 else float("inf"),
            "signing": summary_stats_ms(sign_times_ms),
            "verification": summary_stats_ms(verify_times_ms),
            "end_to_end": summary_stats_ms(total_times_ms),
            "message_size": summary_stats_bytes(sizes_bytes),
        },
        "raw": {
            "sign_times_ms": sign_times_ms,
            "verify_times_ms": verify_times_ms,
            "total_times_ms": total_times_ms,
            "sizes_bytes": sizes_bytes,
        },
    }
    return out
