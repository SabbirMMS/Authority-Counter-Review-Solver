from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from counter_solver.cli import run


def scripted_input(responses: list[str]):
    iterator = iter(responses)

    def _input(prompt: str = "") -> str:
        try:
            return next(iterator)
        except StopIteration as exc:
            raise AssertionError(f"Unexpected prompt: {prompt}") from exc

    return _input


def latest_report(report_dir: Path) -> dict:
    report_path = sorted(report_dir.glob("counter-solver-report-*.json"))[-1]
    return json.loads(report_path.read_text(encoding="utf-8"))


class CliWorkflowTests(unittest.TestCase):
    def test_folder_mode_respects_child_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            (root / "root.py").write_text("print('root')  \n", encoding="utf-8")
            (root / "alpha").mkdir()
            (root / "alpha" / "a.js").write_text("const a = 1;  \n", encoding="utf-8")
            (root / "alpha" / "child").mkdir()
            (root / "alpha" / "child" / "b.js").write_text("const b = 2;  \n", encoding="utf-8")
            (root / "beta").mkdir()
            (root / "beta" / "c.py").write_text("value = 1  \n", encoding="utf-8")
            report_dir = Path(tmp) / "reports"

            exit_code = run(
                ["--project", str(root), "--mode", "folder", "--preview-only"],
                input_func=scripted_input(["n", "i", "s", "r"]),
                output_stream=io.StringIO(),
                report_dir=report_dir,
            )

            report = latest_report(report_dir)
            self.assertEqual(exit_code, 0)
            self.assertEqual(report["scanned_files"], 2)
            paths = {item["path"] for item in report["files"]}
            self.assertEqual(paths, {"alpha/a.js", "beta/c.py"})

    def test_manual_mode_only_writes_selected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            first = root / "a.js"
            second = root / "b.js"
            first.write_text("const a = 1;  \n", encoding="utf-8")
            second.write_text("const b = 2;  \n", encoding="utf-8")
            report_dir = Path(tmp) / "reports"

            exit_code = run(
                ["--project", str(root), "--mode", "manual"],
                input_func=scripted_input(["1", "all", "y"]),
                output_stream=io.StringIO(),
                report_dir=report_dir,
            )

            report = latest_report(report_dir)
            self.assertEqual(exit_code, 1)
            self.assertEqual(first.read_text(encoding="utf-8"), "const a = 1;\n")
            self.assertEqual(second.read_text(encoding="utf-8"), "const b = 2;  \n")
            self.assertEqual(report["changed_files"], 1)
            self.assertEqual(report["remaining_violations"], 1)

    def test_bulk_mode_reduces_violations_and_keeps_advisories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            app = root / "app.js"
            app.write_text(
                (
                    "if ( value ) return total;  \n"
                    "const result = combine( alpha, beta, gamma, delta, epsilon, zeta, eta, theta, "
                    "iota, kappa, lambda, mu, nu, xi, omicron );\n"
                ),
                encoding="utf-8",
            )
            report_dir = Path(tmp) / "reports"

            exit_code = run(
                ["--project", str(root), "--mode", "bulk"],
                input_func=scripted_input(["y"]),
                output_stream=io.StringIO(),
                report_dir=report_dir,
            )

            report = latest_report(report_dir)
            updated = app.read_text(encoding="utf-8")

            self.assertEqual(exit_code, 1)
            self.assertEqual(report["changed_files"], 1)
            self.assertGreater(report["original_violations"], report["remaining_violations"])
            self.assertGreater(report["remaining_violations"], 0)
            self.assertNotIn("  \n", updated)
            self.assertTrue(any(len(line) <= 120 for line in updated.splitlines()))


if __name__ == "__main__":
    unittest.main()
