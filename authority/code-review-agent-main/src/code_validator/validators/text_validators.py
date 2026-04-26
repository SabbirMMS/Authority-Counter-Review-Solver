from __future__ import annotations

import re

from code_validator.github.models import Violation
from code_validator.rules.models import Rule
from code_validator.validators.base_validator import BaseRuleValidator


class LineLengthValidator(BaseRuleValidator):
    def supports(self, rule_type: str) -> bool:
        return rule_type == "max_line_length"

    def validate(self, path: str, content: str, rule: Rule) -> list[Violation]:
        if rule.value is None:
            return []
        limit = int(rule.value)
        violations: list[Violation] = []
        for idx, line in enumerate(content.splitlines(), start=1):
            if len(line) > limit:
                violations.append(
                    Violation(
                        rule_id=rule.rule_id,
                        path=path,
                        message=f"Line {idx} exceeds {limit} characters.",
                        line_number=idx,
                    )
                )
        return violations


class TrailingWhitespaceValidator(BaseRuleValidator):
    def supports(self, rule_type: str) -> bool:
        return rule_type == "no_trailing_whitespace"

    def validate(self, path: str, content: str, rule: Rule) -> list[Violation]:
        violations: list[Violation] = []
        for idx, line in enumerate(content.splitlines(), start=1):
            if line.rstrip(" \t") != line:
                violations.append(
                    Violation(
                        rule_id=rule.rule_id,
                        path=path,
                        message=f"Line {idx} has trailing whitespace.",
                        line_number=idx,
                    )
                )
        return violations


class RegexRuleValidator(BaseRuleValidator):
    def supports(self, rule_type: str) -> bool:
        return rule_type in {"forbid_regex", "require_regex"}

    def validate(self, path: str, content: str, rule: Rule) -> list[Violation]:
        if not rule.pattern:
            return []

        flags = 0
        if "i" in rule.flags.lower():
            flags |= re.IGNORECASE
        if "m" in rule.flags.lower():
            flags |= re.MULTILINE

        expr = re.compile(rule.pattern, flags=flags)

        if rule.rule_type == "forbid_regex":
            match = expr.search(content)
            if not match:
                return []
            line_number = content.count("\n", 0, match.start()) + 1
            return [
                Violation(
                    rule_id=rule.rule_id,
                    path=path,
                    message=f"Forbidden pattern matched: {rule.pattern}",
                    line_number=line_number,
                )
            ]

        if rule.rule_type == "require_regex" and not expr.search(content):
            return [
                Violation(
                    rule_id=rule.rule_id,
                    path=path,
                    message=f"Required pattern not found: {rule.pattern}",
                )
            ]

        return []


class InnerDelimiterSpacingValidator(BaseRuleValidator):
    _pairs = {
        "(": ")",
        "[": "]",
        "{": "}",
    }

    def supports(self, rule_type: str) -> bool:
        return rule_type == "inner_delimiter_spacing"

    def validate(self, path: str, content: str, rule: Rule) -> list[Violation]:
        raw_delimiters = rule.value if isinstance(rule.value, list) else ["()", "[]", "{}"]
        enabled_openers = {
            item[0]
            for item in raw_delimiters
            if isinstance(item, str) and len(item) == 2 and item[0] in self._pairs and self._pairs[item[0]] == item[1]
        }
        if not enabled_openers:
            enabled_openers = {"(", "[", "{"}

        violations: list[Violation] = []
        in_block_comment = False
        for line_number, line in enumerate(content.splitlines(), start=1):
            code_mask, in_block_comment = self._code_mask(line, in_block_comment)
            violations.extend(self._check_opening(path, line, code_mask, line_number, rule.rule_id, enabled_openers))
            violations.extend(self._check_closing(path, line, code_mask, line_number, rule.rule_id, enabled_openers))
        return violations

    def _check_opening(
        self,
        path: str,
        line: str,
        code_mask: list[bool],
        line_number: int,
        rule_id: str,
        enabled_openers: set[str],
    ) -> list[Violation]:
        violations: list[Violation] = []
        for idx, ch in enumerate(line):
            if not code_mask[idx]:
                continue
            if ch not in enabled_openers:
                continue

            close_ch = self._pairs[ch]
            next_non_space_index = self._next_non_space(line, idx + 1)
            if next_non_space_index is None:
                continue
            if line[next_non_space_index] == close_ch:
                continue

            if idx + 1 >= len(line) or line[idx + 1] != " ":
                violations.append(
                    Violation(
                        rule_id=rule_id,
                        path=path,
                        line_number=line_number,
                        message=f"Missing single space right after '{ch}'.",
                    )
                )
        return violations

    def _check_closing(
        self,
        path: str,
        line: str,
        code_mask: list[bool],
        line_number: int,
        rule_id: str,
        enabled_openers: set[str],
    ) -> list[Violation]:
        enabled_closers = {self._pairs[ch]: ch for ch in enabled_openers}
        violations: list[Violation] = []
        for idx, ch in enumerate(line):
            if not code_mask[idx]:
                continue
            if ch not in enabled_closers:
                continue

            open_ch = enabled_closers[ch]
            prev_non_space_index = self._prev_non_space(line, idx - 1)
            if prev_non_space_index is None:
                continue
            if line[prev_non_space_index] == open_ch:
                continue

            if idx - 1 < 0 or line[idx - 1] != " ":
                violations.append(
                    Violation(
                        rule_id=rule_id,
                        path=path,
                        line_number=line_number,
                        message=f"Missing single space right before '{ch}'.",
                    )
                )
        return violations

    @staticmethod
    def _next_non_space(line: str, start: int) -> int | None:
        for idx in range(start, len(line)):
            if line[idx] not in {" ", "\t"}:
                return idx
        return None

    @staticmethod
    def _prev_non_space(line: str, start: int) -> int | None:
        for idx in range(start, -1, -1):
            if line[idx] not in {" ", "\t"}:
                return idx
        return None

    @staticmethod
    def _code_mask(line: str, in_block_comment: bool) -> tuple[list[bool], bool]:
        """Return a mask where True means the character is code, not string/comment text."""
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
                    mask[idx] = False
                    escaped = False
                    idx += 1
                    continue
                if ch == "\\":
                    mask[idx] = False
                    escaped = True
                    idx += 1
                    continue
                mask[idx] = False
                if ch == quote:
                    quote = None
                idx += 1
                continue

            if ch in {'"', "'", "`"}:
                quote = ch
                mask[idx] = False
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
