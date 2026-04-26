from __future__ import annotations

import re


BLOCK_OPENERS = ("{", "[", "(")
BLOCK_CLOSERS = ("}", "]", ")")


def code_mask(line: str, state: str | None = None, language: str | None = None) -> tuple[list[bool], str | None]:
    """
    Returns a mask (True for code, False for strings/comments) and the end state.
    State can be:
        None: Normal code
        '/*': Inside block comment
        '\"\"\"': Inside triple double quotes
        \"'''\": Inside triple single quotes
    """
    mask = [False] * len(line)
    quote: str | None = None
    escaped = False
    idx = 0

    current_state = state

    while idx < len(line):
        ch = line[idx]

        # Handle existing multi-line states
        if current_state == "/*":
            if idx + 1 < len(line) and ch == "*" and line[idx + 1] == "/":
                idx += 2
                current_state = None
                continue
            idx += 1
            continue
        elif current_state == '"""':
            if not escaped and idx + 2 < len(line) and line[idx:idx + 3] == '"""':
                idx += 3
                current_state = None
                continue
            if ch == "\\":
                escaped = not escaped
            else:
                escaped = False
            idx += 1
            continue
        elif current_state == "'''":
            if not escaped and idx + 2 < len(line) and line[idx:idx + 3] == "'''":
                idx += 3
                current_state = None
                continue
            if ch == "\\":
                escaped = not escaped
            else:
                escaped = False
            idx += 1
            continue

        # Handle string literals (single line)
        if quote is not None:
            if escaped:
                escaped = False
                idx += 1
                continue
            if ch == "\\":
                escaped = True
                idx += 1
                continue
            if ch == quote:
                quote = None
            idx += 1
            continue

        # Detect new states
        if ch in {'"', "'"}:
            # Triple quotes check
            if idx + 2 < len(line) and line[idx:idx + 3] == ch * 3:
                current_state = ch * 3
                idx += 3
                continue
            quote = ch
            idx += 1
            continue
        if ch == "`":
            quote = ch
            idx += 1
            continue

        # Comments
        if ch == "#":
            break

        # In Python '//' is floor division, not a comment.
        if language != "python":
            if idx + 1 < len(line) and ch == "/" and line[idx + 1] == "/":
                break

        if idx + 1 < len(line) and ch == "/" and line[idx + 1] == "*":
            current_state = "/*"
            idx += 2
            continue

        mask[idx] = True
        idx += 1

    return mask, current_state


def transform_code_segments(
    line: str,
    state: str | None,
    transform: callable,
    language: str | None = None,
) -> tuple[str, str | None]:
    mask, new_state = code_mask(line, state, language)
    if not line:
        return line, new_state

    chunks: list[str] = []
    idx = 0
    while idx < len(line):
        start = idx
        is_code = mask[idx]
        while idx < len(line) and mask[idx] == is_code:
            idx += 1
        segment = line[start:idx]
        chunks.append(transform(segment) if is_code else segment)
    return "".join(chunks), new_state


def next_non_space(line: str, start: int) -> int | None:
    for idx in range(start, len(line)):
        if line[idx] not in {" ", "\t"}:
            return idx
    return None


def prev_non_space(line: str, start: int) -> int | None:
    for idx in range(start, -1, -1):
        if line[idx] not in {" ", "\t"}:
            return idx
    return None


def detect_newline(content: str) -> str:
    if "\r\n" in content:
        return "\r\n"
    return "\n"


def had_trailing_newline(content: str) -> bool:
    return content.endswith("\n") or content.endswith("\r\n")


def join_lines(lines: list[str], newline: str, trailing_newline: bool) -> str:
    text = newline.join(lines)
    if trailing_newline and lines:
        return f"{text}{newline}"
    return text


def is_pascal_case(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][A-Za-z0-9]*", value))


def is_snake_case(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z0-9_]*", value))
