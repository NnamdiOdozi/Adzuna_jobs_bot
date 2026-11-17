"""Verify delivery's test-result gate without GitHub requests or git commands."""

import io
import json
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from jobs_bot.verified_code import main, verify

SHA = "a" * 40


class VerifiedCodeTests(unittest.TestCase):
    """Distinguish verified code, history-only changes and uncertain test results."""

    def invoke(
        self,
        runs=None,
        statuses=(0, 0),
        repository="owner/repo",
        workflow="code-checks.yml",
        changed="",
    ):
        """Return mocked git calls after checking a synthetic workflow result."""
        if runs is None:
            runs = [{"conclusion": "success", "head_sha": SHA, "id": 123}]
        response = io.BytesIO(json.dumps({"workflow_runs": runs}).encode())
        with (
            patch("jobs_bot.verified_code.urlopen", return_value=response) as request,
            patch(
                "jobs_bot.verified_code.subprocess.run",
                side_effect=[
                    Namespace(returncode=code, stdout=changed) for code in statuses
                ],
            ) as git,
            redirect_stdout(io.StringIO()),
        ):
            verify(repository, workflow, "main", "synthetic-token", 15)
        return request, git

    def test_passed_code_and_history_changes_are_accepted(self):
        """Require ancestry and inspect every path changed since tested code."""
        request, git = self.invoke()
        self.assertEqual(request.call_args.kwargs["timeout"], 15)
        self.assertEqual(git.call_count, 2)
        arguments = git.call_args.args[0]
        self.assertIn(SHA, arguments)
        self.assertIn("--name-only", arguments)
        self.assertIn("--no-renames", arguments)
        self.assertIn("-z", arguments)

    def test_only_known_archive_data_bypasses_gate(self):
        """Archived reports can grow, but code or arbitrary configuration blocks."""
        self.invoke(
            changed="state/seen.json\0archive/123/manifest.json\0"
            "archive/123/job-run-report/email.txt\0"
            "archive/123/ranking-comparison/comparison.md\0"
        )
        for path in (
            "archive/123/run.py",
            "archive/123/config.json",
            "archive/123/job-run-report/config.json",
            "archive/123/job-run-report/email.sh",
            "archive/arbitrary/job-run-report/report.json",
            "jobs_bot/archive_runs.py",
        ):
            with self.subTest(path=path), self.assertRaises(RuntimeError):
                self.invoke(changed=path + "\0")

    def test_missing_pending_or_failed_results_block(self):
        """A skipped, cancelled or unsuccessful suite cannot authorize sending."""
        for conclusion in (None, "failure", "cancelled", "skipped", "timed_out"):
            with self.subTest(conclusion=conclusion), self.assertRaises(RuntimeError):
                self.invoke([{"conclusion": conclusion}])
        with self.assertRaises(RuntimeError):
            self.invoke([])

    def test_docs_skip_retesting_but_model_instructions_do_not(self):
        """Documentation-only pushes cannot block mail or hide live prompt edits."""
        self.invoke(changed="README.md\0docs/RUN_TRAIL.md\0archive/README.md\0")
        for path in (
            "prompts/job_suitability.md",
            ".github/workflows/agentic-ranking.md",
            "docs/example.py",
            "jobs_bot/__main__.py",
        ):
            with self.subTest(path=path), self.assertRaises(RuntimeError):
                self.invoke(changed=path + "\0")

    def test_code_difference_and_git_errors_block(self):
        """Reject changed code, unrelated tested commits and git failures."""
        for statuses in ((1, 0), (128, 0), (0, 1), (0, 128)):
            with self.subTest(statuses=statuses), self.assertRaises(RuntimeError):
                self.invoke(statuses=statuses)

    def test_invalid_inputs_block(self):
        """Reject unsafe endpoint paths and malformed tested commit values."""
        with self.assertRaises(ValueError):
            self.invoke(repository="owner/repo/extra")
        with self.assertRaises(ValueError):
            self.invoke(workflow="../checks.yml")
        with self.assertRaises(ValueError):
            self.invoke([{"conclusion": "success", "head_sha": "invalid"}])

    def test_cli_failure_is_safe_and_success_returns_zero(self):
        """Hide raw service errors and propagate successful verification."""
        argv = [
            "verified_code",
            "--workflow",
            "code-checks.yml",
            "--branch",
            "main",
            "--timeout",
            "15",
        ]
        credentials = {"GITHUB_REPOSITORY": "owner/repo", "GITHUB_TOKEN": "synthetic"}
        for error in (None, RuntimeError("synthetic-private-error")):
            output = io.StringIO()
            with (
                patch("sys.argv", argv),
                patch.dict("os.environ", credentials),
                patch("jobs_bot.verified_code.verify", side_effect=error),
                redirect_stdout(output),
            ):
                self.assertEqual(main(), 1 if error else 0)
            self.assertNotIn("synthetic-private-error", output.getvalue())

    def test_workflows_keep_both_suites_and_gate_delivery(self):
        """Keep the agreed automatic triggers and test commands in version control."""
        checks = Path(".github/workflows/code-checks.yml").read_text()
        daily = Path(".github/workflows/daily-jobs.yml").read_text()
        for required in (
            "  push:",
            "  pull_request:",
            "python -m unittest",
            "node --test cloudflare/worker.test.mjs",
        ):
            self.assertIn(required, checks)
        self.assertIn("python -m jobs_bot.verified_code", daily)
        self.assertLess(
            daily.index("jobs_bot.verified_code"), daily.index("id: search")
        )
        self.assertNotIn("Run tests", daily)
