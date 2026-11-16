"""Verify candidate archives stay sanitized, intact and outside delivery decisions."""

import io
import json
import os
import tomllib
import unittest
from contextlib import redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import HTTPError

from jobs_bot.__main__ import _run
from jobs_bot.snapshots import (
    create_snapshot,
    load_snapshot,
    record_snapshot,
    save_snapshot,
)


def _job():
    return {
        "id": "one",
        "title": "Senior Finance Manager",
        "description": "Finance role",
        "company": {"display_name": "Example Bank", "private_contact": "omit-me"},
        "location": {"display_name": "London", "area": ["UK", "London"]},
        "category": {"tag": "accounting-finance-jobs", "label": "Finance"},
        "created": "2026-11-16T07:00:00Z",
        "redirect_url": "https://example.com/job",
        "salary_min": 30000,
        "salary_max": 40000,
        "salary_currency": "GBP",
        "salary_period": "YEAR",
        "salary_is_predicted": "0",
        "source": "Adzuna",
        "request_headers": {"Authorization": "omit-me"},
        "secret": "omit-me",
    }


class SnapshotTests(unittest.TestCase):
    """Check archive safety, round trips and integrity failures offline."""

    def setUp(self):
        """Create an independent archive destination and synthetic settings."""
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.config = {
            "archive": {"enabled": True, "directory": str(self.directory)},
            "search": {
                "provider": "adzuna",
                "query_terms": ["finance"],
                "base_url": "omit-me",
                "api_key": "omit-me",
            },
            "jsearch": {"query": "finance", "api_key": "omit-me"},
            "email": {"sender": "omit-me", "password": "omit-me"},
        }

    def _snapshot(self):
        return create_snapshot(
            [_job()],
            "adzuna",
            self.config,
            {"old"},
            run_id="123",
            commit="abc",
            captured_at=datetime(2026, 11, 16, tzinfo=UTC),
        )

    def test_round_trip_preserves_allowed_fields_only(self):
        """Keep replay information while dropping arbitrary nested and config data."""
        snapshot = self._snapshot()
        path = save_snapshot(snapshot, self.directory)
        self.assertEqual(load_snapshot(path), snapshot)
        self.assertNotIn("omit-me", path.read_text())
        self.assertEqual(snapshot["jobs"][0]["description"], "Finance role")
        self.assertEqual(snapshot["jobs"][0]["salary_min"], 30000)
        self.assertEqual(snapshot["seen"], ["old"])
        self.assertEqual(snapshot["metadata"], {"run_id": "123", "commit": "abc"})
        self.assertEqual(snapshot["config"]["search"]["query_terms"], ["finance"])
        self.assertEqual(list(self.directory.glob("*.tmp")), [])

    def test_attempts_have_unique_ids_even_with_same_run_and_time(self):
        """Avoid overwriting primary and backup attempts in the same run."""
        first = self._snapshot()
        second = self._snapshot()
        self.assertNotEqual(first["snapshot_id"], second["snapshot_id"])
        save_snapshot(first, self.directory)
        save_snapshot(second, self.directory)
        self.assertEqual(len(list(self.directory.glob("*.json"))), 2)

    def test_tampering_is_rejected(self):
        """Reject altered descriptions even when the document still parses."""
        path = save_snapshot(self._snapshot(), self.directory)
        payload = json.loads(path.read_text())
        payload["jobs"][0]["description"] = "Changed"
        path.write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            load_snapshot(path)

    def test_schema_and_types_are_checked(self):
        """Reject unsupported versions and invalid structures before persistence."""
        for key, value in (
            ("schema_version", 2),
            ("schema_version", True),
            ("jobs", {}),
            ("seen", [3]),
            ("metadata", {"run_id": 7, "commit": "abc"}),
            ("captured_at", "2026-11-16"),
            ("snapshot_id", "../../outside"),
            ("config", {"search": {}, "jsearch": {}, "email": {}}),
        ):
            with self.subTest(key=key, value=value):
                snapshot = self._snapshot()
                snapshot[key] = value
                with self.assertRaises(ValueError):
                    save_snapshot(snapshot, self.directory)
        with self.assertRaises(ValueError):
            create_snapshot(
                [{**_job(), "title": {"private": "value"}}], "adzuna", self.config, []
            )

    def test_empty_response_is_a_valid_snapshot(self):
        """Represent a successful zero-result fetch without inventing vacancies."""
        snapshot = create_snapshot([], "jsearch", self.config, [])
        self.assertEqual(
            load_snapshot(save_snapshot(snapshot, self.directory))["jobs"], []
        )

    def test_explicit_filename_is_confined_to_destination(self):
        """Honor manual export names without accepting paths outside the archive."""
        snapshot = self._snapshot()
        path = save_snapshot(snapshot, self.directory, filename="requested.json")
        self.assertEqual(path, self.directory / "requested.json")
        self.assertEqual(load_snapshot(path), snapshot)
        for filename in ("../outside.json", "/tmp/outside.json", "snapshot.db"):
            with self.subTest(filename=filename), self.assertRaises(ValueError):
                save_snapshot(snapshot, self.directory, filename=filename)

    def test_canonical_hash_ignores_dictionary_order(self):
        """Allow reformatting without treating unchanged content as tampered data."""
        snapshot = self._snapshot()
        reordered = dict(reversed(list(snapshot.items())))
        self.assertEqual(
            load_snapshot(save_snapshot(reordered, self.directory)), snapshot
        )

    def test_save_failure_warns_without_error_details(self):
        """Keep archive diagnostics from blocking delivery or exposing error text."""
        with (
            patch("jobs_bot.snapshots.save_snapshot", side_effect=OSError("omit-me")),
            self.assertLogs(level="WARNING") as logs,
        ):
            self.assertIsNone(record_snapshot([_job()], "adzuna", self.config, []))
        self.assertNotIn("omit-me", " ".join(logs.output))
        self.assertIn("archive_failed", " ".join(logs.output))

    def test_disabled_archive_does_no_work(self):
        """Make archiving optional for older configurations and deliberate opt-out."""
        with patch("jobs_bot.snapshots.create_snapshot") as create:
            self.assertIsNone(record_snapshot([], "adzuna", {}, []))
            self.config["archive"]["enabled"] = False
            self.assertIsNone(record_snapshot([], "adzuna", self.config, []))
            create.assert_not_called()


