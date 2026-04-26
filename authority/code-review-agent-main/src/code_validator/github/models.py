from __future__ import annotations

from dataclasses import dataclass

@dataclass( frozen = True )
class CommitSummary:
    sha: str
    tree_sha: str
    author_login: str | None
    author_email: str | None

@dataclass( frozen = True )
class CommitFile:
    filename: str
    status: str

@dataclass( frozen = True )
class Violation:
    rule_id: str
    path: str
    message: str
    line_number: int | None = None
