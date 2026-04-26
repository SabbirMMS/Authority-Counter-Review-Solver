from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from counter_solver.defaults import DEFAULT_IGNORED_DIRS
from counter_solver.engine import (
    collect_supported_files,
    plan_fixes,
    scan_project,
    summarize_violations,
    write_changes,
)
from counter_solver.models import FileResult, FolderSelection, RunReport
from counter_solver.reporting import write_report
from counter_solver.rules import load_ruleset


SOLVER_ROOT = Path(__file__).resolve().parent.parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Counter solution for authority-style code review findings.")
    parser.add_argument("--project", help="Project folder to scan and fix.")
    parser.add_argument("--mode", choices=("bulk", "folder", "manual"), help="Run mode.")
    parser.add_argument("--rules", help="Optional authority-compatible rules JSON.")
    parser.add_argument("--only-rules", help="Comma-separated list of rule IDs to include.")
    parser.add_argument("--skip-rules", help="Comma-separated list of rule IDs to exclude.")
    parser.add_argument("--preview-only", action="store_true", help="Preview changes without writing files.")
    return parser


def run(
    argv: list[str] | None = None,
    input_func= input,
    output_stream: TextIO | None = None,
    report_dir: Path | None = None,
) -> int:
    out = output_stream or sys.stdout
    args = build_parser().parse_args(argv)

    project_root = resolve_project_root(args.project, input_func, out)
    if project_root is None:
        return 2

    mode = args.mode or prompt_choice(
        input_func,
        out,
        "Choose mode: [b]ulk, [f]older, [m]anual",
        {"b": "bulk", "f": "folder", "m": "manual"},
    )

    ruleset = load_ruleset(args.rules)

    if args.only_rules:
        only_ids = {rid.strip() for rid in args.only_rules.split(",") if rid.strip()}
        ruleset.global_rules = [r for r in ruleset.global_rules if r.rule_id in only_ids]
        for lang in ruleset.language_rules:
            ruleset.language_rules[lang] = [r for r in ruleset.language_rules[lang] if r.rule_id in only_ids]

    if args.skip_rules:
        skip_ids = {rid.strip() for rid in args.skip_rules.split(",") if rid.strip()}
        ruleset.global_rules = [r for r in ruleset.global_rules if r.rule_id not in skip_ids]
        for lang in ruleset.language_rules:
            ruleset.language_rules[lang] = [r for r in ruleset.language_rules[lang] if r.rule_id not in skip_ids]

    supported_files = collect_supported_files(project_root)
    if not supported_files:
        print("No supported source files were found in the selected project.", file=out)
        return 2

    target_files = supported_files
    if mode == "folder":
        selection = select_folders(project_root, input_func, out)
        target_files = [path for path in supported_files if selection.includes(project_root, path)]
    if not target_files:
        print("No files were selected for scanning.", file=out)
        return 2

    selected_rules_by_path = None
    preview_results = plan_fixes(project_root, target_files, ruleset)

    if mode == "manual":
        selected_rules_by_path = build_manual_selection(preview_results, input_func, out)
        preview_results = plan_fixes(project_root, target_files, ruleset, selected_rules_by_path=selected_rules_by_path)

    print_preview(preview_results, out)

    should_write = not args.preview_only
    if should_write:
        should_write = prompt_yes_no(input_func, out, "Apply these safe fixes now?", default=True)

    changed_files = 0
    current_results = preview_results
    if should_write:
        changed_files = write_changes(preview_results)
        current_results = scan_project(project_root, target_files, ruleset)
        metadata_by_path = {item.relative_path: item for item in preview_results}
        for item in current_results:
            metadata = metadata_by_path.get(item.relative_path)
            if not metadata:
                continue
            item.applied_rule_ids = list(metadata.applied_rule_ids)
            item.skipped_fix_reasons = list(metadata.skipped_fix_reasons)

    report = RunReport(
        project_root=str(project_root),
        mode=mode,
        preview_only=not should_write,
        scanned_files=len(target_files),
        changed_files=sum(1 for item in preview_results if item.changed) if not should_write else changed_files,
        remaining_violations=sum(len(item.violations_after) for item in current_results),
        original_violations=sum(len(item.violations_before) for item in preview_results),
        skipped_unsafe_fixes=sum(len(item.skipped_fix_reasons) for item in preview_results),
        files=current_results if should_write else preview_results,
    )
    report_path = write_report(report_dir or (SOLVER_ROOT / "reports"), report)
    print(f"Report written to: {report_path}", file=out)

    print_summary(current_results if should_write else preview_results, changed_files if should_write else None, out)

    if report.remaining_violations:
        return 1
    return 0


