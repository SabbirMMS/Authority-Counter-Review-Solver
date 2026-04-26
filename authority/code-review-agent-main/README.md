# GitHub Commit Code Validator

Python CLI to validate whether the latest commit on a private GitHub repository branch:

1. Was made by an employee.
2. Passes configured code rules across the full repository tree.

Validation scans files recursively in all directories/subdirectories except paths listed in `EXCLUDED_DIRS`. Each entry may be a directory prefix or an exact file path. Language is auto-detected from file extension, and only files whose language has at least one rule in `rules.json` are validated.

Rules are stored in `rules/rules.json` and maintained manually whenever our guideline document changes.

## Project Structure

```text
code-validator/
  main.py
  requirements.txt
  .env.example
  src/code_validator/
    cli.py
    config/settings.py
    github/
      client.py
      models.py
    rules/
      models.py
      rules_store.py
    services/
      commit_validation_service.py
      email_service.py
      reporting_service.py
    validators/
      base_validator.py
      text_validators.py
```

## Setup

```bash
cd /home/zisun/projects/automations/python/bots/code-validator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set these variables in `.env`:

- `GITHUB_TOKEN` (required, with private repo read permissions)
- `RULES_PATH` (path to manually maintained `rules.json`)
- `EXCLUDED_DIRS` (ore framework directories to skip recursively)
- Employee identity config:
- `EMPLOYEE_GITHUB_LOGINS` and/or `EMPLOYEE_EMAILS`
- Optional `GITHUB_ORG` for org membership check
- Optional email reporting config:
- `REPORT_EMAIL` (single primary recipient)
- `CC_EMAILS` (comma-separated CC recipients)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_USE_TLS`

## Usage

Run validation:

```bash
python main.py --repo your-org/your-repo --branch main
```

Notes on branch names and quoting:

- Branch names that contain slashes (for example `feature/xyz` or `FrontendTesting/A2`) are supported. You can pass them without quotes:

```bash
python main.py --repo your-org/your-repo --branch FrontendTesting/A2
```

- If a branch name includes shell-special characters or spaces, wrap it in quotes (single quotes are safest in bash):

```bash
python main.py --repo your-org/your-repo --branch 'feature/$weird name'
```

When `REPORT_EMAIL` is configured, a visual HTML report is generated in `reports/` and emailed to that recipient. `CC_EMAILS` are sent as carbon copy. Each violation row includes a GitHub deep link to the exact file and line. Email delivery is best-effort: SMTP failures are logged as warnings and do not change the validation result.

## Rule Format in rules.json

`rules/rules.json` uses this structure:

```json
{
  "metadata": {"version": 1, "source": "manual"},
  "global": [
    {
      "id": "global-no-trailing-whitespace",
      "type": "no_trailing_whitespace",
      "description": "Lines must not have trailing whitespace."
    }
  ],
  "languages": {
    "python": [
      {
        "id": "py-max-line-length",
        "type": "max_line_length",
        "description": "Python line length limit",
        "value": 100
      }
    ]
  }
}
```

Supported rule types:

- `max_line_length`
- `no_trailing_whitespace`
- `forbid_regex`
- `require_regex`
- `inner_delimiter_spacing`

If a language has no rules and there are no global rules, files for that language are skipped.

## Exit Codes

- `0`: validation passed
- `1`: non-employee commit or rule violations
- `2`: configuration/runtime error
