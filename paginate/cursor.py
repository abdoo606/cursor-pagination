"""Base64 cursors over a stable sort key.

Offset pagination breaks when rows are inserted or deleted mid-scroll; a cursor
built on the last seen sort key does not.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Generic, Iterable, Sequence, TypeVar

T = TypeVar("T")


class CursorError(ValueError):
    """Raised when a cursor is malformed or tampered with."""


def encode_cursor(values: Sequence[Any]) -> str:
    raw = json.dumps(list(values), separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str, *, expected_length: int | None = None) -> list[Any]:
    padding = "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(cursor + padding)
        values = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise CursorError("cursor is not valid base64-encoded JSON") from exc
    if not isinstance(values, list):
        raise CursorError("cursor payload must be a list")
    if expected_length is not None and len(values) != expected_length:
        raise CursorError(f"cursor must contain {expected_length} values")
    return values


@dataclass(slots=True, frozen=True)
class Page(Generic[T]):
    items: list[T]
    next_cursor: str | None
    has_more: bool
    total_returned: int


@dataclass(slots=True, frozen=True)
class Edge:
    """Wraps a row so the paginator knows how to sort it."""

    key: tuple[Any, ...]
    item: Any


def paginate(
    rows: Iterable[Edge],
    *,
    limit: int = 20,
    cursor: str | None = None,
    descending: bool = False,
) -> Page[Any]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    key_length = 1
    rows = list(rows)
    if rows:
        key_length = len(rows[0].key)
    ordered = sorted(rows, key=lambda e: e.key, reverse=descending)

    start = 0
    if cursor:
        values = decode_cursor(cursor, expected_length=key_length)
        start = _position_after(ordered, tuple(values), descending)

    window = ordered[start : start + limit + 1]
    has_more = len(window) > limit
    page_items = window[:limit]
    next_cursor = encode_cursor(page_items[-1].key) if has_more and page_items else None
    return Page(
        items=[e.item for e in page_items],
        next_cursor=next_cursor,
        has_more=has_more,
        total_returned=len(page_items),
    )


def _position_after(ordered: list[Edge], key: tuple[Any, ...], descending: bool) -> int:
    """Binary search for the first index strictly after `key` in the sort order."""
    lo, hi = 0, len(ordered)
    while lo < hi:
        mid = (lo + hi) // 2
        value = ordered[mid].key
        if (value > key) if not descending else (value < key):
            hi = mid
        else:
            lo = mid + 1
    return lo
