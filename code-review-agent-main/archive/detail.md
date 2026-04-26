# Code Review Agent Details

## Project Overview
The Code Review Agent is a Python-based CLI tool designed to validate GitHub commits in private repositories. It checks if:
1. The commit was made by an authorized employee.
2. The code adheres to a set of predefined rules across the repository tree.

## Technical Stack
- **Language**: Python 3.9+
- **Key Libraries**:
    - `python-dotenv`: Environment variable management.
    - `requests`: GitHub API interaction.
    - `python-docx`: Possibly for reporting (though README mentions HTML).
- **Core Components**:
    - `src/code_validator/cli.py`: Entry point for CLI.
    - `src/code_validator/github/`: GitHub API client and models.
    - `src/code_validator/rules/`: Rule storage and models.
    - `src/code_validator/services/`: Business logic for validation, reporting, and email.
    - `src/code_validator/validators/`: Implementation of specific code rules.

## Rule System
Rules are defined in `rules/rules.json`. Supported rule types include:
1.  **max_line_length**: Restricts the maximum number of characters per line.
2.  **no_trailing_whitespace**: Ensures no trailing spaces or tabs at the end of lines.
3.  **forbid_regex**: Rejects files containing specific patterns.
4.  **require_regex**: Rejects files missing specific patterns.
5.  **inner_delimiter_spacing**: Enforces a single space inside delimiters like `( )`, `[ ]`, `{ }`.

## Project Structure
```text
code-review-agent-main/
├── README.md
├── main.py
├── requirements.txt
├── .env
├── .env.example
├── archive/
│   └── detail.md
├── rules/
│   └── rules.json
├── src/
│   └── code_validator/
│       ├── cli.py
│       ├── github/
│       ├── rules/
│       ├── services/
│       └── validators/
```

## Running the Agent
```bash
python3 main.py --repo <org/repo> --branch <branch-name>
```

## Progress
- [x] Update `rules.json` with comprehensive rules.
- [x] Set up environment variables in `.env`.
- [x] Install dependencies.
- [x] Run test execution on 'main' branch (Completed with 925 violations).
- [x] Verified that 'user-code-fix' branch does not exist on the repository.

## Test Results (Branch: main)
- **Status**: FAILED (Guideline violations detected)
- **Total Violations**: 925
- **Key Violation Types**:
    - `py-require-docstring`: Every module/function is missing docstrings.
    - `py-inner-spacing`: Missing spaces like `foo( bar )` instead of `foo(bar)`.
    - `py-no-print`: Use of `print()` instead of logging.
    - `py-max-line-length`: Several lines exceed the 100-character limit.
- **Report Location**: `reports/validation-report-ftpsofts_code-review-agent-main-20260426-105359.html`
