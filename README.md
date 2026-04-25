# Counter Review Solver

Interactive Python fixer for projects that are being checked by the authority-style reviewer in `code-review-agent-main`.

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

### Manual

Scans first, then shows:

- fixable files
- fixable rule ids

You choose which files and which rule ids should be applied. This is the safest mode when you want tight control.

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
