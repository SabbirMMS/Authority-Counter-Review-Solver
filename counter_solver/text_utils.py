from __future__ import annotations

import re


BLOCK_OPENERS = ("{", "[", "(")
BLOCK_CLOSERS = ("}", "]", ")")


def code_mask(line: str, in_block_comment: bool) -> tuple[list[bool], bool]:
    mask = [False] * len(line)
    quote: str | None = None
    escaped = False
    idx = 0

    while idx < len(line):
        ch = line[idx]

        if in_block_comment:
            if idx + 1 < len(line) and ch == "*" and line[idx + 1] == "/":
                idx += 2
                in_block_comment = False
                continue
            idx += 1
            continue

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

        if ch in {'"', "'", "`"}:
            quote = ch
            idx += 1
            continue

        if ch == "#":
            break

        if idx + 1 < len(line) and ch == "/" and line[idx + 1] == "/":
            break

        if idx + 1 < len(line) and ch == "/" and line[idx + 1] == "*":
            in_block_comment = True
            idx += 2
            continue

        mask[idx] = True
        idx += 1

    return mask, in_block_comment


def transform_code_segments(
    line: str,
    in_block_comment: bool,
    transform: callable,
) -> tuple[str, bool]:
    mask, new_state = code_mask(line, in_block_comment)
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
