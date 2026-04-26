from __future__ import annotations

from abc import ABC, abstractmethod

from code_validator.github.models import Violation
from code_validator.rules.models import Rule

class BaseRuleValidator( ABC ):
    @abstractmethod
    def supports( self, rule_type: str ) -> bool:
        """Return True if this validator can process a rule type."""

    @abstractmethod
    def validate( self, path: str, content: str, rule: Rule ) -> list[ Violation ]:
        """Validate one file content against one rule."""
