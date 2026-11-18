"""Exercise permanent evidence preservation without GitHub or repository writes."""

import io
import json
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile, ZipInfo

from jobs_bot.archive_runs import (
    _api,
    _members,
    _request_settings,
    archive_data_path,
    main,
    preserve_run,
)


def zipped(files):
    """Build a tiny in-memory Actions artifact from supplied members."""
    result = io.BytesIO()
    with ZipFile(result, "w") as archive:
        for path, data in files:
            archive.writestr(path, data)
    return result.getvalue()


class ArchiveTests(unittest.TestCase):
    """Keep source identity, ZIP safety and immutable archive contents together."""

    def setUp(self):
        """Create a temporary destination and a completed synthetic source run."""
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "archive"
        self.run = {
            "id": 123,
            "created_at": "2026-11-18T06:30:45Z",
            "head_repository": {"full_name": "owner/repo"},
            "head_branch": "main",
            "path": ".github/workflows/daily-jobs.yml",
            "event": "workflow_dispatch",
            "status": "completed",
            "head_sha": "a" * 40,
            "conclusion": "failure",
            "run_attempt": 1,
        }
        self.artifact = {"id": 456, "name": "job-run-report", "expired": False}
        self.payload = zipped([("report.json", '{"status":"failed"}')])

    def invoke(self, artifacts=None):
        """Preserve synthetic source metadata and downloaded ZIP bytes."""
        if artifacts is None:
            artifacts = [self.artifact]
        with patch(
            "jobs_bot.archive_runs._api",
            side_effect=[self.run, {"artifacts": artifacts}, self.payload],
        ) as api:
            result = preserve_run("owner/repo", "123", "main", self.root)
        return result, api

    def test_failed_source_is_preserved_and_retry_is_identical(self):
        """Preserve failure evidence with exact hashes and no changing timestamps."""
        target, _ = self.invoke()
        before = {p.name: p.read_bytes() for p in target.rglob("*") if p.is_file()}
        manifest = json.loads((target / "manifest.json").read_text())
        self.assertEqual(manifest["source_commit"], "a" * 40)
        self.assertEqual(manifest["conclusion"], "failure")
        self.assertIn("job-run-report/report.json", manifest["sha256"])
        self.invoke()
        after = {p.name: p.read_bytes() for p in target.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_conflicting_existing_file_is_never_overwritten(self):
        """A rerun cannot silently replace a different version of evidence."""
        target, _ = self.invoke()
        self.payload = zipped([("report.json", '{"status":"changed"}')])
        with self.assertRaises(ValueError):
            self.invoke()
        self.assertEqual(
            (target / "job-run-report/report.json").read_text(), '{"status":"failed"}'
        )

    def test_creation_time_uses_london_summer_and_winter_time(self):
        """Name the source run, rather than the later archive job, in UK time."""
        for created, expected in (
            ("2026-11-18T06:30:45Z", "2026-11-18_06-30-45_GMT"),
            ("2026-07-18T05:30:45Z", "2026-07-18_06-30-45_BST"),
        ):
            with self.subTest(created=created):
                self.run["created_at"] = created
                self.root = Path(self.temporary.name) / expected
                target, _ = self.invoke()
                self.assertEqual(target.name, expected)
                manifest = json.loads((target / "manifest.json").read_text())
                self.assertEqual(manifest["source_run_id"], "123")
                self.assertEqual(manifest["source_created_at"], created)
                self.assertEqual(manifest["archive_timezone"], "Europe/London")

    def test_same_second_collision_never_merges_distinct_runs(self):
        """Keep human time first, adding an ID only when two run times collide."""
        first, _ = self.invoke()
        self.run["id"] = 999
        with patch(
            "jobs_bot.archive_runs._api",
            side_effect=[self.run, {"artifacts": [self.artifact]}, self.payload],
        ):
            second = preserve_run("owner/repo", "999", "main", self.root)
        self.assertEqual(second.name, first.name + "--999")
        self.assertTrue(archive_data_path(f"archive/{second.name}/manifest.json"))
        self.assertFalse(archive_data_path(f"archive/{second.name}/run.py"))

    def test_legacy_manifest_and_folder_remain_usable(self):
        """Retry old archives without changing their original evidence bytes."""
        target, _ = self.invoke()
        manifest_path = target / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        for field in ("source_created_at", "source_local_time", "archive_timezone"):
            manifest.pop(field)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        original = manifest_path.read_bytes()
        target.rename(self.root / "123")
        retried, _ = self.invoke()
        self.assertEqual(retried.name, "123")
        self.assertEqual((retried / "manifest.json").read_bytes(), original)

    def test_cli_passes_the_named_directory_to_the_commit_step(self):
        """Stage the actual timestamp folder rather than guessing from its run ID."""
        output = Path(self.temporary.name) / "outputs"
        target = Path("archive/2026-11-18_06-30-45_GMT")
        with (
            patch(
                "sys.argv",
                [
                    "archive",
                    "--repository",
                    "o/r",
                    "--run-id",
                    "123",
                    "--branch",
                    "main",
                ],
            ),
            patch("jobs_bot.archive_runs.preserve_run", return_value=target),
            patch.dict("os.environ", {"GITHUB_OUTPUT": str(output)}),
            patch("sys.stdout", new_callable=io.StringIO),
        ):
            self.assertEqual(main(), 0)
        self.assertEqual(output.read_text(), f"directory={target}\n")

    def test_source_provenance_and_ids_are_enforced(self):
        """Reject foreign, unfinished, non-default and unrelated workflow runs."""
        for field, value in (
            ("id", 999),
            ("head_repository", {"full_name": "foreign/repo"}),
            ("head_branch", "feature"),
            ("path", ".github/workflows/untrusted.yml"),
            ("event", "pull_request"),
            ("status", "in_progress"),
            ("head_sha", "bad"),
        ):
            original = self.run[field]
            self.run[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.invoke()
            self.run[field] = original
        for run_id in ("../123", "--help", "0", "123\n"):
            with self.subTest(run_id=run_id), self.assertRaises(ValueError):
                preserve_run("owner/repo", run_id, "main", self.root)

    def test_only_named_artifacts_are_downloaded(self):
        """Runner logs and unknown artifacts never enter the permanent archive."""
        target, api = self.invoke([{"name": "raw-runner-logs"}, self.artifact])
        self.assertEqual(api.call_count, 3)
        self.assertFalse((target / "raw-runner-logs").exists())
        self.artifact["expired"] = True
        with self.assertRaises(ValueError):
            self.invoke()

    def test_bad_zip_members_and_non_json_are_rejected(self):
        """Do not extract traversal, executables, arbitrary text or symbolic links."""
        symlink = ZipInfo("report.json")
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        for path, value in (
            ("../report.json", "{}"),
            ("/report.json", "{}"),
            ("nested/report.json", "{}"),
            ("report.py", "print('bad')"),
            ("logs.txt", "private runner logs"),
            ("config.json", "{}"),
            ("report.json", "invalid"),
            ("report.json", '{"value": NaN}'),
            (symlink, "outside"),
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                _members("job-run-report", zipped([(path, value)]))

    def test_symlink_destination_is_rejected(self):
        """Trusted filenames cannot escape through existing filesystem links."""
        self.root.mkdir()
        (self.root / "123").symlink_to(self.temporary.name, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.invoke()

    def test_email_body_and_only_known_leafnames_are_accepted(self):
        """Plain email bodies are evidence, while headers and config are excluded."""
        files = _members("job-run-report", zipped([("email.txt", "Body only")]))
        self.assertEqual(files["email.txt"], b"Body only")
        self.assertTrue(archive_data_path("archive/123/job-run-report/email.txt"))
        self.assertFalse(archive_data_path("archive/123/config.toml"))

    def test_workflow_has_separate_authority_and_trusted_checkout(self):
        """Archive publication stays independent from email and model execution."""
        workflow = Path(".github/workflows/archive-runs.yml").read_text()
        for required in (
            "workflow_run:",
            "workflow_dispatch:",
            "actions: read",
            "contents: write",
            "ref: ${{ github.event.repository.default_branch }}",
            "git pull --rebase",
            "for attempt in 1 2 3",
            "python -m jobs_bot.archive_runs",
            "queue: max",
            "cancel-in-progress: false",
            "github.event.workflow_run.head_branch == "
            "github.event.repository.default_branch",
        ):
            self.assertIn(required, workflow)
        for forbidden in ("secrets.", "--force", "[skip ci]", "send_message"):
            self.assertNotIn(forbidden, workflow)

    def test_cli_errors_do_not_print_private_api_responses(self):
        """A failed API call exposes its exception type without response content."""
        with (
            patch(
                "sys.argv",
                [
                    "archive",
                    "--repository",
                    "o/r",
                    "--run-id",
                    "123",
                    "--branch",
                    "main",
                ],
            ),
            patch(
                "jobs_bot.archive_runs.preserve_run", side_effect=ValueError("private")
            ),
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            self.assertEqual(main(), 1)
        self.assertNotIn("private", output.getvalue())

    def test_cli_reports_only_known_validation_reasons(self):
        """An operator can distinguish rejected provenance from a broken download."""
        for error, expected in (
            (ValueError("Invalid source run ID"), "Invalid source run ID"),
            (ValueError("untrusted-response-text"), None),
            (UnicodeDecodeError("utf-8", b"private", 0, 1, "private"), None),
        ):
            with (
                patch(
                    "sys.argv",
                    [
                        "archive",
                        "--repository",
                        "o/r",
                        "--run-id",
                        "123",
                        "--branch",
                        "main",
                    ],
                ),
                patch("jobs_bot.archive_runs.preserve_run", side_effect=error),
                patch("sys.stdout", new_callable=io.StringIO) as output,
            ):
                self.assertEqual(main(), 1)
            if expected:
                self.assertIn(expected, output.getvalue())
            else:
                self.assertNotIn("Archive validation failed:", output.getvalue())

    def test_read_retries_timeout_and_server_error_then_succeeds(self):
        """Transient GitHub read failures have short, bounded recovery waits."""
        for failure in (
            subprocess.TimeoutExpired("gh", 45),
            subprocess.CalledProcessError(1, "gh", stderr=b"gh: private (HTTP 502)"),
        ):
            with (
                patch(
                    "jobs_bot.archive_runs.subprocess.run",
                    side_effect=[
                        failure,
                        failure,
                        SimpleNamespace(stdout=b'{"id":123}'),
                    ],
                ) as request,
                patch("jobs_bot.archive_runs.time.sleep") as sleep,
                patch("sys.stdout", new_callable=io.StringIO) as output,
            ):
                self.assertEqual(_api("o/r", "actions/runs/123"), {"id": 123})
            self.assertEqual(request.call_count, 3)
            self.assertEqual([call.args[0] for call in sleep.call_args_list], [1, 2])
            self.assertNotIn("private", output.getvalue())

    def test_read_retry_exhaustion_and_permanent_errors(self):
        """Never retry authentication or expiry errors; stop after three timeouts."""
        for failure, attempts in (
            (subprocess.TimeoutExpired("gh", 45), 3),
            (subprocess.CalledProcessError(1, "gh", stderr=b"(HTTP 401)"), 1),
            (subprocess.CalledProcessError(1, "gh", stderr=b"(HTTP 403)"), 1),
            (subprocess.CalledProcessError(1, "gh", stderr=b"(HTTP 410)"), 1),
        ):
            with (
                patch(
                    "jobs_bot.archive_runs.subprocess.run", side_effect=failure
                ) as request,
                patch("jobs_bot.archive_runs.time.sleep") as sleep,
                patch("sys.stdout", new_callable=io.StringIO),
                self.assertRaises(type(failure)),
            ):
                _api("o/r", "actions/runs/123")
            self.assertEqual(request.call_count, attempts)
            self.assertEqual(sleep.call_count, attempts - 1)

    def test_bad_provenance_does_not_retry_or_download(self):
        """A manual branch backfill explains the policy after one metadata read."""
        self.run["head_branch"] = "experiment"
        with patch("jobs_bot.archive_runs._api", return_value=self.run) as request:
            with self.assertRaisesRegex(
                ValueError, "branch experiments are not archived"
            ):
                preserve_run("owner/repo", "123", "main", self.root)
        self.assertEqual(request.call_count, 1)

    def test_request_settings_reject_invalid_values(self):
        """Require positive integer waits and exactly one delay between attempts."""
        defaults = {
            "request_timeout_seconds": 45,
            "request_attempts": 3,
            "retry_delays_seconds": [1, 2],
        }
        for key, value in (
            ("request_timeout_seconds", 0),
            ("request_timeout_seconds", True),
            ("request_attempts", -1),
            ("request_attempts", False),
            ("retry_delays_seconds", [1]),
            ("retry_delays_seconds", [0, 2]),
            ("retry_delays_seconds", [True, 2]),
        ):
            with (
                self.subTest(key=key, value=value),
                patch(
                    "jobs_bot.archive_runs.tomllib.loads",
                    return_value={"permanent_archive": {**defaults, key: value}},
                ),
                self.assertRaisesRegex(ValueError, "Invalid permanent archive"),
            ):
                _request_settings()

    def test_api_uses_configured_timeout_and_delay(self):
        """Changing request settings changes the actual GitHub read boundary."""
        with (
            patch("jobs_bot.archive_runs._request_settings", return_value=(9, 2, [4])),
            patch(
                "jobs_bot.archive_runs.subprocess.run",
                side_effect=[
                    subprocess.TimeoutExpired("gh", 9),
                    SimpleNamespace(stdout=b"{}"),
                ],
            ) as request,
            patch("jobs_bot.archive_runs.time.sleep") as sleep,
            patch("sys.stdout", new_callable=io.StringIO),
        ):
            self.assertEqual(_api("o/r", "actions/runs/123"), {})
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args.kwargs["timeout"], 9)
        sleep.assert_called_once_with(4)
