from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from .base import Signer


_DILITHIUM_SIZES = {
    # Commonly cited (pre-standardisation naming) sizes in bytes.
    # These are *approximate targets* for this educational simulator.
    #
    # Dilithium2: sig≈2420, pk≈1312
    # Dilithium3: sig≈3293, pk≈1952
    # Dilithium5: sig≈4595, pk≈2592
    2: {"sig": 2420, "pk": 1312, "verify_work": 6000, "sign_work": 3000},
    3: {"sig": 3293, "pk": 1952, "verify_work": 8000, "sign_work": 4000},
    5: {"sig": 4595, "pk": 2592, "verify_work": 12000, "sign_work": 6000},
}


def _expand(seed: bytes, length: int) -> bytes:
    """Deterministically expand `seed` into `length` bytes."""
    out = bytearray()
    counter = 0
    while len(out) < length:
        counter_bytes = counter.to_bytes(4, "big")
        out.extend(hashlib.sha3_256(seed + counter_bytes).digest())
        counter += 1
    return bytes(out[:length])


def _burn_cpu(tag: bytes, iters: int) -> None:
    """Spend CPU time deterministically (no sleep)."""
    x = tag
    for _ in range(max(0, iters)):
        x = hashlib.sha3_256(x).digest()
    # prevent Python from optimizing away
    if x[0] == 257:  # impossible
        raise RuntimeError("unreachable")


@dataclass
class MockDilithiumSigner(Signer):
    """Portable mock PQC signer (Dilithium-like).

    Internally uses Ed25519 for real public-key semantics, then:

    - pads public keys to Dilithium-like sizes
    - pads signatures to Dilithium-like sizes
    - burns CPU cycles to emulate higher signing/verification costs

    This is NOT Dilithium. It's a teaching/benchmarking scaffold.
    """

    kid: str
    level: Literal[2, 3, 5] = 3
    _sk: ed25519.Ed25519PrivateKey | None = None

    @property
    def alg(self) -> str:  # type: ignore[override]
        return f"MOCK-DILITHIUM{self.level}"

    @classmethod
    def generate(cls, *, kid: str, level: Literal[2, 3, 5] = 3) -> "MockDilithiumSigner":
        obj = cls(kid=kid, level=level)
        obj._sk = ed25519.Ed25519PrivateKey.generate()
        return obj

    def public_key_bytes(self) -> bytes:
        if self._sk is None:
            raise RuntimeError("Signer not initialised; call generate().")
        pk_raw = self._sk.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        pk_target = _DILITHIUM_SIZES[int(self.level)]["pk"]
        if pk_target <= len(pk_raw):
            return pk_raw
        pad = _expand(pk_raw, pk_target - len(pk_raw))
        return pk_raw + pad

    def sign(self, msg: bytes) -> bytes:
        if self._sk is None:
            raise RuntimeError("Signer not initialised; call generate().")
        _burn_cpu(b"sign" + msg[:32], _DILITHIUM_SIZES[int(self.level)]["sign_work"])
        sig_raw = self._sk.sign(msg)  # 64 bytes
        sig_target = _DILITHIUM_SIZES[int(self.level)]["sig"]
        if sig_target <= len(sig_raw):
            return sig_raw
        pad = _expand(sig_raw, sig_target - len(sig_raw))
        return sig_raw + pad

    @staticmethod
    def verify(msg: bytes, sig: bytes, public_key: bytes) -> bool:
        try:
            # Infer "level" from public key length (best-effort).
            level = {1312: 2, 1952: 3, 2592: 5}.get(len(public_key), 3)
            _burn_cpu(b"verify" + msg[:32], _DILITHIUM_SIZES[level]["verify_work"])

            pk_raw = public_key[:32]  # Ed25519 pk (in this mock)
            pub = ed25519.Ed25519PublicKey.from_public_bytes(pk_raw)
            pub.verify(sig[:64], msg)  # first 64 bytes are Ed25519 signature
            return True
        except Exception:
            return False
