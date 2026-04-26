from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

@dataclass( frozen = True )
class Rule:
    rule_id: str
    rule_type: str
    description: str
    value: Any = None
    pattern: str | None = None
    flags: str = ""

@dataclass( frozen = True )
class RuleSet:
    global_rules: list[ Rule ] = field( default_factory = list )
    language_rules: dict[ str, list[ Rule ] ] = field( default_factory = dict )

    def rules_for_language( self, language: str | None ) -> list[ Rule ]:
        if not language:
            return list( self.global_rules )
        return [ *self.global_rules, *self.language_rules.get( language.lower(), [] ) ]
