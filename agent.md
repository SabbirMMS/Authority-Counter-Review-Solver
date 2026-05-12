# Authority Counter Review Solver - Agent Context

This file serves as the contextual onboarding document for any AI agents working on this project. Please review this document to understand the project architecture, goals, and specific design rules before making modifications.

## Project Purpose
`authority-counter-review-solver` is an interactive Python CLI tool and module designed to analyze, report, and automatically fix codebase formatting and styling violations. It is designed to act as a preparatory/cleanup step for projects that will be evaluated by an "authority-style reviewer" (`code-review-agent-main`).

It supports Python, JavaScript, TypeScript, PHP, Dart, HTML, and CSS.

## Architecture & Core Files
The tool is built completely in Python (3.11+) with no third-party dependencies required for the core solver.

*   `main.py` - The CLI entrypoint. Parses arguments and orchestrates modes (bulk, folder, manual).
*   `counter_solver/engine.py` - The core engine. Contains the rules for detection (`detect_*`) and safe autofixing (`fix_*`). Also contains the core loop `apply_safe_fixes`.
*   `counter_solver/defaults.py` - Contains the default `RuleSet` (global rules and language-specific rules) and defines `SAFE_FIXABLE_RULE_TYPES`.
*   `counter_solver/models.py` - Dataclasses representing `Rule`, `RuleSet`, `Violation`, `FileResult`, etc.
*   `counter_solver/text_utils.py` - Utilities for safe string manipulation, notably `code_mask()` which is critical for masking out strings, block comments, and triple-quotes so fixers don't accidentally format inside literal strings.
*   `counter_solver/rules.py` - Logic for loading and merging custom `.json` rule profiles.
*   `tests/` - The `unittest` suite testing individual fixers and full CLI workflows.

## Essential Operational Rules & Fixer Execution Order
The engine intentionally prioritizes the order in which auto-fixers are applied to prevent regressions (found in `apply_safe_fixes` in `engine.py`). 
**Do not change this order without deep consideration:**
1.  **Standard Rules (Priority 0):** Spacing, strict equality, tabs, indentations, etc., are applied first.
2.  **Max Line Length (Priority 1):** Runs late. The default limit is **110 characters**. This runs *after* spacing modifications to ensure it catches lines that were lengthened by previous fixers.
3.  **No Trailing Whitespace (Priority 2):** Runs absolutely last. This guarantees that errant whitespace introduced by any previous fixers (e.g., assignment spacing wrapping an `=` to the end of a line) is completely scrubbed away.

## Recent Fixes & Critical Edge Cases
When modifying fixers, be aware of these established protections:
*   **Trailing Whitespace:** The `fix_assignment_spacing` specifically strips trailing whitespace on modified lines, but we also rely on the `no_trailing_whitespace` fixer running last as a final catch-all.
*   **Blade / HTML Comments:** `<!--` and `-->` are explicitly protected inside `_normalize_assignment_segment` using placeholder substitution so they are not incorrectly split into `- ->` by the assignment spacing normalizer.
*   **Strict Equality:** The `strict_equality` fixer cleanly transitions `==` to `===` and `!=` to `!==` in JS, TS, and PHP using a character-by-character replacement approach coupled with `code_mask` to safely avoid strings. 
*   **Max Line Length:** The maximum line length is standardized at **110 characters**.

## Modes of Operation
*   **Bulk:** Scans the entire project, shows a preview, and asks to apply safe fixes.
*   **Folder:** Prompts the user folder-by-folder to allow, recursively allow, inspect, or skip.
*   **Manual:** Shows all violations and allows the user to specify exactly which files and rule IDs to run via comma-separated lists.

## Testing
Always run the test suite after making changes to ensure regressions aren't introduced to the code-masking or string parsers.

```bash
# Run tests
python3 -m unittest discover -s tests

# Or manually run specific targeted tests locally
python3 -c "import ... " 
```
