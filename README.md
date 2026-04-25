# Authority Counter Review Solver

Repository name: `authority-counter-review-solver`

Clone URL:

```bash
git clone https://github.com/SabbirMMS/authority-counter-review-solver.git
cd authority-counter-review-solver
```

Interactive Python fixer for projects that are being checked by the authority-style reviewer in `code-review-agent-main`.

GitHub profile: [github.com/SabbirMMS](https://github.com/SabbirMMS)  
Portfolio: [sabbirms.github.io](https://sabbirms.github.io)

It mirrors the reviewer’s real rule families:

- `no_trailing_whitespace`
- `max_line_length`
- `forbid_regex`
- `require_regex`
- `inner_delimiter_spacing`

It also adds a stricter safe-fix profile based on your formatting brief:

- tabs to 4 spaces
- indentation normalized toward 4-space steps
- one blank line between logical blocks
- safe comma and assignment/comparison spacing cleanup
- advisory detection for risky items such as missing control braces, inline control statements, long functions, and some naming issues

## Requirements

- Python 3.11 or newer recommended
- No third-party packages are required for the root solver

## Files

- `main.py`: entrypoint
- `counter_solver/`: rule loading, scanning, fixers, reporting, CLI
- `reports/`: JSON run reports created when the tool runs
- `tests/`: `unittest` coverage for fixers and CLI flows

## How To Run

From the root folder:

```bash
python3 main.py
```

The script will ask for:

1. Project folder path
2. Mode:
   - `bulk`
   - `folder`
   - `manual`
3. Confirmation before writing changes

## Quick Start

Clone the repo:

```bash
git clone https://github.com/SabbirMMS/authority-counter-review-solver.git
cd authority-counter-review-solver
```

Run the interactive solver:

```bash
python3 main.py
```

Run preview only against a project:

```bash
python3 main.py --project /path/to/project --mode bulk --preview-only
```

Run the test suite:

```bash
python3 -m unittest discover -s tests
```

## Modes

### Bulk

Scans the whole selected project, previews safe changes, then asks before writing.

Use this when you want the fastest project-wide cleanup.

### Folder

Walks the project tree and asks for folder-by-folder permission.

For each folder you can choose:

- `a`: allow this folder only
- `r`: allow this folder and all children
- `i`: include this folder and inspect child folders one by one
- `s`: skip

It also asks whether root-level files should be included.

Folder input guide:

- type one letter only: `a`, `r`, `i`, or `s`
- press Enter after each choice
- use `i` when you want to keep drilling into child folders manually

### Manual

Scans first, then shows:

- fixable files
- fixable rule ids

You choose which files and which rule ids should be applied. This is the safest mode when you want tight control.

Manual selection guide:

- enter comma-separated numbers like `1,2,3`
- spaces are also accepted, so `1, 2, 3` works
- enter `all` to select every item in the current list
- first you select files, then you select rule ids
- ranges like `1-5` are not supported in the current CLI

## Optional Flags

You can skip the initial prompts with flags:

```bash
python3 main.py --project /path/to/project --mode bulk
```

Available flags:

- `--project`
- `--mode bulk|folder|manual`
- `--rules path/to/rules.json`
- `--preview-only`

Examples:

```bash
python3 main.py --project /work/app --mode bulk --preview-only
python3 main.py --project /work/app --mode manual
python3 main.py --project /work/app --mode bulk --rules custom-rules.json
```

## Command Examples

Bulk preview:

```bash
python3 main.py --project /work/app --mode bulk --preview-only
```

Expected output sample:

```text
Preview summary
  Files scanned: 18
  Files with proposed changes: 12
  Violations before fixes: 1113
  Violations after safe fixes: 15
  Rule counts before:
    - global-no-trailing-whitespace: 3
    - global-max-line-length: 12
  Remaining rule counts after safe fixes:
    - global-max-line-length: 14

Report written to: /path/to/reports/counter-solver-report-YYYYMMDD-HHMMSS.json

Run summary
  Files scanned: 18
  Files changed: 12
  Remaining violations: 15
  Skipped unsafe fixes: 1
```

Bulk apply:

```bash
python3 main.py --project /work/app --mode bulk
```

Expected interactive flow sample:

```text
Apply these safe fixes now? [Y/n]: y
Report written to: /path/to/reports/counter-solver-report-YYYYMMDD-HHMMSS.json

Run summary
  Files scanned: 18
  Files changed: 12
  Remaining violations: 15
  Skipped unsafe fixes: 1
```

Folder mode:

```bash
python3 main.py --project /work/app --mode folder
```

Expected interactive flow sample:

```text
Include supported files from the project root? [Y/n]: y
src -> [a] allow this folder, [r] allow folder + all children, [i] inspect children individually, [s] skip: i
src/components -> [a] allow this folder, [r] allow folder + all children, [i] inspect children individually, [s] skip: r
src/utils -> [a] allow this folder, [r] allow folder + all children, [i] inspect children individually, [s] skip: s
tests -> [a] allow this folder, [r] allow folder + all children, [i] inspect children individually, [s] skip: a
```

Manual mode:

```bash
python3 main.py --project /work/app --mode manual
```

Expected interactive flow sample:

```text
Fixable files:
  1. src/app.js
  2. src/utils/helpers.js

Select files to fix by number or 'all' (example: 1,2,3 or all): 1,2
Fixable rule ids:
  1. global-no-trailing-whitespace
  2. global-inner-delimiter-spacing

Select rule ids to apply by number or 'all' (example: 1,2,3 or all): all
Apply these safe fixes now? [Y/n]: y
```

Another valid manual example:

```text
Select files to fix by number or 'all' (example: 1,2,3 or all): 1, 2, 3, 4, 5
Select rule ids to apply by number or 'all' (example: 1,2,3 or all): 1,3,6
```

If you want every listed file or every listed rule id, just type:

```text
all
```

Custom rules:

```bash
python3 main.py --project /work/app --mode bulk --rules custom-rules.json
```

Test run:

```bash
python3 -m unittest discover -s tests
```

Expected output sample:

```text
.........
----------------------------------------------------------------------
Ran 9 tests in 0.009s

OK
```

## Custom Rules

The solver loads built-in defaults first, then optionally merges a custom JSON file using the same authority-compatible schema:

```json
{
  "metadata": { "version": 1, "source": "manual" },
  "global": [
    {
      "id": "global-max-line-length",
      "type": "max_line_length",
      "description": "Override line length",
      "value": 100
    }
  ],
  "languages": {
    "javascript": [
      {
        "id": "js-no-debugger",
        "type": "forbid_regex",
        "description": "Debugger is forbidden",
        "pattern": "\\bdebugger\\b"
      }
    ]
  }
}
```

If a custom rule id matches a built-in rule id, the custom rule overrides it. New rule ids are added on top.

## What Gets Auto-Fixed

Safe autofix covers:

- trailing whitespace
- tabs outside strings/comments
- max consecutive blank lines
- inner delimiter spacing
- comma spacing
- assignment/comparison spacing
- best-effort 4-space indentation cleanup
- line wrapping at or before column 120 when a safe break space exists

## What Stays Advisory

These are detected and reported, but not rewritten generically in v1:

- missing braces for control blocks
- inline `if` / `for` / `while`
- long functions
- some naming issues such as non-PascalCase class names or non-snake-case Dart filenames
- regex rules without a known safe autofix

## Reports

Every run writes a JSON report into `reports/`.

The report contains:

- project root
- mode
- preview/write status
- files scanned
- files changed
- original violation count
- remaining violation count
- per-file violation details

## Exit Codes

- `0`: no remaining violations after the run or preview
- `1`: run completed but violations still remain
- `2`: invalid path, no supported files, or runtime setup error

## Supported File Types

- Python
- PHP
- JavaScript
- TypeScript
- Dart
- HTML
- CSS

## Tests

Run the test suite from the root:

```bash
python3 -m unittest discover -s tests
```

## Notes

- The authority repo does not include its live `rules.json`, so this solver does not depend on extracting one.
- Safe autofix is intentionally conservative around regex rules and structural rewrites.
- Line wrapping only happens when a safe space exists before the configured limit.
- Common heavy folders such as `.git`, `node_modules`, `vendor`, `dist`, `build`, `.venv`, and `__pycache__` are skipped automatically.

## Author

Sabbir MMS  
GitHub: [github.com/SabbirMMS](https://github.com/SabbirMMS)  
Portfolio: [sabbirms.github.io](https://sabbirms.github.io)

## Copyright

Copyright (c) 2026 Sabbir MMS. All rights reserved.
