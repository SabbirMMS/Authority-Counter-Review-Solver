from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from counter_solver.defaults import build_default_ruleset
from counter_solver.models import Rule, RuleSet


def load_ruleset(custom_rules_path: str | None = None) -> RuleSet:
    ruleset = build_default_ruleset()
    if not custom_rules_path:
        return ruleset

    override = load_rule_file(Path(custom_rules_path))
    return merge_rulesets(ruleset, override)


def load_rule_file(path: Path) -> RuleSet:
    data = json.loads(path.read_text(encoding="utf-8"))
    global_rules = [to_rule(item) for item in data.get("global", [])]
    language_rules = {
        language.lower(): [to_rule(item) for item in items]
        for language, items in data.get("languages", {}).items()
    }
    return RuleSet(global_rules=global_rules, language_rules=language_rules)


def merge_rulesets(base: RuleSet, override: RuleSet) -> RuleSet:
    global_map = {item.rule_id: item for item in base.global_rules}
    for item in override.global_rules:
        global_map[item.rule_id] = item

    language_rules: dict[str, list[Rule]] = {}
    all_languages = set(base.language_rules) | set(override.language_rules)
    for language in all_languages:
        merged = {item.rule_id: item for item in base.language_rules.get(language, [])}
        for item in override.language_rules.get(language, []):
            merged[item.rule_id] = item
        language_rules[language] = list(merged.values())

    return RuleSet(global_rules=list(global_map.values()), language_rules=language_rules)


def to_rule(data: dict[str, Any]) -> Rule:
    return Rule(
        rule_id=data["id"],
        rule_type=data["type"],
        description=data.get("description", ""),
        value=data.get("value"),
        pattern=data.get("pattern"),
        flags=data.get("flags", ""),
    )
