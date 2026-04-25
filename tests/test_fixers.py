from __future__ import annotations

import unittest
from pathlib import Path

from counter_solver.engine import apply_safe_fixes
from counter_solver.models import Rule


class SafeFixerTests(unittest.TestCase):
    def apply_rules(self, content: str, rules: list[Rule], suffix: str = ".js") -> str:
        path = Path(f"sample{suffix}")
        updated, _, _ = apply_safe_fixes(
            relative_path=path.name,
            path=path,
            content=content,
            language="javascript" if suffix == ".js" else "python",
            rules=rules,
            allowed_rule_ids=None,
        )
        return updated

    def test_trailing_whitespace_is_removed(self) -> None:
        rule = Rule("global-no-trailing-whitespace", "no_trailing_whitespace", "trim")
        updated = self.apply_rules("const value = 1;   \n", [rule])
        self.assertEqual(updated, "const value = 1;\n")

    def test_tabs_outside_strings_are_replaced(self) -> None:
        rule = Rule("global-no-tabs", "no_tabs", "tabs")
        content = "\tconst value\t= 1;\nconst label = \"a\tb\";\n"
        updated = self.apply_rules(content, [rule])
        self.assertNotIn("\tconst value", updated)
        self.assertIn("\"a\tb\"", updated)

    def test_delimiter_and_comma_spacing_ignore_strings(self) -> None:
        rules = [
            Rule("global-comma-spacing", "comma_spacing", "comma"),
            Rule("global-inner-delimiter-spacing", "inner_delimiter_spacing", "delimiters", value=["()"]),
        ]
        content = "const result = call(a,b);\nconst label = \"(a,b)\";\n"
        updated = self.apply_rules(content, rules)
        self.assertIn("call( a, b )", updated)
        self.assertIn("\"(a,b)\"", updated)

    def test_blank_line_runs_are_collapsed(self) -> None:
        rule = Rule("global-max-consecutive-blank-lines", "max_consecutive_blank_lines", "blank lines", value=1)
        content = "first\n\n\nsecond\n"
        updated = self.apply_rules(content, [rule])
        self.assertEqual(updated, "first\n\nsecond\n")

    def test_long_lines_wrap_at_safe_spaces(self) -> None:
        rule = Rule("global-max-line-length", "max_line_length", "line length", value=120)
        content = (
            "const result = combine( alpha, beta, gamma, delta, epsilon, zeta, eta, theta, "
            "iota, kappa, lambda, mu, nu, xi, omicron );\n"
        )
        updated = self.apply_rules(content, [rule])
        self.assertIn("\n", updated.strip())
        for line in updated.splitlines():
            self.assertLessEqual(len(line), 120)


if __name__ == "__main__":
    unittest.main()
