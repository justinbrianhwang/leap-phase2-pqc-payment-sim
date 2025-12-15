from __future__ import annotations

import json
from typing import Any, Mapping


def canonical_json_bytes(obj: Any) -> bytes:
    """Serialize an object into canonical JSON bytes for signing.

    We use:
    - sort_keys=True
    - separators=(',', ':')  (no whitespace)
    - ensure_ascii=False
    """

    # Pydantic models support `model_dump()`.
    if hasattr(obj, "model_dump"):
        obj = obj.model_dump(mode="json")  # type: ignore[attr-defined]

    if isinstance(obj, Mapping):
        payload = obj
    else:
        payload = obj  # json.dumps can handle dict/list/str/int/float etc.

    s = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return s.encode("utf-8")
