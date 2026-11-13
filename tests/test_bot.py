"""Verify shortlist delivery without live credentials, requests or email."""

import io
import json
import os
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from jobs_bot.__main__ import _run
from jobs_bot.shortlist import job_keys, select_jobs


def _job(identifier="one", title="Finance Analyst", company="Example Bank"):
    return {
        "id": identifier,
        "title": title,
        "company": {"display_name": company},
        "location": {"display_name": "London"},
        "category": {"tag": "accounting-finance-jobs"},
        "created": "2026-10-24T10:00:00Z",
        "redirect_url": "https://example.com/vacancy",
    }


class BotTests(unittest.TestCase):
    """Exercise the command's delivery and sent-history boundaries."""

    def setUp(self):
        """Give each test an independent configuration and history path."""
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.history = Path(temporary.name) / "seen.json"
        self.delivery = Path(temporary.name) / "delivery.json"
        self.now = datetime(2026, 10, 26, 7, 32)
        self.config = Path(temporary.name) / "config.toml"
        source = Path("config.toml").read_text()
        self.config.write_text(
            source.replace('"state/seen.json"', json.dumps(str(self.history))).replace(
                '"state/delivery.json"', json.dumps(str(self.delivery))
            )
        )
        self.credentials = {
            "ADZUNA_APP_ID": "synthetic-app-id",
            "ADZUNA_API_KEY": "synthetic-api-key",
            "gmail_app_password": "synthetic-password",
            "GMAIL_SENDER": "sender@example.com",
            "email_user": "user@example.com",
            "email_friend": "friend@example.com",
        }

    def _invoke(
        self, jobs, send=False, failure=None, test_send=False, search_failure=None
    ):
        argv = ["jobs_bot", "--config", str(self.config)]
        if send:
            argv.append("--send")
        if test_send:
            argv.append("--test-send")
        output = io.StringIO()
        with (
            patch.dict(os.environ, self.credentials, clear=True),
            patch("sys.argv", argv),
            patch("jobs_bot.__main__.datetime") as clock,
            patch(
                "jobs_bot.__main__.fetch_jobs",
                return_value=jobs,
                side_effect=search_failure,
            ) as fetch,
            patch("jobs_bot.__main__.send_message", side_effect=failure) as deliver,
            redirect_stdout(output),
        ):
            clock.now.return_value = self.now
            _run()
        return fetch, deliver, output.getvalue()

    def test_preview_uses_uppercase_credentials_without_sending(self):
        """Accept the configured names and leave mail and history untouched."""
        self.credentials.pop("gmail_app_password")
        fetch, deliver, output = self._invoke([_job()])
        self.assertEqual(
            fetch.call_args.args[1:], ("synthetic-app-id", "synthetic-api-key")
        )
        deliver.assert_not_called()
        self.assertFalse(self.history.exists())
        self.assertFalse(self.delivery.exists())
        self.assertIn("Finance Analyst", output)
        self.assertNotIn("user@example.com", output)

    def test_jsearch_selection_uses_only_its_key_and_preserves_delivery_rules(self):
        """Preview safely, then save provider-prefixed IDs only after mock delivery."""
        self.config.write_text(
            self.config.read_text().replace(
                'provider = "adzuna"', 'provider = "jsearch"'
            )
        )
        self.credentials.pop("ADZUNA_APP_ID")
        self.credentials.pop("ADZUNA_API_KEY")
        self.credentials["JSEARCH_API_KEY"] = "synthetic-jsearch-key"
        job = _job("jsearch:one", "Graduate Business Analyst")
        job.pop("category")
        job["description"] = "Analyse finance operations."
        unrelated = _job("jsearch:other", "Graduate Gardener")
        with patch(
            "jobs_bot.__main__.fetch_jsearch", return_value=[job, unrelated]
        ) as fetch:
            adzuna, deliver, output = self._invoke([])
            adzuna.assert_not_called()
            deliver.assert_not_called()
            self.assertIn("sourced from JSearch", output)
            self.assertIn(job["title"], output)
            self.assertNotIn(unrelated["title"], output)
            self.assertFalse(self.history.exists())
            _, deliver, _ = self._invoke([], send=True)
            self.assertIn("JSearch", deliver.call_args.args[0]["Subject"])
            self.assertEqual(set(json.loads(self.history.read_text())), job_keys(job))
            self.assertEqual(fetch.call_count, 2)
            self.assertEqual(fetch.call_args.args[1], "synthetic-jsearch-key")

    def test_adzuna_http_error_uses_jsearch_filtering_and_delivery(self):
        """Record the backup's jobs after delivery, without logging HTTP details."""
        job = _job("jsearch:backup", "Graduate Business Analyst")
        job.pop("category")
        job["description"] = "Finance operations."
        error = HTTPError("https://example.com/private", 429, "private", {}, None)
        self.credentials["JSEARCH_API_KEY"] = "synthetic-jsearch-key"
        with (
            patch("jobs_bot.__main__.fetch_jsearch", return_value=[job]) as backup,
            self.assertLogs(level="WARNING") as logs,
        ):
            primary, deliver, _ = self._invoke([], send=True, search_failure=error)
        primary.assert_called_once()
        backup.assert_called_once()
        self.assertIn("JSearch", deliver.call_args.args[0]["Subject"])
        self.assertEqual(set(json.loads(self.history.read_text())), job_keys(job))
        self.assertIn("http_status=429", " ".join(logs.output))
        self.assertNotIn("private", " ".join(logs.output))

    def test_empty_adzuna_response_uses_backup_once(self):
        """An empty primary response can be filled by the backup, even in preview."""
        self.credentials["JSEARCH_API_KEY"] = "synthetic-jsearch-key"
        with patch("jobs_bot.__main__.fetch_jsearch", return_value=[]) as backup:
            primary, deliver, output = self._invoke([])
        primary.assert_called_once()
        backup.assert_called_once()
        deliver.assert_not_called()
        self.assertIn("sourced from JSearch", output)
        self.assertFalse(self.history.exists())

    def test_seen_or_filtered_primary_jobs_trigger_backup(self):
        """Search the backup when the primary has nothing worth emailing."""
        self.credentials["JSEARCH_API_KEY"] = "synthetic-jsearch-key"
        self.history.write_text(json.dumps(sorted(job_keys(_job()))))
        for jobs in ([_job()], [_job("senior", "Senior Finance Manager")]):
            with patch("jobs_bot.__main__.fetch_jsearch", return_value=[]) as backup:
                self._invoke(jobs)
                backup.assert_called_once()

    def test_backup_does_not_mask_non_http_failures(self):
        """Do not hide malformed responses or unrelated runtime failures."""
        with patch("jobs_bot.__main__.fetch_jsearch") as backup:
            for error in (URLError("network"), ValueError("invalid data")):
                with self.assertRaises(type(error)):
                    self._invoke([], search_failure=error)
            backup.assert_not_called()

    def test_no_matches_sends_informative_email_and_records_delivery(self):
        """A completed empty search still informs recipients and the watchdog."""
        self.credentials["JSEARCH_API_KEY"] = "synthetic-jsearch-key"
        with patch("jobs_bot.__main__.fetch_jsearch", return_value=[]) as backup:
            _, deliver, _ = self._invoke([], send=True)
            backup.assert_called_once()
        deliver.assert_called_once()
        message = deliver.call_args.args[0]
        self.assertIn("No matching jobs found today", message.get_content())
        self.assertIn("JSearch", message["Subject"])
        self.assertEqual(json.loads(self.history.read_text()), [])
        self.assertEqual(json.loads(self.delivery.read_text()), ["2026-10-26"])

    def test_failed_backup_sends_failure_notice_without_changing_seen_jobs(self):
        """Record accepted failure notification, but keep the search visibly failed."""
        original = ["id:older"]
        self.history.write_text(json.dumps(original))
        self.credentials["JSEARCH_API_KEY"] = "synthetic-jsearch-key"
        messages = []

        def accept(message, config, password):
            messages.append(message)

        for mode in ("preview", "test", "send"):
            with patch(
                "jobs_bot.__main__.fetch_jsearch",
                side_effect=HTTPError(
                    "https://example.com/private-key", 500, "private error", {}, None
                ),
            ) as backup:
                with self.assertRaisesRegex(RuntimeError, "JSearch API failed"):
                    self._invoke(
                        [],
                        send=mode == "send",
                        test_send=mode == "test",
                        failure=accept,
                    )
                backup.assert_called_once()
            if mode != "send":
                self.assertFalse(self.delivery.exists())
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["To"], "sender@example.com")
        self.assertIn("user@example.com", messages[1]["To"])
        for message in messages:
            self.assertIn("JSearch API failed", message["Subject"])
            self.assertNotIn("No matching jobs found today", message.get_content())
            self.assertNotIn("private", message.get_content())
        self.assertEqual(json.loads(self.delivery.read_text()), ["2026-10-26"])
        self.assertEqual(json.loads(self.history.read_text()), original)
        self.credentials.clear()
        primary, deliver, _ = self._invoke([], send=True)
        primary.assert_not_called()
        deliver.assert_not_called()

    def test_failure_notice_rejected_by_gmail_does_not_record_delivery(self):
        """A notification is not complete until Gmail accepts it."""
        self.credentials["JSEARCH_API_KEY"] = "synthetic-jsearch-key"
        with patch("jobs_bot.__main__.fetch_jsearch", side_effect=TimeoutError()):
            with self.assertRaises(ConnectionError):
                self._invoke([], send=True, failure=ConnectionError("mail failed"))
        self.assertFalse(self.delivery.exists())
        self.assertFalse(self.history.exists())

    def test_disabled_backup_does_not_contact_jsearch(self):
        """Retain deliberate Adzuna-only operation when the fallback is disabled."""
        with patch("jobs_bot.__main__.fetch_jsearch") as backup:
            self.config.write_text(
                self.config.read_text().replace(
                    'fallback_provider = "jsearch"', 'fallback_provider = ""'
                )
            )
            self._invoke([])
            with self.assertRaises(HTTPError):
                self._invoke(
                    [],
                    search_failure=HTTPError(
                        "https://example.com", 401, "failed", {}, None
                    ),
                )
            backup.assert_not_called()

    def test_weekend_normal_sends_skip_before_credentials_or_search(self):
        """Keep Saturday Cloudflare triggers harmless, including forced sends."""
        self.config.write_text(
            self.config.read_text().replace("force_send = false", "force_send = true")
        )
        self.credentials.clear()
        for day in (7, 8):
            with self.subTest(day=day), self.assertLogs(level="INFO") as logs:
                self.now = datetime(2026, 11, day, 6, 30)
                fetch, deliver, _ = self._invoke([_job()], send=True)
                fetch.assert_not_called()
                deliver.assert_not_called()
                self.assertFalse(self.history.exists())
                self.assertFalse(self.delivery.exists())
                self.assertIn("reason=non_send_day", "\n".join(logs.output))

    def test_weekend_preview_and_sender_only_test_remain_available(self):
        """Restrict ordinary delivery without preventing safe weekend testing."""
        self.now = datetime(2026, 11, 7, 6, 30)
        fetch, deliver, _ = self._invoke([_job()])
        fetch.assert_called_once()
        deliver.assert_not_called()
        _, deliver, _ = self._invoke([_job()], test_send=True)
        self.assertEqual(deliver.call_args.args[0]["To"], "sender@example.com")
        self.assertFalse(self.history.exists())
        self.assertFalse(self.delivery.exists())

    def test_friday_and_monday_normal_sends_are_allowed(self):
        """Allow the last weekday and the first weekday after a weekend."""
        for day in (6, 9):
            with self.subTest(day=day):
                self.now = datetime(2026, 11, day, 6, 30)
                _, deliver, _ = self._invoke(
                    [_job(str(day), company=f"Example Bank {day}")], send=True
                )
                deliver.assert_called_once()

    def test_send_saves_history_only_after_gmail_accepts(self):
        """Persist the delivered listing keys after Gmail submission succeeds."""
        job = _job()

        def _accept(message, config, password):
            self.assertFalse(self.history.exists())
            self.assertEqual(password, "synthetic-password")
            self.assertIn("user@example.com", str(message["To"]))
            self.assertIn("friend@example.com", str(message["To"]))
            self.assertEqual(message["From"], "sender@example.com")
            self.assertIsNone(message["Bcc"])

        self._invoke([job], send=True, failure=_accept)
        self.assertEqual(set(json.loads(self.history.read_text())), job_keys(job))
        self.assertEqual(json.loads(self.delivery.read_text()), ["2026-10-26"])

    def test_failed_send_preserves_previous_history(self):
        """Keep earlier sent records unchanged when delivery raises."""
        original = ["id:already-sent"]
        self.history.write_text(json.dumps(original))
        with self.assertRaises(ConnectionError):
            self._invoke([_job()], send=True, failure=ConnectionError("unavailable"))
        self.assertEqual(json.loads(self.history.read_text()), original)
        self.assertFalse(self.delivery.exists())
        _, deliver, _ = self._invoke([_job()], send=True)
        deliver.assert_called_once()

    def test_second_send_skips_search_and_delivery(self):
        """A delayed scheduled send must skip after a manual send that day."""
        self._invoke([_job()], send=True)
        original = self.history.read_text()
        self.credentials.clear()
        with self.assertLogs(level="INFO") as logs:
            fetch, deliver, _ = self._invoke([_job("new")], send=True)
        fetch.assert_not_called()
        deliver.assert_not_called()
        self.assertEqual(self.history.read_text(), original)
        self.assertIn("reason=already_sent", "\n".join(logs.output))

    def test_preview_after_send_still_searches(self):
        """Inspect new jobs without sending or changing the day's record."""
        self._invoke([_job()], send=True)
        original = self.delivery.read_text()
        fetch, deliver, output = self._invoke([_job("new", company="Other Bank")])
        fetch.assert_called_once()
        deliver.assert_not_called()
        self.assertIn("Other Bank", output)
        self.assertEqual(self.delivery.read_text(), original)

    def test_force_send_bypasses_date_but_preserves_vacancy_filter(self):
        """An explicit override permits a test email containing only unseen jobs."""
        self._invoke([_job()], send=True)
        self.config.write_text(
            self.config.read_text().replace("force_send = false", "force_send = true")
        )
        _, deliver, _ = self._invoke(
            [_job(), _job("new", company="Other Bank")], send=True
        )
        deliver.assert_called_once()
        body = deliver.call_args.args[0].get_content()
        self.assertIn("Other Bank", body)
        self.assertNotIn("Example Bank", body)
        self.assertEqual(json.loads(self.delivery.read_text()), ["2026-10-26"])

    def test_test_send_uses_sender_only_after_normal_delivery(self):
        """Testing after a real send cannot contact the friend or consume jobs."""
        self._invoke([_job()], send=True)
        before = (self.history.read_text(), self.delivery.read_text())
        self.credentials.pop("email_user")
        self.credentials.pop("email_friend")
        _, deliver, _ = self._invoke(
            [_job("new", company="Other Bank")], test_send=True
        )
        deliver.assert_called_once()
        message = deliver.call_args.args[0]
        self.assertEqual(message["To"], "sender@example.com")
        self.assertIsNone(message["Cc"])
        self.assertIsNone(message["Bcc"])
        self.assertTrue(message["Subject"].startswith("[TEST]"))
        self.assertIn("Other Bank", message.get_content())
        self.assertEqual((self.history.read_text(), self.delivery.read_text()), before)

    def test_test_send_never_creates_normal_history(self):
        """A test on a fresh checkout leaves both normal history files absent."""
        self._invoke([_job()], test_send=True)
        self.assertFalse(self.history.exists())
        self.assertFalse(self.delivery.exists())

    def test_invalid_delivery_history_blocks_search(self):
        """Do not silently discard a damaged daily-send record."""
        self.delivery.write_text('["invalid-date"]')
        with self.assertRaises(ValueError):
            self._invoke([_job()], send=True)

    def test_empty_recipient_list_prevents_delivery(self):
        """Reject an empty recipient list before searching or sending."""
        self.credentials["email_user"] = ""
        self.credentials["email_friend"] = ""
        with self.assertRaisesRegex(ValueError, "recipient"):
            self._invoke([_job()], send=True)

    def test_next_run_filters_sent_ids_and_probable_reposts(self):
        """Suppress both a delivered ID and a new ID for the same role."""
        self._invoke([_job()], send=True)
        self.now = datetime(2026, 10, 27, 2, 30)
        _, deliver, _ = self._invoke(
            [_job(), _job("repost"), _job("different", company="Other Bank")], send=True
        )
        message = deliver.call_args.args[0]
        self.assertIn("Other Bank", message.get_content())
        self.assertNotIn("Example Bank", message.get_content())
        self.assertEqual(
            json.loads(self.delivery.read_text()), ["2026-10-26", "2026-10-27"]
        )

    def test_recruiter_title_is_excluded_but_other_employer_is_retained(self):
        """Reject recruiter titles without collapsing roles at different firms."""
        config = {
            "category": "accounting-finance-jobs",
            "title_keywords": ["finance"],
            "exclude_title_keywords": ["recruiter"],
            "shortlist_size": 20,
        }
        jobs = [
            _job(),
            _job("two", company="Other Bank"),
            _job("three", title="Finance RECRUITER"),
        ]
        selected = select_jobs(jobs, set(), config)
        self.assertEqual({job["id"] for job in selected}, {"one", "two"})

    def test_send_filters_irrelevant_and_senior_roles_before_email_and_history(self):
        """Only finance roles surviving seniority rules reach delivery/history."""
        junior = _job("junior", "Junior Finance Analyst")
        _, deliver, _ = self._invoke(
            [
                _job("senior", "Senior Finance Analyst"),
                _job("recruitment", "Entry-Level Executive Search Consultant"),
                _job("barista", "Bank Barista"),
                junior,
            ],
            send=True,
        )
        body = deliver.call_args.args[0].get_content()
        self.assertIn("Junior Finance Analyst", body)
        self.assertNotIn("Senior Finance Analyst", body)
        self.assertNotIn("Executive Search", body)
        self.assertNotIn("Barista", body)
        self.assertEqual(set(json.loads(self.history.read_text())), job_keys(junior))


if __name__ == "__main__":
    unittest.main()
