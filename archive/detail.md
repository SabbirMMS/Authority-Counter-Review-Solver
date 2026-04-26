# Project Progress: Code Review Solver Refinement

## Objective
Fix critical bugs in the `counter-solver` tool and ensure perfect, rule-compliant code formatting across multiple languages (Python, Dart, JS).

## Progress Log

### 2026-04-26
- **Operator Splitting Bug Fix**: Refactored `_normalize_assignment_segment` to use a single-pass regex for multi-character operators (e.g., `+=`, `===`, `!==`).
- **Python Floor Division Support**: Updated `code_mask` to prevent `//` from being treated as a comment in Python.
- **Refined Line Wrapping**: Fixed an issue where `max-line-length` fixes could leave trailing spaces on broken lines. Added aggressive `rstrip()` to segments and a check to avoid empty indentation-only lines.
- **CLI Enhancements**: Added `--only-rules` and `--skip-rules` flags to allow selective rule application from the command line.
- **Expanded Rule Support**:
    - Added generic regex fixer (`fix_regex_rule`).
    - Added safe fixers for `global-no-tabs` and `global-no-multiple-empty-lines`.
    - Added `global-assignment-spacing` and `global-comma-spacing` to the primary `rules.json`.
- **Language-Aware Indentation**: Updated the indentation fixer/detector to use a 2-space step for Dart and 4-space step for others (unless overridden).
- **Manual Cleanup**: Restored `reporting_service.py` in the `code-review-agent` project after it was broken by an earlier version of the solver.
- **Validation**: Verified the solver on the `code-review-agent` project. Fixable violations were reduced from ~1200 to ~50 (remaining are mostly advisory or non-fixable length issues).

## Current Status
The solver is now robust and language-aware. It handles complex Python and Dart syntax without breaking code logic. 

### Remaining Work
- Review the ~50 remaining violations in `code-review-agent` to see if more automated fixers can be added safely.
- Verify the solver against a larger Dart codebase if available.
