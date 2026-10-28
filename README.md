# 09 · paginate

Cursor pagination that stays correct while rows are inserted mid-scroll.

## Run

```bash
from paginate.cursor import Edge, paginate
```

## Test

```bash
pytest projects/09-cursor-pagination -q
```

## What it demonstrates

- Opaque base64 cursors over a composite sort key
- Binary search to find the cursor position - O(log n) instead of scanning
- A test that proves new rows inserted before the cursor do not shift the window
- Malformed or tampered cursors raise `CursorError`, never a 500

## Repository
- GitHub: https://github.com/{owner}/cursor-pagination
- Python 3.11+ · tests: `pytest` · runtime dependencies: none (standard library only)
