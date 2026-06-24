"""snake_case -> camelCase serialization for the API boundary.

The agent layer (``/chat``, ``/propose``) and the persisted proposal payloads are
snake_case; the frontend contract (README §8B) is camelCase. These helpers do the
deep key conversion in one place so responses stay consistent.
"""

from __future__ import annotations

import re
from typing import Any

_SNAKE_RE = re.compile(r"_([a-z0-9])")


def to_camel(key: str) -> str:
    return _SNAKE_RE.sub(lambda m: m.group(1).upper(), key)


def camelize(value: Any) -> Any:
    """Recursively convert all dict keys from snake_case to camelCase."""
    if isinstance(value, list):
        return [camelize(v) for v in value]
    if isinstance(value, dict):
        return {to_camel(k): camelize(v) for k, v in value.items()}
    return value
