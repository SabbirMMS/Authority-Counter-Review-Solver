from __future__ import annotations

from dataclasses import dataclass

from code_validator.github.client import GitHubClient
from code_validator.github.models import CommitSummary, Violation
from code_validator.rules.models import Rule, RuleSet
from code_validator.validators.base_validator import BaseRuleValidator


@dataclass(frozen=True)
class ValidationResult:
    repo: str
    branch: str
    commit_sha: str
    checked_files: int
    skipped_files: int
    violations: list[Violation]
    author_login: str | None
    author_email: str | None


class EmployeeRegistry:
    def __init__(
        self,
        github_client: GitHubClient,
        org: str | None,
        employee_logins: set[str],
        employee_emails: set[str],
    ) -> None:
        self._github_client = github_client
        self._org = org
        self._employee_logins = employee_logins
        self._employee_emails = employee_emails

    def is_employee(self, commit: CommitSummary) -> bool:
        return self.is_employee_identity(commit.author_login, commit.author_email)

    def is_employee_identity(self, author_login: str | None, author_email: str | None) -> bool:
        if author_login and author_login in self._employee_logins:
            return True
        if author_email and author_email in self._employee_emails:
            return True
        if self._org and author_login:
            return self._github_client.is_org_member(self._org, author_login)
        return False


class CommitValidationService:
    def __init__(
        self,
        github_client: GitHubClient,
        validators: list[BaseRuleValidator],
        excluded_dirs: tuple[str, ...],
        only_dirs: tuple[str, ...] | None = None,
    ) -> None:
        self._github_client = github_client
        self._validators = validators
        self._excluded_dirs = excluded_dirs
        self._only_dirs = only_dirs

    def validate_latest_commit(
        self,
        repo: str,
        branch: str,
        ruleset: RuleSet,
    ) -> ValidationResult:
        commit = self._github_client.get_latest_commit(repo, branch)
        files = self._github_client.list_repository_files(repo, commit.tree_sha)

        violations: list[Violation] = []
        checked_files = 0
        skipped_files = 0

        for path in files:
            if not self._should_check(path):
                skipped_files += 1
                continue

            language = self._infer_language(path)
            if not language or not self._has_language_rules(ruleset, language):
                skipped_files += 1
                continue

            rules = ruleset.rules_for_language(language)

            content = self._github_client.get_file_content(repo, path, commit.sha)
            checked_files += 1
            violations.extend(self._validate_file(path, content, rules))

        return ValidationResult(
            repo=repo,
            branch=branch,
            commit_sha=commit.sha,
            checked_files=checked_files,
            skipped_files=skipped_files,
            violations=violations,
            author_login=commit.author_login,
            author_email=commit.author_email,
        )

    def _validate_file(self, path: str, content: str, rules: list[Rule]) -> list[Violation]:
        violations: list[Violation] = []
        for rule in rules:
            for validator in self._validators:
                if validator.supports(rule.rule_type):
                    violations.extend(validator.validate(path=path, content=content, rule=rule))
                    break
        return violations

    def _should_check(self, path: str) -> bool:
        """Determine if a file should be checked based on only_dirs and excluded_dirs."""
        norm = path.strip("/")

        # If only_dirs is specified, check if path is in one of the allowed directories
        if self._only_dirs:
            in_allowed_dir = False
            for only_dir in self._only_dirs:
                prefix = only_dir.strip("/")
                if not prefix:
                    continue
                if norm == prefix or norm.startswith(f"{prefix}/"):
                    in_allowed_dir = True
                    break
            if not in_allowed_dir:
                return False

        # Check if path is excluded
        for excluded in self._excluded_dirs:
            prefix = excluded.strip("/")
            if not prefix:
                continue
            if norm == prefix:
                return False
            if norm.startswith(f"{prefix}/"):
                return False
        return True

    @staticmethod
    def _has_language_rules(ruleset: RuleSet, language: str) -> bool:
        return bool(ruleset.language_rules.get(language.lower()))

    @staticmethod
    def _infer_language(path: str) -> str | None:
        mapping = {
            ".py": "python",
            ".php": "php",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".dart": "dart",
            ".java": "java",
            ".sql": "sql",
            ".go": "go",
            ".rb": "ruby",
            ".rs": "rust",
            ".cpp": "cpp",
            ".c": "c",
        }
        for suffix, language in mapping.items():
            if path.lower().endswith(suffix):
                return language
        return None
