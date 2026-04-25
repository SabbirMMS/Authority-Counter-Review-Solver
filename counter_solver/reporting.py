from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from counter_solver.models import RunReport


def write_report(report_dir: Path, report: RunReport) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = report_dir / f"counter-solver-report-{stamp}.json"
    report.report_path = str(path)
    path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return path
