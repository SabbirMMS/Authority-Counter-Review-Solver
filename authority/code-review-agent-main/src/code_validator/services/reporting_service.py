from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import quote

from code_validator.github.models import Violation
from code_validator.services.commit_validation_service import ValidationResult


@dataclass(frozen=True)
class ReportArtifact:
    html_path: Path


class HtmlReportService:
    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def generate(
        self,
        result: ValidationResult,
        is_employee: bool,
        signature_html: str = "",
    ) -> ReportArtifact:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        safe_repo = result.repo.replace("/", "_")
        safe_branch = result.branch.replace("/", "_")
        filename = f"validation-report-{safe_repo}-{safe_branch}-{stamp}.html"
        path = self._output_dir / filename

        grouped = self._group_by_file(result.violations)
        severity_color = "#c1121f" if result.violations or not is_employee else "#1f7a1f"
        status_text = "FAILED" if result.violations or not is_employee else "PASSED"
        repo_url = f"https://github.com/{quote(result.repo, safe='/')}"

        html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Code Validation Report</title>
  <style>
    :root {{
      --bg-1: #f6efe9;
      --bg-2: #e5edf7;
      --card: rgba(255, 255, 255, 0.84);
      --text: #13263a;
      --muted: #44617d;
      --line: rgba(79, 116, 150, 0.24);
      --accent: #0f5ea8;
      --danger: #c1121f;
      --ok: #1f7a1f;
      --chip: #f2f8ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Space Grotesk", "Avenir Next", "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(80rem 80rem at -10% -10%, #f8d7c7 0%, rgba(248, 215, 199, 0) 40%),
        radial-gradient(80rem 80rem at 110% -20%, #d5e4f7 0%, rgba(213, 228, 247, 0) 44%),
        linear-gradient(135deg, var(--bg-1), var(--bg-2));
      min-height: 100vh;
    }}
    .wrap {{ max-width: 1200px; margin: 28px auto; padding: 0 16px 24px; }}
    .card {{
      background: var(--card);
      backdrop-filter: blur(8px);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 20px;
      box-shadow: 0 14px 34px rgba(16, 39, 61, 0.12);
    }}
    .topbar {{ display: flex; flex-wrap: wrap; justify-content: space-between; gap: 10px; align-items: center; }}
    .title {{ margin: 0; font-size: 22px; letter-spacing: 0.01em; }}
    .status {{ display: inline-flex; align-items: center; padding: 7px 12px; border-radius: 999px; color: #fff; font-weight: 700; letter-spacing: 0.03em; background: {severity_color}; }}
    .repo-link {{ color: var(--accent); text-decoration: none; font-weight: 700; }}
    .repo-link:hover {{ text-decoration: underline; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; margin-top: 16px; }}
    .metric {{ border: 1px solid var(--line); border-radius: 12px; padding: 10px; background: var(--chip); }}
    .metric .label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; }}
    .metric .value {{ margin-top: 6px; font-size: 18px; font-weight: 700; }}
    h2 {{ margin: 22px 0 12px; font-size: 18px; }}
    .file-card {{ margin-bottom: 14px; border: 1px solid var(--line); border-radius: 14px; overflow: hidden; background: #fff; }}
    .file-accordion {{ border-bottom: 1px solid var(--line); }}
    .file-accordion:last-child {{ border-bottom: none; }}
    .file-summary {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 10px 12px;
      background: #f4f9ff;
      cursor: pointer;
      list-style: none;
    }}
    .file-summary::-webkit-details-marker {{ display: none; }}
    .summary-left {{ display: flex; align-items: center; gap: 8px; min-width: 0; }}
    .summary-right {{ display: flex; align-items: center; gap: 8px; flex-shrink: 0; }}
    .chev {{ color: var(--muted); font-weight: 700; width: 12px; }}
    .file-accordion[open] .chev {{ transform: rotate(90deg); }}
    .count-chip {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      background: #eef5ff;
      border: 1px solid #cadef4;
      color: #24496b;
      font-size: 12px;
      font-weight: 700;
    }}
    .file-table-wrap {{ padding: 0 10px 10px; }}
    .path {{ font-family: "IBM Plex Mono", "Cascadia Code", monospace; font-size: 12px; word-break: break-all; }}
    .violations-table {{ width: 100%; border-collapse: collapse; }}
    .violations-table th, .violations-table td {{ padding: 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; font-size: 13px; }}
    .violations-table th {{ background: #f9fcff; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #335475; }}
    .violations-table tr:last-child td {{ border-bottom: none; }}
    .line-chip {{ display: inline-block; padding: 2px 8px; border-radius: 999px; background: #eef5ff; border: 1px solid #cadef4; font-weight: 700; }}
    .open-link {{ color: var(--accent); text-decoration: none; font-weight: 700; }}
    .open-link:hover {{ text-decoration: underline; }}
    .muted {{ color: var(--muted); }}
    .signature-section {{ margin-top: 24px; padding-top: 18px; border-top: 1px solid var(--line); overflow-x: auto; }}
    .signature-section table {{ width: auto; border-collapse: collapse; }}
    @media (max-width: 680px) {{
      .title {{ font-size: 19px; }}
      .violations-table th, .violations-table td {{ padding: 8px; font-size: 12px; }}
    }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"card\">
      <div class=\"topbar\">
        <h1 class=\"title\">Engineering Code Validation Report</h1>
        <div class=\"status\">{status_text}</div>
      </div>
      <p class=\"muted\">Repository: <a class=\"repo-link\" target=\"_blank\" rel=\"noopener noreferrer\" href=\"{escape(repo_url, quote=True)}\">{escape(result.repo)}</a></p>
      <div class=\"grid\">
        <div class=\"metric\"><div class=\"label\">Branch</div><div class=\"value\">{escape(result.branch)}</div></div>
        <div class=\"metric\"><div class=\"label\">Commit</div><div class=\"value path\">{escape(result.commit_sha[:12])}</div></div>
        <div class=\"metric\"><div class=\"label\">Employee Commit</div><div class=\"value\">{'Yes' if is_employee else 'No'}</div></div>
        <div class=\"metric\"><div class=\"label\">Checked Files</div><div class=\"value\">{result.checked_files}</div></div>
        <div class=\"metric\"><div class=\"label\">Skipped Files</div><div class=\"value\">{result.skipped_files}</div></div>
        <div class=\"metric\"><div class=\"label\">Violations</div><div class=\"value\">{len(result.violations)}</div></div>
      </div>

      <h2>Violation Details</h2>
      {self._render_tables(result.repo, result.commit_sha, grouped)}
      <p class=\"muted\">Generated at {datetime.now(timezone.utc).isoformat()}</p>
      {self._render_signature(signature_html)}
    </div>
  </div>
</body>
</html>
"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        return ReportArtifact(html_path=path)

    @staticmethod
    def _group_by_file(violations: list[Violation]) -> dict[str, list[Violation]]:
        grouped: dict[str, list[Violation]] = {}
        for item in violations:
            grouped.setdefault(item.path, []).append(item)
        return grouped

    def _render_tables(self, repo: str, commit_sha: str, grouped: dict[str, list[Violation]]) -> str:
        if not grouped:
            return "<p class=\"muted\">No guideline violations found.</p>"

        chunks: list[str] = []
        for path, items in sorted(grouped.items()):
            rows = []
            for v in items:
                line = str(v.line_number) if v.line_number is not None else "-"
                link = self._github_file_link(repo, commit_sha, path, v.line_number)
                rows.append(
                    "<tr>"
                    f"<td>{escape(v.rule_id)}</td>"
                    f"<td><span class=\"line-chip\">{line}</span></td>"
                    f"<td>{escape(v.message)}</td>"
                    f"<td><a class=\"open-link\" target=\"_blank\" rel=\"noopener noreferrer\" href=\"{escape(link, quote=True)}\">Open</a></td>"
                    "</tr>"
                )
            table = (
                "<div class=\"file-card\">"
                "<details class=\"file-accordion\">"
                "<summary class=\"file-summary\">"
                "<div class=\"summary-left\">"
                "<span class=\"chev\">&#9656;</span>"
                f"<span class=\"path\">{escape(path)}</span>"
                "</div>"
                "<div class=\"summary-right\">"
                f"<span class=\"count-chip\">{len(items)} violations</span>"
                f"<a class=\"open-link\" target=\"_blank\" rel=\"noopener noreferrer\" href=\"{escape(self._github_file_link(repo, commit_sha, path, None), quote=True)}\">Open File</a>"
                "</div>"
                "</summary>"
                "<div class=\"file-table-wrap\">"
                "<table class=\"violations-table\"><thead><tr><th>Rule ID</th><th>Line</th><th>Message</th><th>GitHub</th></tr></thead><tbody>"
                + "".join(rows)
                + "</tbody></table>"
                "</div>"
                "</details>"
                "</div>"
            )
            chunks.append(table)
        return "".join(chunks)

    @staticmethod
    def _render_signature(signature_html: str) -> str:
        if not signature_html.strip():
            return ""
        return (
            "<div class=\"signature-section\">"
            "<!--EMAIL_SIGNATURE-->"
            + signature_html
            + "</div>"
        )

    @staticmethod
    def _github_file_link(repo: str, git_ref: str, file_path: str, line_number: int | None) -> str:
        quoted_repo = quote(repo, safe="/")
        quoted_ref = quote(git_ref, safe="")
        quoted_path = quote(file_path, safe="/")
        anchor = f"#L{line_number}" if line_number else ""
        return f"https://github.com/{quoted_repo}/blob/{quoted_ref}/{quoted_path}{anchor}"
