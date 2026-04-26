from __future__ import annotations

import argparse
import sys
from pathlib import Path

from code_validator.config.settings import load_settings
from code_validator.github.client import GitHubClient
from code_validator.rules.rules_store import RuleStore
from code_validator.services.commit_validation_service import (
    CommitValidationService,
    EmployeeRegistry,
)
from code_validator.services.email_service import EmailService
from code_validator.services.reporting_service import HtmlReportService
from code_validator.services.signature_service import SignatureContext, SignatureTemplateService
from code_validator.validators.text_validators import (
    InnerDelimiterSpacingValidator,
    LineLengthValidator,
    RegexRuleValidator,
    TrailingWhitespaceValidator,
)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser( description = "Validate latest commit on a GitHub branch." )
    parser.add_argument( "--repo", help = "Repository in owner/name format." )
    parser.add_argument( "--branch", help = "Branch to inspect." )
    parser.add_argument( "--env-file", help = "Optional path to .env file." )
    parser.add_argument(
        "--only",
        help = "Comma-separated directories to check. If specified, only these directories will be reviewed.",
    )
    return parser

def run() -> int:
    args = build_parser().parse_args()
    settings = load_settings( env_path = args.env_file )

    repo = args.repo or settings.default_repo
    branch = args.branch or settings.default_branch

    if not repo:
        print( "ERROR: repository is required via --repo or DEFAULT_REPO.", file = sys.stderr )
        return 2

    if not settings.github_token:
        print( "ERROR: GITHUB_TOKEN is required for private repository access.", file = sys.stderr )
        return 2

    store = RuleStore( settings.rules_path )
    if not store.exists():
        print(
            f"ERROR: rules file not found at {store.path}. Create/update rules.json manually.",
            file = sys.stderr,
        )
        return 2

    ruleset = store.load()

    github_client = GitHubClient( token = settings.github_token, api_url = settings.github_api_url )
    employee_registry = EmployeeRegistry(
        github_client = github_client,
        org = settings.github_org,
        employee_logins = settings.employee_github_logins,
        employee_emails = settings.employee_emails,
    )

    only_dirs = tuple(
        item.strip() for item in args.only.split( "," )
        if item.strip()
    ) if args.only else None

    service = CommitValidationService(
        github_client = github_client,
        validators = [
            LineLengthValidator(),
            TrailingWhitespaceValidator(),
            RegexRuleValidator(),
            InnerDelimiterSpacingValidator(),
        ],
        excluded_dirs = settings.excluded_dirs,
        only_dirs = only_dirs,
    )

    result = service.validate_latest_commit(
        repo = repo,
        branch = branch,
        ruleset = ruleset,
    )

    is_employee = employee_registry.is_employee_identity( result.author_login, result.author_email )

    signature_service = SignatureTemplateService(
        template_path = settings.signature_template_path,
        context = SignatureContext(
            name = settings.email_signature_name,
            designation = settings.email_signature_designation,
            email = settings.email_signature_email,
            phone = settings.email_signature_phone,
        ),
    )
    signature_html = signature_service.render()

    report_service = HtmlReportService( output_dir = Path( "reports" ) )
    report = report_service.generate(
        result = result,
        is_employee = is_employee,
        signature_html = signature_html,
    )
    print( f"Report: {report.html_path}" )

    if settings.report_email:
        if not settings.smtp_host or not settings.smtp_from_email:
            print(
                "WARNING: REPORT_EMAIL is set, but SMTP_HOST/SMTP_FROM_EMAIL is missing. "
                "Skipping email delivery.",
                file = sys.stderr,
            )
        else:
            html_content = report.html_path.read_text( encoding = "utf-8" )
            subject = (
                f"[Code Validator] FAILED - {repo}@{branch}"
                if ( result.violations or not is_employee )
                else f"[Code Validator] PASSED - {repo}@{branch}"
            )
            mailer = EmailService(
                host = settings.smtp_host,
                port = settings.smtp_port,
                username = settings.smtp_username,
                password = settings.smtp_password,
                from_email = settings.smtp_from_email,
                use_tls = settings.smtp_use_tls,
            )
            try:
                mailer.send_html(
                    to_email = settings.report_email,
                    cc_emails = sorted( settings.cc_emails ),
                    subject = subject,
                    html_content = html_content,
                    signature_html = signature_html,
                )
                if settings.cc_emails:
                    print(
                        "Email report sent to: "
                        f"{settings.report_email} (cc: {', '.join(sorted(settings.cc_emails))})"
                    )
                else:
                    print( f"Email report sent to: {settings.report_email}" )
            except Exception as exc:  # noqa: BLE001
                print(
                    "WARNING: Email delivery failed, but validation/report generation completed. "
                    f"Reason: {exc}",
                    file = sys.stderr,
                )

    print( f"Repo: {result.repo}" )
    print( f"Branch: {result.branch}" )
    print( f"Commit: {result.commit_sha}" )
    print( f"Author login: {result.author_login}" )
    print( f"Author email: {result.author_email}" )
    print( f"Employee commit: {'yes' if is_employee else 'no'}" )
    print( f"Checked files: {result.checked_files}" )
    print( f"Skipped files: {result.skipped_files}" )

    if not is_employee:
        print( "FAILED: latest commit author is not recognized as an employee." )
        return 1

    if result.violations:
        print(
            "FAILED: guideline violations detected "
            f"({len(result.violations)} total). See HTML report for details."
        )
        return 1

    print( "PASSED: commit author is employee and all configured rules passed." )
    return 0
