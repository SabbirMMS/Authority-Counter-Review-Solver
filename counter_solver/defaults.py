from __future__ import annotations

from counter_solver.models import Rule, RuleSet


LANGUAGE_EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".php": "php",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".dart": "dart",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
}

DEFAULT_IGNORED_DIRS: tuple[str, ...] = (
    ".git",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "vendor",
    "build",
    "dist",
    ".dart_tool",
)

SAFE_FIXABLE_RULE_TYPES: frozenset[str] = frozenset(
    {
        "assignment_spacing",
        "comma_spacing",
        "indent_multiple_of_four",
        "inner_delimiter_spacing",
        "max_consecutive_blank_lines",
        "max_line_length",
        "no_tabs",
        "no_trailing_whitespace",
    }
)


def build_default_ruleset() -> RuleSet:
    global_rules = [
        Rule(
            rule_id="global-no-trailing-whitespace",
            rule_type="no_trailing_whitespace",
            description="Lines must not have trailing whitespace.",
        ),
        Rule(
            rule_id="global-no-tabs",
            rule_type="no_tabs",
            description="Tabs are not allowed in source formatting.",
        ),
        Rule(
            rule_id="global-indent-multiple-of-four",
            rule_type="indent_multiple_of_four",
            description="Indentation should use 4-space steps.",
        ),
        Rule(
            rule_id="global-max-consecutive-blank-lines",
            rule_type="max_consecutive_blank_lines",
            description="Keep at most one empty line between logical blocks.",
            value=1,
        ),
        Rule(
            rule_id="global-max-line-length",
            rule_type="max_line_length",
            description="Lines should not exceed 120 characters.",
            value=120,
        ),
        Rule(
            rule_id="global-inner-delimiter-spacing",
            rule_type="inner_delimiter_spacing",
            description="Use single spaces inside (), [] and {}.",
            value=["()", "[]", "{}"],
        ),
        Rule(
            rule_id="global-comma-spacing",
            rule_type="comma_spacing",
            description="Use a single space after commas and none before them.",
        ),
        Rule(
            rule_id="global-assignment-spacing",
            rule_type="assignment_spacing",
            description="Use spaces around assignment and comparison operators.",
        ),
    ]

    function_length_rule = Rule(
        rule_id="advisory-function-length",
        rule_type="function_max_lines",
        description="Prefer functions under 60 lines.",
        value=60,
    )
    class_naming_rule = Rule(
        rule_id="advisory-class-pascal-case",
        rule_type="naming_convention",
        description="Class names should use PascalCase.",
        value={"target": "class", "style": "pascal_case"},
    )

    language_rules = {
        "python": [
            function_length_rule,
            class_naming_rule,
        ],
        "javascript": [
            Rule(
                rule_id="advisory-js-control-braces",
                rule_type="missing_control_braces",
                description="Always use braces for control blocks.",
            ),
            Rule(
                rule_id="advisory-js-inline-control",
                rule_type="no_inline_control",
                description="Inline control statements are discouraged.",
            ),
            function_length_rule,
            class_naming_rule,
        ],
        "typescript": [
            Rule(
                rule_id="advisory-ts-control-braces",
                rule_type="missing_control_braces",
                description="Always use braces for control blocks.",
            ),
            Rule(
                rule_id="advisory-ts-inline-control",
                rule_type="no_inline_control",
                description="Inline control statements are discouraged.",
            ),
            function_length_rule,
            class_naming_rule,
        ],
        "php": [
            Rule(
                rule_id="advisory-php-control-braces",
                rule_type="missing_control_braces",
                description="Always use braces for control blocks.",
            ),
            Rule(
                rule_id="advisory-php-inline-control",
                rule_type="no_inline_control",
                description="Inline control statements are discouraged.",
            ),
            function_length_rule,
            class_naming_rule,
        ],
        "dart": [
            Rule(
                rule_id="advisory-dart-control-braces",
                rule_type="missing_control_braces",
                description="Always use braces for control blocks.",
            ),
            Rule(
                rule_id="advisory-dart-inline-control",
                rule_type="no_inline_control",
                description="Inline control statements are discouraged.",
            ),
            function_length_rule,
            class_naming_rule,
            Rule(
                rule_id="advisory-dart-file-snake-case",
                rule_type="naming_convention",
                description="Dart file names should use snake_case.",
                value={"target": "file", "style": "snake_case"},
            ),
        ],
        "html": [],
        "css": [],
    }

    return RuleSet(global_rules=global_rules, language_rules=language_rules)
