from __future__ import annotations

import base64

import pytest

from paginate.cursor import CursorError, Edge, decode_cursor, encode_cursor, paginate


def edges(start: int, count: int) -> list[Edge]:
    return [Edge((i,), f"row-{i}") for i in range(start, start + count)]


# ----------------------------------------------------------------- cursor
def test_cursor_roundtrip():
    cursor = encode_cursor([42, "abc"])
    assert decode_cursor(cursor) == [42, "abc"]


def test_cursor_is_url_safe():
    cursor = encode_cursor([1, "a/b+c="])
    assert "/" not in cursor and "+" not in cursor and "=" not in cursor


def test_cursor_handles_unicode():
    assert decode_cursor(encode_cursor(["مكتبة"])) == ["مكتبة"]


@pytest.mark.parametrize("bad", ["!!!", "YWJj", base64.urlsafe_b64encode(b'{"a": 1}').decode()])
def test_malformed_cursors_raise(bad):
    with pytest.raises(CursorError):
        decode_cursor(bad)


def test_cursor_length_is_validated():
    with pytest.raises(CursorError):
        decode_cursor(encode_cursor([1]), expected_length=2)


# ------------------------------------------------------------------- page
def test_first_page_reports_more():
    page = paginate(edges(0, 10), limit=3)
    assert [i for i in page.items] == ["row-0", "row-1", "row-2"]
    assert page.has_more and page.next_cursor
    assert page.total_returned == 3


def test_walking_pages_yields_every_row_exactly_once():
    rows = edges(0, 10)
    seen, cursor, pages = [], None, 0
    while True:
        page = paginate(rows, limit=3, cursor=cursor)
        seen.extend(page.items)
        pages += 1
        cursor = page.next_cursor
        if not page.has_more:
            break
    assert seen == [f"row-{i}" for i in range(10)]
    assert pages == 4


def test_last_page_has_no_cursor():
    page = paginate(edges(0, 5), limit=10)
    assert page.next_cursor is None and page.has_more is False


def test_exact_multiple_boundary():
    """6 rows, limit 3: the third page is exactly full and must not be repeated."""
    pages, cursor = [], None
    while True:
        page = paginate(edges(0, 6), limit=3, cursor=cursor)
        pages.append(page.items)
        cursor = page.next_cursor
        if not page.has_more:
            break
    assert pages == [["row-0", "row-1", "row-2"], ["row-3", "row-4", "row-5"]]


def test_descending_order():
    page = paginate(edges(0, 5), limit=2, descending=True)
    assert page.items == ["row-4", "row-3"]


def test_cursor_survives_insertions_before_the_cursor():
    """The headline benefit over OFFSET: newly inserted rows don't shift the window."""
    rows = edges(0, 6)
    first = paginate(rows, limit=2)
    rows_after_insert = edges(-2, 2) + rows  # two new rows sort before the cursor
    second = paginate(rows_after_insert, limit=2, cursor=first.next_cursor)
    assert second.items == ["row-2", "row-3"]


def test_composite_keys():
    rows = [Edge((1, "a"), "x"), Edge((1, "b"), "y"), Edge((2, "a"), "z")]
    page = paginate(rows, limit=2)
    second = paginate(rows, limit=2, cursor=page.next_cursor)
    assert page.items == ["x", "y"]
    assert second.items == ["z"]


def test_invalid_limit():
    with pytest.raises(ValueError):
        paginate([], limit=0)


def test_empty_input():
    page = paginate([], limit=5)
    assert page.items == [] and page.next_cursor is None and page.has_more is False
