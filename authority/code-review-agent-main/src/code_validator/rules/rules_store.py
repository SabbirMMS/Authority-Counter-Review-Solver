from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from code_validator.rules.models import Rule, RuleSet

class RuleStore:
    def __init__( self, path: Path ) -> None:
        self._path = path

    @property
    def path( self ) -> Path:
        return self._path

    def exists( self ) -> bool:
        return self._path.exists()

    def load( self ) -> RuleSet:
        data = json.loads( self._path.read_text( encoding = "utf-8" ) )
        global_rules = [ self._to_rule( rule ) for rule in data.get( "global", [] ) ]
        language_rules = {
            language.lower(): [ self._to_rule( rule ) for rule in rule_list ]
            for language, rule_list in data.get( "languages", {} ).items()
        }
        return RuleSet( global_rules = global_rules, language_rules = language_rules )

    @staticmethod
    def _to_rule( data: dict[ str, Any ] ) -> Rule:
        return Rule(
            rule_id = data[ "id" ],
            rule_type = data[ "type" ],
            description = data.get( "description","" ),
            value = data.get( "value" ),
            pattern = data.get( "pattern" ),
            flags = data.get( "flags","" ),
        )
