from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from pydantic import BaseModel, Field, ConfigDict


class BusinessApplicationHeader(BaseModel):
    """Minimal ISO 20022-like Business Application Header (BAH).

    In Project Leap Phase 2, the BAH signature (RSA in the current system) was replaced
    with a post-quantum signature to keep the message flow intact while swapping the
    cryptographic primitive.
    """

    model_config = ConfigDict(extra="forbid")

    msg_id: str = Field(..., description="Unique message id (UUID recommended).")
    from_party: str = Field(..., description="Sender identifier (eg BIC).")
    to_party: str = Field(..., description="Receiver identifier (eg BIC).")
    msg_def_id: str = Field("head.001", description="Message definition id (simplified).")
    creation_dt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Creation datetime in ISO format.",
    )


class LiquidityTransfer(BaseModel):
    """A simplified liquidity transfer payload.

    Real systems use detailed ISO 20022 messages (eg camt.050/camt.025 etc).
    Here we keep only the fields needed to simulate performance & integrity checks.
    """

    model_config = ConfigDict(extra="forbid")

    amount: float = Field(..., gt=0, description="Transfer amount.")
    currency: str = Field("EUR", min_length=3, max_length=3)
    sender_account: str = Field(..., description="Sender account id (toy).")
    receiver_account: str = Field(..., description="Receiver account id (toy).")
    reference: str = Field(..., description="Business reference / reason.")
    requested_dt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Requested datetime in ISO format.",
    )


class SignatureEnvelope(BaseModel):
    """A signature container so we can support RSA / PQC / hybrid."""

    model_config = ConfigDict(extra="forbid")

    alg: str = Field(..., description="Algorithm identifier.")
    kid: str = Field(..., description="Key identifier, used to fetch verification key.")
    sig_b64: str = Field(..., description="Signature bytes, base64-encoded.")


class PaymentMessage(BaseModel):
    """A signed payment message: BAH + payload + one-or-more signatures."""

    model_config = ConfigDict(extra="forbid")

    bah: BusinessApplicationHeader
    document: LiquidityTransfer
    signatures: List[SignatureEnvelope] = Field(default_factory=list)

