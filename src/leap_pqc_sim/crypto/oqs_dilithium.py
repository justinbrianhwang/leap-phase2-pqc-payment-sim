from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .base import Signer


@dataclass
class OQSDilithiumSigner(Signer):
    """PQC signer backed by liboqs-python (if installed).

    Requires:
      - liboqs (C library)
      - liboqs-python (Python bindings), importable as `oqs`

    Because liboqs-python is sometimes installed from source and its API can differ
    slightly across versions, this wrapper tries a few call patterns.
    """

    kid: str
    oqs_alg: str = "Dilithium3"  # Phase 2 used a Dilithium variant (security category 3)
    _public_key: bytes = b""
    _secret_key: Optional[bytes] = None
    _sig_obj: object | None = None

    @property
    def alg(self) -> str:  # type: ignore[override]
        return f"OQS-{self.oqs_alg}"

    @classmethod
    def generate(cls, *, kid: str, oqs_alg: str = "Dilithium3") -> "OQSDilithiumSigner":
        try:
            import oqs  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "Cannot import `oqs`. Install liboqs-python (open-quantum-safe/liboqs-python) "
                "and make sure liboqs is available on your system."
            ) from e

        obj = cls(kid=kid, oqs_alg=oqs_alg)

        sig_obj = oqs.Signature(oqs_alg)  # type: ignore[attr-defined]
        obj._sig_obj = sig_obj

        # generate_keypair() patterns:
        # - returns public_key and stores secret key inside the object
        # - or returns (public_key, secret_key)
        kp = sig_obj.generate_keypair()  # type: ignore[attr-defined]
        if isinstance(kp, tuple) and len(kp) == 2:
            obj._public_key, obj._secret_key = kp  # type: ignore[assignment]
        else:
            obj._public_key = kp  # type: ignore[assignment]

        return obj

    def public_key_bytes(self) -> bytes:
        return self._public_key

    def sign(self, msg: bytes) -> bytes:
        if self._sig_obj is None:
            raise RuntimeError("Signer not initialised; call generate().")

        # sign() patterns:
        # - sign(message) using internal secret key
        # - or sign(message, secret_key)
        try:
            return self._sig_obj.sign(msg)  # type: ignore[attr-defined]
        except TypeError:
            if self._secret_key is None:
                raise
            return self._sig_obj.sign(msg, self._secret_key)  # type: ignore[attr-defined]

    @staticmethod
    def verify(msg: bytes, sig: bytes, public_key: bytes) -> bool:
        try:
            import oqs  # type: ignore
        except Exception:
            return False

        # We need the algorithm id. We infer it from the public key length? Not safe.
        # Therefore, this verifier is designed to be called through the simulation's
        # algorithm registry with the right `oqs_alg`.
        raise RuntimeError(
            "OQSDilithiumSigner.verify() needs an explicit algorithm name. "
            "Use `leap_pqc_sim.crypto.oqs_verify(alg, msg, sig, public_key)` instead."
        )


def oqs_verify(oqs_alg: str, msg: bytes, sig: bytes, public_key: bytes) -> bool:
    """Verify an OQS signature with an explicit algorithm name."""
    try:
        import oqs  # type: ignore
    except Exception:
        return False

    try:
        verifier = oqs.Signature(oqs_alg)  # type: ignore[attr-defined]
        ok = verifier.verify(msg, sig, public_key)  # type: ignore[attr-defined]
        return bool(ok)
    except Exception:
        return False
