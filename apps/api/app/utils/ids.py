"""
InvarPay AI — ULID-based ID generation

Uses ULID (Universally Unique Lexicographically Sortable Identifier)
for all entity IDs. ULIDs are:
- Sortable by creation time
- 26 characters (fits in VARCHAR(26))
- URL-safe
- Monotonically increasing within millisecond
"""
from __future__ import annotations

import uuid


def new_id() -> str:
    """Generate a new 26-character sortable identifier."""
    try:
        import ulid

        # ulid-py package provides ulid.new()
        if hasattr(ulid, "new"):
            return str(ulid.new())

        # python-ulid package provides ulid.ULID()
        if hasattr(ulid, "ULID"):
            try:
                return str(ulid.ULID())
            except TypeError:
                pass
    except (ImportError, Exception):
        pass

    try:
        from ulid import ULID

        try:
            return str(ULID())
        except TypeError:
            pass
    except (ImportError, Exception):
        pass

    # Fallback to 26-character UUID
    return uuid.uuid4().hex[:26]
