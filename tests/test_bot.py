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

from jobs_bot.__main__ import _run
from jobs_bot.shortlist import job_keys, select_jobs


def _job(identifier="one", title="Finance Analyst", company="Example Bank"):
    return {
        "id": identifier,
        "title": title,
        "company": {"display_name": company},
        "location": {"display_name": "London"},
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

    def _invoke(self, jobs, send=False, failure=None):
        argv = ["jobs_bot", "--config", str(self.config)]
        if send:
            argv.append("--send")
        output = io.StringIO()
        with (
            patch.dict(os.environ, self.credentials, clear=True),
            patch("sys.argv", argv),
            patch("jobs_bot.__main__.datetime") as clock,
            patch("jobs_bot.__main__.fetch_jobs", return_value=jobs) as fetch,
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


if __name__ == "__main__":
    unittest.main()