class SnapshotIntegrationTests(unittest.TestCase):
    """Capture each successful provider attempt before semantic selection."""

    def setUp(self):
        """Use temporary paths and synthetic credentials for every command run."""
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.config_path = self.directory / "config.toml"
        self.config_path.write_text("")
        self.config = tomllib.loads(Path("config.toml").read_text())
        # Archive tests isolate capture ordering from optional paid ranking/top-up.
        self.config["ranking"]["method"] = "rules"
        self.config["search"]["jsearch_top_up_threshold"] = 0
        self.config["history"] = {
            "path": str(self.directory / "seen.json"),
            "delivery_path": str(self.directory / "delivery.json"),
        }
        self.archive = self.directory / "archive"
        self.config["archive"] = {"enabled": True, "directory": str(self.archive)}
        self.credentials = {
            "ADZUNA_APP_ID": "synthetic",
            "ADZUNA_API_KEY": "synthetic",
            "JSEARCH_API_KEY": "synthetic",
            "GMAIL_SENDER": "sender@example.com",
            "email_user": "reader@example.com",
        }

    def _run(self, primary, backup, selections):
        with (
            patch.dict(os.environ, self.credentials, clear=True),
            patch("sys.argv", ["jobs_bot", "--config", str(self.config_path)]),
            patch("jobs_bot.__main__.tomllib.load", return_value=self.config),
            patch("jobs_bot.__main__.fetch_jobs", side_effect=primary),
            patch("jobs_bot.__main__.fetch_jsearch", side_effect=backup),
            patch("jobs_bot.__main__.select_jobs", side_effect=selections),
            patch("jobs_bot.__main__.send_message") as send,
            redirect_stdout(io.StringIO()),
        ):
            _run()
        send.assert_not_called()
        return [load_snapshot(path) for path in self.archive.glob("*.json")]

    def test_rejected_primary_and_fallback_captured_before_filter(self):
        """Retain raw rejected candidates and both successful source attempts."""
        counts = []

        def select(jobs, seen, config):
            counts.append(len(list(self.archive.glob("*.json"))))
            return []

        snapshots = self._run(lambda *args: [_job()], lambda *args: [], select)
        self.assertEqual(counts, [1, 2])
        by_provider = {item["provider"]: item for item in snapshots}
        self.assertEqual(
            by_provider["adzuna"]["jobs"][0]["title"], "Senior Finance Manager"
        )
        self.assertEqual(by_provider["jsearch"]["jobs"], [])
        self.assertFalse(Path(self.config["history"]["path"]).exists())

    def test_empty_primary_captured_before_empty_fallback(self):
        """Archive successful empty fetches even when fallback happens immediately."""
        snapshots = self._run(lambda *args: [], lambda *args: [], lambda *args: [])
        self.assertEqual(
            {item["provider"] for item in snapshots}, {"adzuna", "jsearch"}
        )
        self.assertTrue(all(item["jobs"] == [] for item in snapshots))

    def test_failed_primary_has_only_successful_backup_snapshot(self):
        """Do not label an unsuccessful HTTP fetch as a successful empty response."""
        error = HTTPError("https://example.com", 503, "unavailable", {}, io.BytesIO())
        snapshots = self._run(error, lambda *args: [], lambda *args: [])
        self.assertEqual([item["provider"] for item in snapshots], ["jsearch"])

    def test_successful_primary_needs_no_backup(self):
        """Save the primary candidate set without changing provider selection."""
        snapshots = self._run(
            lambda *args: [_job()],
            AssertionError("Unexpected fallback"),
            lambda jobs, *args: jobs,
        )
        self.assertEqual([item["provider"] for item in snapshots], ["adzuna"])

    def test_explicit_jsearch_records_its_success(self):
        """Capture JSearch when it is chosen directly rather than as fallback."""
        self.config["search"]["provider"] = "jsearch"
        snapshots = self._run(
            AssertionError("Unexpected primary fetch"),
            lambda *args: [_job()],
            lambda jobs, *args: jobs,
        )
        self.assertEqual([item["provider"] for item in snapshots], ["jsearch"])

    def test_failed_backup_does_not_fabricate_success(self):
        """Keep the primary archive when the fallback request fails."""
        with self.assertRaisesRegex(RuntimeError, "preview only"):
            self._run(lambda *args: [], TimeoutError(), lambda *args: [])
        snapshots = [load_snapshot(path) for path in self.archive.glob("*.json")]
        self.assertEqual([item["provider"] for item in snapshots], ["adzuna"])

    def test_archive_write_failure_preserves_normal_preview(self):
        """Complete preview when the diagnostic archive cannot be written."""
        with patch("jobs_bot.snapshots.save_snapshot", side_effect=PermissionError()):
            snapshots = self._run(
                lambda *args: [_job()], lambda *args: [], lambda *args: []
            )
        self.assertEqual(snapshots, [])
