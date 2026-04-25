from __future__ import annotations

import unittest
from pathlib import Path

from counter_solver.rules import load_ruleset


class RuleLoaderTests(unittest.TestCase):
    def test_authority_style_override_merges_with_defaults(self) -> None:
        fixture = Path(__file__).resolve().parent / "fixtures" / "authority_rules.json"
        ruleset = load_ruleset(str(fixture))

        global_ids = {rule.rule_id for rule in ruleset.global_rules}
        self.assertIn("global-no-tabs", global_ids)

        max_line_length = next(rule for rule in ruleset.global_rules if rule.rule_id == "global-max-line-length")
        self.assertEqual(max_line_length.value, 80)

        javascript_ids = {rule.rule_id for rule in ruleset.language_rules["javascript"]}
        self.assertIn("js-no-debugger", javascript_ids)
        self.assertIn("advisory-js-control-braces", javascript_ids)


if __name__ == "__main__":
    unittest.main()
