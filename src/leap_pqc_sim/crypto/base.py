from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Tuple


def b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def b64d(data_b64: str) -> bytes:
    return base64.b64decode(data_b64.encode("ascii"))


class KeyNotFoundError(KeyError):
    pass


class AlgorithmMismatchError(ValueError):
    pass


@dataclass(frozen=True)
class PublicKeyRecord:
    alg: str
    public_key: bytes


class KeyStore:
    """In-memory public key store.

    Real payment systems have certificate chains, revocation, static data, HSM integration, etc.
    Here we only model: `kid -> (alg, public_key_bytes)`.
    """

    def __init__(self) -> None:
        self._store: Dict[str, PublicKeyRecord] = {}

    def register(self, *, kid: str, alg: str, public_key: bytes) -> None:
        self._store[kid] = PublicKeyRecord(alg=alg, public_key=public_key)

    def get(self, kid: str) -> PublicKeyRecord:
        if kid not in self._store:
            raise KeyNotFoundError(kid)
        return self._store[kid]


class Signer(ABC):
    """Abstract signature scheme wrapper."""

    alg: str
    kid: str

    @abstractmethod
    def public_key_bytes(self) -> bytes:
        """Return a transportable representation of the public key."""
        raise NotImplementedError

    @abstractmethod
    def sign(self, msg: bytes) -> bytes:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def verify(msg: bytes, sig: bytes, public_key: bytes) -> bool:
        raise NotImplementedError


