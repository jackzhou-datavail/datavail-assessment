"""SQL text helpers shared by the runners."""

from __future__ import annotations

import re

def split_sql(ddl: str) -> list[str]:
    """Split a DDL script on statement boundaries, quote-aware.

    A naive split on ';' breaks on semicolons inside COMMENT strings,
    which the result schema uses throughout. Line comments are stripped
    in the same pass, because they too can contain semicolons.
    """
    statements, buf, in_str = [], [], False
    i, n = 0, len(ddl)
    while i < n:
        ch = ddl[i]
        if in_str:
            # '' inside a string is an escaped quote, not a terminator.
            if ch == "'" and i + 1 < n and ddl[i + 1] == "'":
                buf.append("''")
                i += 2
                continue
            if ch == "'":
                in_str = False
            buf.append(ch)
        elif ch == "'":
            in_str = True
            buf.append(ch)
        elif ch == "-" and i + 1 < n and ddl[i + 1] == "-":
            # Skip to end of line, preserving the newline.
            j = ddl.find("\n", i)
            i = n if j == -1 else j
            continue
        elif ch == ";":
            statements.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    statements.append("".join(buf))

    return [s.strip() for s in statements if s.strip()]


def lit(v) -> str:
    """Render a Python value as a SQL literal for INSERT ... VALUES."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (list, tuple)):
        return "array(" + ", ".join(lit(x) for x in v) + ")" if v else "array()"
    return "'" + str(v).replace("\\", "\\\\").replace("'", "''") + "'"
