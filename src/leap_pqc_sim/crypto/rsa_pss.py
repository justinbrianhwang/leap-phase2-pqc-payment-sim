from __future__ import annotations

from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .base import Signer


@dataclass
class RSAPSSSigner(Signer):
    """Traditional baseline signer: RSA-PSS with SHA-256.

    Note: Project Leap Phase 2 describes the BAH digital signature using RSA in today's system,
    then replacing it with a PQC signature for the experiment.
    """

    kid: str
    private_key: rsa.RSAPrivateKey

    alg: str = "RSA-PSS-SHA256"

    @classmethod
    def generate(cls, *, kid: str, key_size: int = 2048) -> "RSAPSSSigner":
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        return cls(kid=kid, private_key=private_key)

    def public_key_bytes(self) -> bytes:
        pub = self.private_key.public_key()
        return pub.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def sign(self, msg: bytes) -> bytes:
        return self.private_key.sign(
            msg,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )

    @staticmethod
    def verify(msg: bytes, sig: bytes, public_key: bytes) -> bool:
        try:
            pub = serialization.load_pem_public_key(public_key)
            assert hasattr(pub, "verify")
            pub.verify(
                sig,
                msg,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except Exception:
            return False