def resolve_project_root(project_value: str | None, input_func, out: TextIO) -> Path | None:
    candidate = project_value
    while not candidate:
        entered = input_func("Project folder path: ").strip()
        candidate = entered or None
    project_root = Path(candidate).expanduser().resolve()
    if not project_root.exists() or not project_root.is_dir():
        print(f"Invalid project folder: {project_root}", file=out)
        return None
    return project_root


def prompt_choice(input_func, out: TextIO, prompt: str, choices: dict[str, str]) -> str:
    while True:
        value = input_func(f"{prompt}: ").strip().lower()
        if value in choices:
            return choices[value]
        print(f"Please choose one of: {', '.join(choices)}", file=out)


def prompt_yes_no(input_func, out: TextIO, prompt: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        value = input_func(f"{prompt} {suffix}: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please answer yes or no.", file=out)


def select_folders(project_root: Path, input_func, out: TextIO) -> FolderSelection:
    print("Folder mode guide:", file=out)
    print("  - Type a single letter and press Enter.", file=out)
    print("  - a = include only files directly inside that folder", file=out)
    print("  - r = include that folder and every child folder under it", file=out)
    print("  - i = include that folder, then choose child folders one by one", file=out)
    print("  - s = skip that folder", file=out)
    include_root_files = prompt_yes_no(input_func, out, "Include supported files from the project root?", default=True)
    shallow_dirs: list[Path] = []
    recursive_dirs: list[Path] = []

    def walk(current_root: Path) -> None:
        children = sorted(
            [
                child for child in current_root.iterdir()
                if child.is_dir()
                and not child.name.startswith(".")
                and child.name not in DEFAULT_IGNORED_DIRS
            ],
            key=lambda item: item.name.lower(),
        )
        for child in children:
            choice = prompt_choice(
                input_func,
                out,
                (
                    f"{child.relative_to(project_root).as_posix()} -> "
                    "[a] allow this folder, [r] allow folder + all children, "
                    "[i] inspect children individually, [s] skip"
                ),
                {"a": "allow", "r": "recursive", "i": "inspect", "s": "skip"},
            )
            if choice == "allow":
                shallow_dirs.append(child)
            elif choice == "recursive":
                recursive_dirs.append(child)
            elif choice == "inspect":
                shallow_dirs.append(child)
                walk(child)

    walk(project_root)
    return FolderSelection(
        shallow_dirs=tuple(shallow_dirs),
        recursive_dirs=tuple(recursive_dirs),
        include_root_files=include_root_files,
    )


def build_manual_selection(results: list[FileResult], input_func, out: TextIO) -> dict[str, set[str]]:
    fixable_files = [item for item in results if any(violation.fixable for violation in item.violations_before)]
    if not fixable_files:
        print("No safe autofix candidates were found in manual mode.", file=out)
        return {}

    print("Manual mode guide:", file=out)
    print("  - Enter comma-separated numbers like 1,2,3", file=out)
    print("  - Spaces are allowed, so 1, 2, 3 also works", file=out)
    print("  - Enter all to select every item in the current list", file=out)
    print("  - Choose files first, then choose rule ids", file=out)
    print("Fixable files:", file=out)
    for index, item in enumerate(fixable_files, start=1):
        print(f"  {index}. {item.relative_path}", file=out)

    chosen_files = prompt_index_selection(
        input_func,
        out,
        "Select files to fix by number or 'all' (example: 1,2,3 or all)",
        len(fixable_files),
    )
    selected_files = fixable_files if chosen_files is None else [fixable_files[index - 1] for index in sorted(chosen_files)]

    available_rules = sorted(
        {
            violation.rule_id
            for item in selected_files
            for violation in item.violations_before
            if violation.fixable
        }
    )
    if not available_rules:
        return {}

    print("Fixable rule ids:", file=out)
    for index, rule_id in enumerate(available_rules, start=1):
        print(f"  {index}. {rule_id}", file=out)

    chosen_rules = prompt_index_selection(
        input_func,
        out,
        "Select rule ids to apply by number or 'all' (example: 1,2,3 or all)",
        len(available_rules),
    )
    selected_rule_ids = set(available_rules) if chosen_rules is None else {available_rules[index - 1] for index in chosen_rules}
    return {item.relative_path: set(selected_rule_ids) for item in selected_files}


def prompt_index_selection(input_func, out: TextIO, prompt: str, max_index: int) -> set[int] | None:
    while True:
        value = input_func(f"{prompt}: ").strip().lower()
        if value == "all":
            return None
        try:
            numbers = {int(item.strip()) for item in value.split(",") if item.strip()}
        except ValueError:
            print("Please enter comma-separated numbers such as 1,2,3 or use 'all'.", file=out)
            continue
        if not numbers:
            print("Please choose at least one item.", file=out)
            continue
        if any(number < 1 or number > max_index for number in numbers):
            print(f"Please choose numbers between 1 and {max_index}.", file=out)
            continue
        return numbers


def print_preview(results: list[FileResult], out: TextIO) -> None:
    original_counts = summarize_violations(results)
    remaining_counts = summarize_violations(results, use_after=True)
    print("", file=out)
    print("Preview summary", file=out)
    print(f"  Files scanned: {len(results)}", file=out)
    print(f"  Files with proposed changes: {sum(1 for item in results if item.changed)}", file=out)
    print(f"  Violations before fixes: {sum(original_counts.values())}", file=out)
    print(f"  Violations after safe fixes: {sum(remaining_counts.values())}", file=out)

    if original_counts:
        print("  Rule counts before:", file=out)
        for rule_id, count in sorted(original_counts.items()):
            print(f"    - {rule_id}: {count}", file=out)

    if remaining_counts:
        print("  Remaining rule counts after safe fixes:", file=out)
        for rule_id, count in sorted(remaining_counts.items()):
            print(f"    - {rule_id}: {count}", file=out)


def print_summary(results: list[FileResult], written_files: int | None, out: TextIO) -> None:
    changed_files = written_files if written_files is not None else sum(1 for item in results if item.changed)
    remaining = sum(len(item.violations_after) for item in results)
    skipped = sum(len(item.skipped_fix_reasons) for item in results)

    print("", file=out)
    print("Run summary", file=out)
    print(f"  Files scanned: {len(results)}", file=out)
    print(f"  Files changed: {changed_files}", file=out)
    print(f"  Remaining violations: {remaining}", file=out)
    print(f"  Skipped unsafe fixes: {skipped}", file=out)

    changed_paths = [item.relative_path for item in results if item.changed]
    if changed_paths and written_files is None:
        print("  Proposed file changes:", file=out)
        for path in changed_paths:
            print(f"    - {path}", file=out)

    stubborn_files = [item for item in results if item.violations_after]
    if stubborn_files:
        print("  Files still needing manual attention:", file=out)
        for item in stubborn_files[:15]:
            print(f"    - {item.relative_path}", file=out)


def collect_fixable_rule_ids(results: list[FileResult]) -> set[str]:
    return {
        violation.rule_id
        for item in results
        for violation in item.violations_before
        if violation.fixable
    }
