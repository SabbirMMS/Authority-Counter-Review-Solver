from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from counter_solver.defaults import DEFAULT_IGNORED_DIRS, LANGUAGE_EXTENSIONS, SAFE_FIXABLE_RULE_TYPES
from counter_solver.models import FileResult, Rule, RuleSet, Violation
from counter_solver.text_utils import (
    BLOCK_CLOSERS,
    BLOCK_OPENERS,
    code_mask,
    detect_newline,
    had_trailing_newline,
    is_pascal_case,
    is_snake_case,
    join_lines,
    next_non_space,
    prev_non_space,
    transform_code_segments,
)


SAFE_REGEX_FIXERS: dict[str, callable] = {}


def infer_language(path: Path) -> str | None:
    return LANGUAGE_EXTENSIONS.get(path.suffix.lower())


def collect_supported_files(project_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in project_root.rglob("*"):
        if path.is_dir():
            continue
        relative = path.relative_to(project_root)
        if any(part in DEFAULT_IGNORED_DIRS for part in relative.parts):
            continue
        if infer_language(path):
            files.append(path)
    return sorted(files)


def plan_fixes(
    project_root: Path,
    files: list[Path],
    ruleset: RuleSet,
    selected_rules_by_path: dict[str, set[str]] | None = None,
) -> list[FileResult]:
    results: list[FileResult] = []
    for path in files:
        language = infer_language(path) or "plain"
        relative_path = path.relative_to(project_root).as_posix()
        rules = ruleset.rules_for_language(language)
        try:
            original_content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            results.append(
                FileResult(
                    path=path,
                    relative_path=relative_path,
                    language=language,
                    original_content="",
                    proposed_content="",
                    read_error="File is not valid UTF-8 text and was skipped.",
                )
            )
            continue

        violations_before = analyze_content(relative_path, path, original_content, language, rules)
        allowed_rule_ids = None
        if selected_rules_by_path is not None:
            allowed_rule_ids = selected_rules_by_path.get(relative_path, set())

        proposed_content, applied_rule_ids, skipped_fix_reasons = apply_safe_fixes(
            relative_path=relative_path,
            path=path,
            content=original_content,
            language=language,
            rules=rules,
            allowed_rule_ids=allowed_rule_ids,
        )
        violations_after = analyze_content(relative_path, path, proposed_content, language, rules)
        results.append(
            FileResult(
                path=path,
                relative_path=relative_path,
                language=language,
                original_content=original_content,
                proposed_content=proposed_content,
                violations_before=violations_before,
                violations_after=violations_after,
                applied_rule_ids=applied_rule_ids,
                skipped_fix_reasons=skipped_fix_reasons,
            )
        )
    return results


def scan_project(
    project_root: Path,
    files: list[Path],
    ruleset: RuleSet,
) -> list[FileResult]:
    return plan_fixes(
        project_root=project_root,
        files=files,
        ruleset=ruleset,
        selected_rules_by_path={path.relative_to(project_root).as_posix(): set() for path in files},
    )


def analyze_content(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rules: list[Rule],
) -> list[Violation]:
    violations: list[Violation] = []
    for rule in rules:
        violations.extend(detect_rule(relative_path, path, content, language, rule))
    return violations


def detect_rule(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> list[Violation]:
    detector = DETECTORS.get(rule.rule_type)
    if not detector:
        return []
    return detector(relative_path, path, content, language, rule)


def apply_safe_fixes(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rules: list[Rule],
    allowed_rule_ids: set[str] | None,
) -> tuple[str, list[str], list[str]]:
    text = content
    applied_rule_ids: list[str] = []
    skipped_fix_reasons: list[str] = []

    for rule in rules:
        fixer = FIXERS.get(rule.rule_type)
        if not fixer:
            if rule.rule_type in {"forbid_regex", "require_regex"} and rule.rule_id not in SAFE_REGEX_FIXERS:
                skipped_fix_reasons.append(f"{rule.rule_id}: no safe autofix available for regex rule.")
            continue

        if allowed_rule_ids is not None and rule.rule_id not in allowed_rule_ids:
            continue

        updated_text, changed, skip_reason = fixer(relative_path, path, text, language, rule)
        if changed:
            applied_rule_ids.append(rule.rule_id)
            text = updated_text
        if skip_reason:
            skipped_fix_reasons.append(f"{rule.rule_id}: {skip_reason}")

    return text, applied_rule_ids, skipped_fix_reasons


def summarize_violations(results: list[FileResult], use_after: bool = False) -> Counter[str]:
    counter: Counter[str] = Counter()
    for item in results:
        violations = item.violations_after if use_after else item.violations_before
        for violation in violations:
            counter[violation.rule_id] += 1
    return counter


def write_changes(results: list[FileResult]) -> int:
    written = 0
    for item in results:
        if item.read_error or not item.changed:
            continue
        item.path.write_text(item.proposed_content, encoding="utf-8")
        written += 1
    return written


def fix_no_trailing_whitespace(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> tuple[str, bool, str | None]:
    newline = detect_newline(content)
    trailing = had_trailing_newline(content)
    lines = content.splitlines()
    updated = [line.rstrip(" \t") for line in lines]
    return join_lines(updated, newline, trailing), updated != lines, None


def fix_no_tabs(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> tuple[str, bool, str | None]:
    newline = detect_newline(content)
    trailing = had_trailing_newline(content)
    changed = False
    updated_lines: list[str] = []
    in_block_comment = False
    for line in content.splitlines():
        updated, in_block_comment = transform_code_segments(
            line,
            in_block_comment,
            lambda chunk: chunk.replace("\t", "    "),
        )
        if updated != line:
            changed = True
        updated_lines.append(updated)
    return join_lines(updated_lines, newline, trailing), changed, None


def fix_max_consecutive_blank_lines(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> tuple[str, bool, str | None]:
    max_blank = int(rule.value or 1)
    newline = detect_newline(content)
    trailing = had_trailing_newline(content)
    updated_lines: list[str] = []
    blank_run = 0
    for line in content.splitlines():
        if line.strip():
            blank_run = 0
            updated_lines.append(line)
            continue
        blank_run += 1
        if blank_run <= max_blank:
            updated_lines.append("")
    changed = updated_lines != content.splitlines()
    return join_lines(updated_lines, newline, trailing), changed, None


def _normalize_comma_segment(segment: str) -> str:
    if not segment:
        return segment

    def replacement(match: re.Match[str]) -> str:
        end = match.end()
        next_char = segment[end:end + 1]
        if not next_char or next_char in ")]},":
            return ","
        return ", "

    segment = re.sub(r"\s*,\s*", replacement, segment)
    return re.sub(r",\s+$", ",", segment)


def fix_comma_spacing(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> tuple[str, bool, str | None]:
    newline = detect_newline(content)
    trailing = had_trailing_newline(content)
    changed = False
    updated_lines: list[str] = []
    in_block_comment = False
    for line in content.splitlines():
        updated, in_block_comment = transform_code_segments(line, in_block_comment, _normalize_comma_segment)
        if updated != line:
            changed = True
        updated_lines.append(updated)
    return join_lines(updated_lines, newline, trailing), changed, None


def _normalize_assignment_segment(segment: str) -> str:
    leading_match = re.match(r"^\s*", segment)
    leading = leading_match.group(0) if leading_match else ""
    body = segment[len(leading):]
    replacements = (
        (r"\s*===\s*", " === "),
        (r"\s*!==\s*", " !== "),
        (r"\s*==\s*", " == "),
        (r"\s*!=\s*", " != "),
        (r"\s*<=\s*", " <= "),
        (r"\s*>=\s*", " >= "),
        (r"(?<![<>=!])\s*=\s*(?![=>])", " = "),
    )
    updated = body
    for pattern, replacement in replacements:
        updated = re.sub(pattern, replacement, updated)
    updated = re.sub(r"(?<=\S) {2,}(?=\S)", " ", updated)
    return f"{leading}{updated}"


def fix_assignment_spacing(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> tuple[str, bool, str | None]:
    newline = detect_newline(content)
    trailing = had_trailing_newline(content)
    changed = False
    updated_lines: list[str] = []
    in_block_comment = False
    for line in content.splitlines():
        updated, in_block_comment = transform_code_segments(line, in_block_comment, _normalize_assignment_segment)
        if updated != line:
            changed = True
        updated_lines.append(updated)
    return join_lines(updated_lines, newline, trailing), changed, None


def _fix_inner_spacing_for_line(line: str, enabled_openers: set[str], in_block_comment: bool) -> tuple[str, bool, bool]:
    changed = False
    updated = line
    start_state = in_block_comment

    mask, end_state = code_mask(updated, start_state)
    idx = 0
    pairs = {"(": ")", "[": "]", "{": "}"}
    while idx < len(updated):
        if idx >= len(mask) or not mask[idx]:
            idx += 1
            continue
        char = updated[idx]
        if char not in enabled_openers:
            idx += 1
            continue
        close_char = pairs[char]
        next_index = next_non_space(updated, idx + 1)
        if next_index is None or updated[next_index] == close_char:
            idx += 1
            continue
        if idx + 1 >= len(updated) or updated[idx + 1] != " ":
            updated = f"{updated[:idx + 1]} {updated[idx + 1:]}"
            changed = True
            mask, _ = code_mask(updated, start_state)
        idx += 1

    mask, _ = code_mask(updated, start_state)
    idx = 0
    closers = {pairs[item]: item for item in enabled_openers}
    while idx < len(updated):
        if idx >= len(mask) or not mask[idx]:
            idx += 1
            continue
        char = updated[idx]
        if char not in closers:
            idx += 1
            continue
        open_char = closers[char]
        prev_index = prev_non_space(updated, idx - 1)
        if prev_index is None or updated[prev_index] == open_char:
            idx += 1
            continue
        if idx - 1 < 0 or updated[idx - 1] != " ":
            updated = f"{updated[:idx]} {updated[idx:]}"
            changed = True
            mask, _ = code_mask(updated, start_state)
            idx += 1
        idx += 1

    return updated, changed, end_state


def fix_inner_delimiter_spacing(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> tuple[str, bool, str | None]:
    raw_delimiters = rule.value if isinstance(rule.value, list) else ["()", "[]", "{}"]
    pairs = {"(": ")", "[": "]", "{": "}"}
    enabled_openers = {
        item[0]
        for item in raw_delimiters
        if isinstance(item, str) and len(item) == 2 and pairs.get(item[0]) == item[1]
    }
    if not enabled_openers:
        enabled_openers = {"(", "[", "{"}

    newline = detect_newline(content)
    trailing = had_trailing_newline(content)
    changed = False
    updated_lines: list[str] = []
    in_block_comment = False
    for line in content.splitlines():
        updated, line_changed, in_block_comment = _fix_inner_spacing_for_line(line, enabled_openers, in_block_comment)
        changed = changed or line_changed
        updated_lines.append(updated)
    return join_lines(updated_lines, newline, trailing), changed, None


def _looks_like_block_opener(stripped: str, language: str) -> bool:
    if not stripped:
        return False
    if stripped.endswith(("{", ":", "[")):
        return True
    if language == "html":
        return bool(re.match(r"<[A-Za-z][^>]*?>$", stripped)) and not stripped.startswith("</") and not stripped.endswith("/>")
    return False


def fix_indent_multiple_of_four(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> tuple[str, bool, str | None]:
    newline = detect_newline(content)
    trailing = had_trailing_newline(content)
    lines = content.splitlines()
    updated_lines: list[str] = []
    changed = False
    previous_indent = 0
    previous_opened_block = False

    for line in lines:
        stripped = line.lstrip(" ")
        if not stripped:
            updated_lines.append("")
            continue

        leading_spaces = len(line) - len(stripped)
        target_indent = leading_spaces
        if leading_spaces % 4 != 0:
            if stripped.startswith(BLOCK_CLOSERS) or stripped.startswith("</"):
                target_indent = max((leading_spaces // 4) * 4, 0)
            elif previous_opened_block and leading_spaces <= previous_indent:
                target_indent = previous_indent + 4
            else:
                remainder = leading_spaces % 4
                target_indent = leading_spaces - remainder if remainder < 2 else leading_spaces + (4 - remainder)

        updated_line = f"{' ' * max(target_indent, 0)}{stripped}"
        if updated_line != line:
            changed = True
        updated_lines.append(updated_line)
        previous_indent = len(updated_line) - len(stripped)
        previous_opened_block = _looks_like_block_opener(stripped.rstrip(), language)

    return join_lines(updated_lines, newline, trailing), changed, None


def _wrap_long_line(line: str, limit: int, in_block_comment: bool) -> tuple[list[str], bool, bool]:
    if len(line) <= limit:
        return [line], False, in_block_comment

    indent = len(line) - len(line.lstrip(" "))
    continuation_indent = " " * (indent + 4)
    remaining = line
    wrapped: list[str] = []
    changed = False
    current_block_state = in_block_comment

    while len(remaining) > limit:
        mask, current_block_state = code_mask(remaining, current_block_state)
        break_at = -1
        for idx in range(min(limit, len(remaining) - 1), max(indent + 8, 0), -1):
            if remaining[idx] != " ":
                continue
            if idx < len(mask) and mask[idx]:
                break_at = idx
                break
        if break_at == -1:
            return [line], False, in_block_comment

        wrapped.append(remaining[:break_at].rstrip())
        remaining = f"{continuation_indent}{remaining[break_at + 1:].lstrip()}"
        changed = True

    wrapped.append(remaining)
    return wrapped, changed, current_block_state


def fix_max_line_length(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> tuple[str, bool, str | None]:
    limit = int(rule.value or 120)
    newline = detect_newline(content)
    trailing = had_trailing_newline(content)
    updated_lines: list[str] = []
    changed = False
    in_block_comment = False
    skipped = False

    for line in content.splitlines():
        wrapped_lines, line_changed, in_block_comment = _wrap_long_line(line, limit, in_block_comment)
        if len(line) > limit and not line_changed:
            skipped = True
        changed = changed or line_changed
        updated_lines.extend(wrapped_lines)

    skip_reason = None
    if skipped:
        skip_reason = "some long lines had no safe break point before the limit"
    return join_lines(updated_lines, newline, trailing), changed, skip_reason


def detect_max_line_length(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> list[Violation]:
    limit = int(rule.value or 120)
    violations: list[Violation] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if len(line) > limit:
            violations.append(
                Violation(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    path=relative_path,
                    message=f"Line {line_number} exceeds {limit} characters.",
                    line_number=line_number,
                    fixable=True,
                )
            )
    return violations


def detect_no_trailing_whitespace(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> list[Violation]:
    violations: list[Violation] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if line.rstrip(" \t") != line:
            violations.append(
                Violation(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    path=relative_path,
                    message=f"Line {line_number} has trailing whitespace.",
                    line_number=line_number,
                    fixable=True,
                )
            )
    return violations


def detect_no_tabs(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> list[Violation]:
    violations: list[Violation] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if "\t" in line:
            violations.append(
                Violation(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    path=relative_path,
                    message=f"Line {line_number} contains tab characters.",
                    line_number=line_number,
                    fixable=True,
                )
            )
    return violations


def detect_max_consecutive_blank_lines(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> list[Violation]:
    max_blank = int(rule.value or 1)
    violations: list[Violation] = []
    blank_run = 0
    for line_number, line in enumerate(content.splitlines(), start=1):
        if line.strip():
            blank_run = 0
            continue
        blank_run += 1
        if blank_run > max_blank:
            violations.append(
                Violation(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    path=relative_path,
                    message=f"Line {line_number} exceeds the allowed blank-line run of {max_blank}.",
                    line_number=line_number,
                    fixable=True,
                )
            )
    return violations


def detect_indent_multiple_of_four(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> list[Violation]:
    violations: list[Violation] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            continue
        stripped = line.lstrip(" ")
        leading_spaces = len(line) - len(stripped)
        if leading_spaces % 4 != 0:
            violations.append(
                Violation(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    path=relative_path,
                    message=f"Line {line_number} indentation is not a multiple of 4 spaces.",
                    line_number=line_number,
                    fixable=True,
                )
            )
    return violations


def detect_forbid_regex(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> list[Violation]:
    if not rule.pattern:
        return []
    flags = 0
    if "i" in rule.flags.lower():
        flags |= re.IGNORECASE
    if "m" in rule.flags.lower():
        flags |= re.MULTILINE

    match = re.search(rule.pattern, content, flags)
    if not match:
        return []
    line_number = content.count("\n", 0, match.start()) + 1
    return [
        Violation(
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            path=relative_path,
            message=f"Forbidden pattern matched: {rule.pattern}",
            line_number=line_number,
            fixable=rule.rule_id in SAFE_REGEX_FIXERS,
        )
    ]


def detect_require_regex(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> list[Violation]:
    if not rule.pattern:
        return []
    flags = 0
    if "i" in rule.flags.lower():
        flags |= re.IGNORECASE
    if "m" in rule.flags.lower():
        flags |= re.MULTILINE

    if re.search(rule.pattern, content, flags):
        return []
    return [
        Violation(
            rule_id=rule.rule_id,
            rule_type=rule.rule_type,
            path=relative_path,
            message=f"Required pattern not found: {rule.pattern}",
            fixable=rule.rule_id in SAFE_REGEX_FIXERS,
        )
    ]


def detect_inner_delimiter_spacing(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> list[Violation]:
    raw_delimiters = rule.value if isinstance(rule.value, list) else ["()", "[]", "{}"]
    pairs = {"(": ")", "[": "]", "{": "}"}
    enabled_openers = {
        item[0]
        for item in raw_delimiters
        if isinstance(item, str) and len(item) == 2 and pairs.get(item[0]) == item[1]
    }
    if not enabled_openers:
        enabled_openers = {"(", "[", "{"}

    violations: list[Violation] = []
    in_block_comment = False
    for line_number, line in enumerate(content.splitlines(), start=1):
        mask, in_block_comment = code_mask(line, in_block_comment)
        for idx, char in enumerate(line):
            if not mask[idx]:
                continue
            if char in enabled_openers:
                close_char = pairs[char]
                next_index = next_non_space(line, idx + 1)
                if next_index is None or line[next_index] == close_char:
                    continue
                if idx + 1 >= len(line) or line[idx + 1] != " ":
                    violations.append(
                        Violation(
                            rule_id=rule.rule_id,
                            rule_type=rule.rule_type,
                            path=relative_path,
                            message=f"Missing single space right after '{char}'.",
                            line_number=line_number,
                            fixable=True,
                        )
                    )
            if char in {pairs[item]: item for item in enabled_openers}:
                open_char = {pairs[item]: item for item in enabled_openers}[char]
                prev_index = prev_non_space(line, idx - 1)
                if prev_index is None or line[prev_index] == open_char:
                    continue
                if idx - 1 < 0 or line[idx - 1] != " ":
                    violations.append(
                        Violation(
                            rule_id=rule.rule_id,
                            rule_type=rule.rule_type,
                            path=relative_path,
                            message=f"Missing single space right before '{char}'.",
                            line_number=line_number,
                            fixable=True,
                        )
                    )
    return violations


def detect_comma_spacing(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> list[Violation]:
    violations: list[Violation] = []
    in_block_comment = False
    for line_number, line in enumerate(content.splitlines(), start=1):
        normalized, in_block_comment = transform_code_segments(line, in_block_comment, _normalize_comma_segment)
        if normalized != line:
            violations.append(
                Violation(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    path=relative_path,
                    message=f"Line {line_number} has inconsistent comma spacing.",
                    line_number=line_number,
                    fixable=True,
                )
            )
    return violations


def detect_assignment_spacing(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> list[Violation]:
    violations: list[Violation] = []
    in_block_comment = False
    for line_number, line in enumerate(content.splitlines(), start=1):
        normalized, in_block_comment = transform_code_segments(line, in_block_comment, _normalize_assignment_segment)
        if normalized != line:
            violations.append(
                Violation(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    path=relative_path,
                    message=f"Line {line_number} has inconsistent operator spacing.",
                    line_number=line_number,
                    fixable=True,
                )
            )
    return violations


def detect_missing_control_braces(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> list[Violation]:
    if language not in {"javascript", "typescript", "php", "dart"}:
        return []
    violations: list[Violation] = []
    control_pattern = re.compile(r"^\s*(if|for|while|else\s+if|elseif)\b")
    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        if stripped.startswith("else") and stripped == "else":
            violations.append(
                Violation(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    path=relative_path,
                    message=f"Line {line_number} should place '{{' on the same line as else.",
                    line_number=line_number,
                    advisory=True,
                )
            )
            continue
        if control_pattern.match(stripped) and "{" not in stripped:
            violations.append(
                Violation(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    path=relative_path,
                    message=f"Line {line_number} appears to use a control block without same-line braces.",
                    line_number=line_number,
                    advisory=True,
                )
            )
    return violations


def detect_no_inline_control(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> list[Violation]:
    violations: list[Violation] = []
    if language in {"javascript", "typescript", "php", "dart"}:
        pattern = re.compile(r"^\s*(if|for|while|else\s+if|elseif)\b.*\)\s+[^{\s].*;")
        for line_number, line in enumerate(content.splitlines(), start=1):
            if pattern.search(line):
                violations.append(
                    Violation(
                        rule_id=rule.rule_id,
                        rule_type=rule.rule_type,
                        path=relative_path,
                        message=f"Line {line_number} contains an inline control statement.",
                        line_number=line_number,
                        advisory=True,
                    )
                )
    elif language == "python":
        pattern = re.compile(r"^\s*(if|for|while)\b.+:\s+\S+")
        for line_number, line in enumerate(content.splitlines(), start=1):
            if pattern.search(line):
                violations.append(
                    Violation(
                        rule_id=rule.rule_id,
                        rule_type=rule.rule_type,
                        path=relative_path,
                        message=f"Line {line_number} contains an inline control statement.",
                        line_number=line_number,
                        advisory=True,
                    )
                )
    return violations


def detect_function_max_lines(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> list[Violation]:
    limit = int(rule.value or 60)
    if language == "python":
        return _detect_python_function_length(relative_path, content, rule, limit)
    if language in {"javascript", "typescript", "php", "dart"}:
        return _detect_brace_function_length(relative_path, content, rule, limit)
    return []


def _detect_python_function_length(relative_path: str, content: str, rule: Rule, limit: int) -> list[Violation]:
    lines = content.splitlines()
    violations: list[Violation] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if not re.match(r"^\s*def\s+[A-Za-z_][A-Za-z0-9_]*\s*\(", line):
            idx += 1
            continue
        start = idx
        indent = len(line) - len(line.lstrip(" "))
        end = idx + 1
        while end < len(lines):
            candidate = lines[end]
            stripped = candidate.strip()
            if stripped and (len(candidate) - len(candidate.lstrip(" "))) <= indent:
                break
            end += 1
        length = max(end - start, 1)
        if length > limit:
            violations.append(
                Violation(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    path=relative_path,
                    message=f"Function starting on line {start + 1} is {length} lines long.",
                    line_number=start + 1,
                    advisory=True,
                )
            )
        idx = end
    return violations


def _detect_brace_function_length(relative_path: str, content: str, rule: Rule, limit: int) -> list[Violation]:
    lines = content.splitlines()
    violations: list[Violation] = []
    start_pattern = re.compile(
        r"^\s*(function\b|[A-Za-z_][A-Za-z0-9_]*\s*\([^;]*\)\s*\{|(?:const|let|var)\s+[A-Za-z_][A-Za-z0-9_]*\s*=\s*\([^;]*\)\s*=>\s*\{)"
    )
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if not start_pattern.search(line):
            idx += 1
            continue
        depth = 0
        found_open = False
        end = idx
        in_block_comment = False
        while end < len(lines):
            mask, in_block_comment = code_mask(lines[end], in_block_comment)
            for char_index, char in enumerate(lines[end]):
                if char_index >= len(mask) or not mask[char_index]:
                    continue
                if char == "{":
                    depth += 1
                    found_open = True
                elif char == "}":
                    depth -= 1
            if found_open and depth <= 0:
                break
            end += 1
        length = max(end - idx + 1, 1)
        if found_open and length > limit:
            violations.append(
                Violation(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    path=relative_path,
                    message=f"Function starting on line {idx + 1} is {length} lines long.",
                    line_number=idx + 1,
                    advisory=True,
                )
            )
        idx = max(end + 1, idx + 1)
    return violations


def detect_naming_convention(
    relative_path: str,
    path: Path,
    content: str,
    language: str,
    rule: Rule,
) -> list[Violation]:
    value = rule.value if isinstance(rule.value, dict) else {}
    target = value.get("target")
    style = value.get("style")
    violations: list[Violation] = []

    if target == "file" and style == "snake_case":
        stem = path.stem
        if not is_snake_case(stem):
            violations.append(
                Violation(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    path=relative_path,
                    message=f"File name '{path.name}' should use snake_case.",
                    advisory=True,
                )
            )
        return violations

    if target == "class" and style == "pascal_case":
        for line_number, line in enumerate(content.splitlines(), start=1):
            match = re.match(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", line)
            if not match:
                continue
            class_name = match.group(1)
            if not is_pascal_case(class_name):
                violations.append(
                    Violation(
                        rule_id=rule.rule_id,
                        rule_type=rule.rule_type,
                        path=relative_path,
                        message=f"Class '{class_name}' should use PascalCase.",
                        line_number=line_number,
                        advisory=True,
                    )
                )
        return violations

    return violations


DETECTORS: dict[str, callable] = {
    "assignment_spacing": detect_assignment_spacing,
    "comma_spacing": detect_comma_spacing,
    "forbid_regex": detect_forbid_regex,
    "function_max_lines": detect_function_max_lines,
    "indent_multiple_of_four": detect_indent_multiple_of_four,
    "inner_delimiter_spacing": detect_inner_delimiter_spacing,
    "max_consecutive_blank_lines": detect_max_consecutive_blank_lines,
    "max_line_length": detect_max_line_length,
    "missing_control_braces": detect_missing_control_braces,
    "naming_convention": detect_naming_convention,
    "no_inline_control": detect_no_inline_control,
    "no_tabs": detect_no_tabs,
    "no_trailing_whitespace": detect_no_trailing_whitespace,
    "require_regex": detect_require_regex,
}

FIXERS: dict[str, callable] = {
    "assignment_spacing": fix_assignment_spacing,
    "comma_spacing": fix_comma_spacing,
    "indent_multiple_of_four": fix_indent_multiple_of_four,
    "inner_delimiter_spacing": fix_inner_delimiter_spacing,
    "max_consecutive_blank_lines": fix_max_consecutive_blank_lines,
    "max_line_length": fix_max_line_length,
    "no_tabs": fix_no_tabs,
    "no_trailing_whitespace": fix_no_trailing_whitespace,
}


def is_safe_fixable(rule: Rule) -> bool:
    return rule.rule_type in SAFE_FIXABLE_RULE_TYPES or rule.rule_id in SAFE_REGEX_FIXERS
