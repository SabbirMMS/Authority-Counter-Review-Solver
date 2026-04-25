from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Rule:
    rule_id: str
    rule_type: str
    description: str
    value: Any = None
    pattern: str | None = None
    flags: str = ""


@dataclass(frozen=True)
class RuleSet:
    global_rules: list[Rule] = field(default_factory=list)
    language_rules: dict[str, list[Rule]] = field(default_factory=dict)

    def rules_for_language(self, language: str | None) -> list[Rule]:
        if not language:
            return list(self.global_rules)
        return [*self.global_rules, *self.language_rules.get(language.lower(), [])]


@dataclass(frozen=True)
class Violation:
    rule_id: str
    rule_type: str
    path: str
    message: str
    line_number: int | None = None
    fixable: bool = False
    advisory: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FileResult:
    path: Path
    relative_path: str
    language: str
    original_content: str
    proposed_content: str
    violations_before: list[Violation] = field(default_factory=list)
    violations_after: list[Violation] = field(default_factory=list)
    applied_rule_ids: list[str] = field(default_factory=list)
    skipped_fix_reasons: list[str] = field(default_factory=list)
    read_error: str | None = None

    @property
    def changed(self) -> bool:
        return self.original_content != self.proposed_content

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.relative_path,
            "language": self.language,
            "changed": self.changed,
            "applied_rule_ids": self.applied_rule_ids,
            "skipped_fix_reasons": self.skipped_fix_reasons,
            "read_error": self.read_error,
            "violations_before": [item.to_dict() for item in self.violations_before],
            "violations_after": [item.to_dict() for item in self.violations_after],
        }


@dataclass(frozen=True)
class FolderSelection:
    shallow_dirs: tuple[Path, ...] = ()
    recursive_dirs: tuple[Path, ...] = ()
    include_root_files: bool = True

    def includes(self, project_root: Path, candidate: Path) -> bool:
        relative = candidate.relative_to(project_root)
        parts = relative.parts
        if len(parts) == 1:
            return self.include_root_files

        for directory in self.recursive_dirs:
            try:
                candidate.relative_to(directory)
            except ValueError:
                continue
            return True

        for directory in self.shallow_dirs:
            if candidate.parent == directory:
                return True

        return False


@dataclass
class RunReport:
    project_root: str
    mode: str
    preview_only: bool
    scanned_files: int
    changed_files: int
    remaining_violations: int
    original_violations: int
    skipped_unsafe_fixes: int
    report_path: str = ""
    files: list[FileResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_root": self.project_root,
            "mode": self.mode,
            "preview_only": self.preview_only,
            "scanned_files": self.scanned_files,
            "changed_files": self.changed_files,
            "remaining_violations": self.remaining_violations,
            "original_violations": self.original_violations,
            "skipped_unsafe_fixes": self.skipped_unsafe_fixes,
            "report_path": self.report_path,
            "files": [item.to_dict() for item in self.files],
        }
