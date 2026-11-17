"""Check numbered vacancy reports and public email evidence entirely offline."""

import copy
import json
import os
import unittest
from email.message import EmailMessage
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from jobs_bot.run_reports import main, record_run
from jobs_bot.snapshots import create_snapshot, save_snapshot


def _job(identifier):
    return {
        "id": identifier,
        "title": f"Finance analyst {identifier}",
        "description": "Full vacancy description",
        "redirect_url": f"https://example.com/jobs/{identifier}?source=listing",
        "company": {"display_name": "Example Bank"},
        "location": {"display_name": "London"},
        "salary_min": 30000,
        "salary_max": 40000,
        "salary_currency": "GBP",
        "salary_period": "YEAR",
        "salary_is_predicted": "0",
    }


class RunReportTests(unittest.TestCase):
    """Exercise saved artifacts without providers, models or email submission."""

    def setUp(self):
        """Place all generated evidence in a temporary directory."""
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.directory = self.root / "report"
        self.config = {
            "report": {"enabled": True, "directory": str(self.directory)},
            "archive": {"directory": str(self.root / "archive")},
            "ranking": {
                "method": "jev",
                "receipt_directory": str(self.root / "receipts"),
            },
            "search": {"api_key": "synthetic-private-config"},
            "jsearch": {},
            "email": {
                "timezone": "Europe/London",
                "password": "synthetic-private-config",
            },
        }
        self.jobs = [_job(identifier) for identifier in ("a", "b", "c")]
        self.selected = [self.jobs[2], self.jobs[0]]
        self.records = [
            {
                "receipt": {
                    "assessments": [
                        {
                            "id": "c",
                            "suitability": "strong_fit",
                            "probabilities": {
                                "strong_fit": 0.7,
                                "possible_fit": 0.2,
                                "not_fit": 0.1,
                            },
                        },
                        {"id": "b", "suitability": "not_fit"},
                    ]
                }
            }
        ]
        self.message = EmailMessage()
        self.message["Subject"] = "Today's vacancies"
        self.message["From"] = "private-sender@example.com"
        self.message["To"] = "private-recipient@example.com"
        self.message.set_content("Prepared vacancy bulletin.\n")
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def _record(self, state="prepared", config=None):
        return record_run(
            self.jobs,
            self.selected,
            self.config if config is None else config,
            self.records,
            date="2026-11-17",
            mode="test",
            state=state,
            message=self.message,
        )

    def _read(self, name):
        return json.loads((self.directory / f"{name}.json").read_text())

    def test_orders_cross_links_and_full_details_survive_without_mutation(self):
        """Keep fetched numbering distinct from the ranked email order."""
        original = copy.deepcopy((self.jobs, self.selected, self.records, self.config))
        self.assertTrue(self._record())
        candidates, shortlist = self._read("candidates"), self._read("shortlist")
        self.assertEqual(
            [(j["id"], j["fetched_index"]) for j in candidates],
            [("a", 1), ("b", 2), ("c", 3)],
        )
        self.assertEqual(
            [(j["id"], j["email_index"], j["fetched_index"]) for j in shortlist],
            [("c", 1, 3), ("a", 2, 1)],
        )
        self.assertEqual(
            [(r["id"], r["fetched_index"]) for r in self._read("assessments")],
            [("c", 3), ("b", 2)],
        )
        for saved in (candidates[2], shortlist[0]):
            for field in self.jobs[2]:
                self.assertEqual(saved[field], self.jobs[2][field])
        self.assertEqual(
            (self.jobs, self.selected, self.records, self.config), original
        )
        self.assertEqual(self._read("report")["fetched"], 3)
        self.assertEqual(self._read("report")["selected"], 2)

    def test_exact_email_body_excludes_headers_and_private_config(self):
        """Publish the prepared text while withholding recipient and secret settings."""
        self.assertTrue(self._record())
        self.assertEqual(
            (self.directory / "email.txt").read_text(), self.message.get_content()
        )
        self.assertEqual(
            {p.name for p in self.directory.iterdir()},
            {
                "report.json",
                "candidates.json",
                "assessments.json",
                "shortlist.json",
                "email.txt",
                "summary.md",
            },
        )
        for path in self.directory.iterdir():
            content = path.read_text()
            for private in (
                "private-sender@example.com",
                "private-recipient@example.com",
                "synthetic-private-config",
                "From:",
                "To:",
            ):
                self.assertNotIn(private, content)

    def test_markdown_escapes_vacancy_text_and_retains_clickable_link(self):
        """Stop vacancy titles from creating images, HTML or extra table cells."""
        self.jobs[2]["title"] = (
            "![advert](https://example.com/pixel) <b>Finance</b> | role"
        )
        self.assertTrue(self._record())
        summary = (self.directory / "summary.md").read_text()
        self.assertNotIn("![advert]", summary)
        self.assertNotIn("<b>", summary)
        self.assertIn(r"!\[advert\]", summary)
        self.assertIn("&lt;b&gt;Finance&lt;/b&gt;", summary)
        self.assertIn(r"\| role", summary)
        self.assertIn("](<https://example.com/jobs/c?source=listing>)", summary)

    def test_delivery_states_distinguish_preparation_acceptance_and_history(self):
        """Never describe preparation or an uncertain submission as accepted."""
        expected = {
            "prepared": "Email prepared; acceptance has not been recorded",
            "accepted": "Gmail accepted the message; history completion not recorded",
            "accepted_history_saved": (
                "Gmail accepted the message; delivery history saved"
            ),
            "submission_failed_or_unknown": (
                "Submission failed or acceptance is unknown"
            ),
        }
        for state, wording in expected.items():
            with self.subTest(state=state):
                self.assertTrue(self._record(state))
                self.assertEqual(self._read("report")["state"], state)
                summary = (self.directory / "summary.md").read_text()
                self.assertIn(wording, summary)
                self.assertIn("not proof of inbox delivery", summary)

    def test_missing_or_disabled_report_configuration_has_no_side_effect(self):
        """Older configuration must not trigger candidate processing or writes."""
        with patch("jobs_bot.run_reports.create_snapshot") as create:
            for config in ({}, {"report": {"enabled": False}}):
                self.assertFalse(self._record(config=config))
            create.assert_not_called()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_write_failure_returns_false_without_disclosing_exception_text(self):
        """An unavailable report destination must not interrupt email handling."""
        with (
            patch(
                "jobs_bot.run_reports.Path.write_text",
                side_effect=PermissionError("synthetic-private-config"),
            ),
            self.assertLogs(level="WARNING") as logs,
        ):
            self.assertFalse(self._record())
        self.assertNotIn("synthetic-private-config", " ".join(logs.output))
        self.assertIn("PermissionError", " ".join(logs.output))

    def _snapshot(self, jobs, provider, run_id, time):
        snapshot = create_snapshot(
            jobs,
            provider,
            self.config,
            (),
            run_id=run_id,
            captured_at=f"2026-11-17T07:00:{time:02d}+00:00",
        )
        save_snapshot(snapshot, self.config["archive"]["directory"])

    def test_current_run_counts_provider_batches_once_and_ignores_other_runs(self):
        """Recover all raw batches without doubling their combined snapshot."""
        self._snapshot([self.jobs[2]], "jsearch", "123", 2)
        self._snapshot(self.jobs, "combined", "123", 3)
        self._snapshot(self.jobs[:2], "adzuna", "123", 1)
        self._snapshot([_job("unrelated")], "adzuna", "122", 0)
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "123"}):
            self.assertTrue(self._record())
        self.assertEqual(
            [job["id"] for job in self._read("candidates")], ["a", "b", "c"]
        )
        self.assertEqual(self._read("report")["fetched"], 3)

    def test_actions_fallback_publishes_available_evidence_after_failure(self):
        """Publish captured vacancies and receipts even if email was never prepared."""
        self._snapshot([self.jobs[2]], "adzuna", "123", 1)
        receipts = Path(self.config["ranking"]["receipt_directory"])
        receipts.mkdir()
        (receipts / "ranking-test.json").write_text(json.dumps(self.records[0]))
        config_path = self.root / "config.toml"
        config_path.write_text("")
        summary_path = self.root / "actions-summary.md"
        with (
            patch.dict(
                os.environ,
                {
                    "GITHUB_RUN_ID": "123",
                    "RUN_OUTCOME": "failure",
                    "RUN_MODE": "live",
                    "GITHUB_STEP_SUMMARY": str(summary_path),
                },
            ),
            patch("sys.argv", ["run_reports", "--config", str(config_path)]),
            patch("jobs_bot.run_reports.tomllib.load", return_value=self.config),
        ):
            main()
        self.assertEqual(self._read("report")["state"], "failed")
        self.assertEqual(self._read("report")["mode"], "live")
        self.assertEqual(self._read("report")["fetched"], 1)
        self.assertEqual(self._read("assessments")[0]["fetched_index"], 1)
        self.assertEqual(
            summary_path.read_text(), (self.directory / "summary.md").read_text()
        )
        self.assertIn("Run failed", summary_path.read_text())
        self.assertFalse((self.directory / "email.txt").exists())
