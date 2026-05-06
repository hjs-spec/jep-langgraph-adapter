"""Deterministic canonicalization utilities for replayable JEP events."""

from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


def _normalize(value: Any) -> Any:
    """Convert Python values into deterministic JSON-compatible structures."""

    if dataclasses.is_dataclass(value):
        value = dataclasses.asdict(value)

    if isinstance(value, Mapping):
        return {str(key): _normalize(value[key]) for key in sorted(value, key=lambda item: str(item))}

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize(item) for item in value]

    if isinstance(value, (set, frozenset)):
        return sorted((_normalize(item) for item in value), key=lambda item: canonicalize(item))

    if isinstance(value, (bytes, bytearray)):
        return value.hex()

    return repr(value)


def canonicalize(value: Any) -> str:
    """Return a deterministic JSON representation for hashing and export."""

    return json.dumps(_normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_hash(value: Any) -> str:
    """Return the SHA-256 hash of a canonicalized value."""

    return hashlib.sha256(canonicalize(value).encode("utf-8")).hexdigest()
