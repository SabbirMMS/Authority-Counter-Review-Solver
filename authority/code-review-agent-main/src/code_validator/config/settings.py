from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppSettings:
    github_token: str
    github_api_url: str
    github_org: str | None
    employee_github_logins: set[str]
    employee_emails: set[str]
    rules_path: Path
    excluded_dirs: tuple[str, ...]
    report_email: str | None
    cc_emails: set[str]
    smtp_host: str | None
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None
    smtp_from_email: str | None
    smtp_use_tls: bool
    signature_template_path: Path
    email_signature_name: str
    email_signature_designation: str
    email_signature_email: str
    email_signature_phone: str
    default_repo: str | None
    default_branch: str



def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())



def load_settings(env_path: str | None = None) -> AppSettings:
    load_dotenv(dotenv_path=env_path)

    rules_path = Path(os.getenv("RULES_PATH", "rules/rules.json"))
    signature_template_path = Path(os.getenv("SIGNATURE_TEMPLATE_PATH", "signature.html"))

    return AppSettings(
        github_token=os.getenv("GITHUB_TOKEN", "").strip(),
        github_api_url=os.getenv("GITHUB_API_URL", "https://api.github.com").strip(),
        github_org=os.getenv("GITHUB_ORG", "").strip() or None,
        employee_github_logins=set(_split_csv(os.getenv("EMPLOYEE_GITHUB_LOGINS", ""))),
        employee_emails=set(_split_csv(os.getenv("EMPLOYEE_EMAILS", ""))),
        rules_path=rules_path,
        excluded_dirs=_split_csv(os.getenv("EXCLUDED_DIRS", "")),
        report_email=os.getenv("REPORT_EMAIL", "").strip() or None,
        cc_emails=set(_split_csv(os.getenv("CC_EMAILS", ""))),
        smtp_host=os.getenv("SMTP_HOST", "").strip() or None,
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_username=os.getenv("SMTP_USERNAME", "").strip() or None,
        smtp_password=os.getenv("SMTP_PASSWORD", "").strip() or None,
        smtp_from_email=os.getenv("SMTP_FROM_EMAIL", "").strip() or None,
        smtp_use_tls=os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes"},
        signature_template_path=signature_template_path,
        email_signature_name=os.getenv("EMAIL_SIGNATURE_NAME", "").strip(),
        email_signature_designation=os.getenv("EMAIL_SIGNATURE_DESIGNATION", "").strip(),
        email_signature_email=os.getenv("EMAIL_SIGNATURE_EMAIL", "").strip(),
        email_signature_phone=os.getenv("EMAIL_SIGNATURE_PHONE", "").strip(),
        default_repo=os.getenv("DEFAULT_REPO", "").strip() or None,
        default_branch=os.getenv("DEFAULT_BRANCH", "main").strip(),
    )
