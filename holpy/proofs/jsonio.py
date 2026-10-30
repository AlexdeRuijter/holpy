from __future__ import annotations

import json
import os

__all__ = ["dumps_theory", "write_theory"]


def dumps_theory(data: dict) -> str:
    """Return a canonical JSON string for a theory dictionary.

    Keys are sorted at every level. Separators are `", "` and `": "`.
    ``ensure_ascii=False`` keeps non-ASCII characters. Each item of the
    top-level ``content`` list and each entry of a proof's ``proof`` or
    ``steps`` list appears on its own line. The output ends with exactly
    one ``\\n`` and uses ``\\n`` on every platform.
    """
    return _serialize(data) + "\n"


def write_theory(path: str | os.PathLike, data: dict) -> None:
    """Write *data* as canonical theory JSON to *path* (UTF-8, ``newline="\\n"``)."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(dumps_theory(data))


def _is_primitive(obj: object) -> bool:
    return isinstance(obj, (str, int, float, bool, type(None)))


def _serialize(obj: object, indent: int = 0) -> str:
    spaces = " " * indent
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        items: list[str] = []
        for k in sorted(obj.keys()):
            v_str = _serialize(obj[k], indent + 2)
            items.append(f"{json.dumps(k, ensure_ascii=False)}: {v_str}")
        inner = ", ".join(items)
        return "{" + inner + "}"
    elif isinstance(obj, list):
        if not obj:
            return "[]"
        if all(_is_primitive(e) for e in obj):
            inner = ", ".join(json.dumps(e, ensure_ascii=False) for e in obj)
            return "[" + inner + "]"
        inner_items: list[str] = []
        for e in obj:
            inner_items.append(" " * (indent + 2) + _serialize(e, indent + 2))
        lines: list[str] = []
        for i, item_str in enumerate(inner_items):
            stripped = item_str.rstrip()
            if i < len(inner_items) - 1:
                lines.append(stripped + ",")
            else:
                lines.append(stripped)
        return "[\n" + "\n".join(lines) + "\n" + spaces + "]"
    else:
        return json.dumps(obj, ensure_ascii=False)
