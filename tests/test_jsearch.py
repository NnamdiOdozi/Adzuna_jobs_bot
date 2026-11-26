"""Verify JSearch requests and normalization without network access."""

import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from jobs_bot.jsearch import fetch_jsearch


class JSearchTests(unittest.TestCase):
    """Keep paid searches bounded and reject unusable provider records."""

    def setUp(self):
        """Prepare a synthetic provider response and search settings."""
        self.config = dict(
            base_url="https://api.openwebninja.com/jsearch/search-v2",
            query="graduate finance jobs in London, UK",
            country="gb",
            language="en",
            num_pages=8,
            date_posted="week",
            radius=50,
            timeout_seconds=30,
        )
        self.job = dict(
            job_id="abc",
            job_title="Graduate Analyst",
            employer_name="Bank",
            job_location="London",
            job_apply_link="https://example.com/apply",
            job_description="Finance work",
            job_posted_at_datetime_utc="2026-11-10T09:00:00Z",
        )

    def _fetch(self, payload):
        with patch("jobs_bot.jsearch.build_opener") as opener:
            request = opener.return_value.open
            request.return_value = io.StringIO(json.dumps(payload))
            rows = fetch_jsearch(self.config, "synthetic-key")
        return rows, request

    def test_one_request_normalizes_jobs_without_following_cursor(self):
        """Preserve provenance and request all pages in one charged call."""
        self.job.update(
            job_min_salary=30000, job_max_salary=40000, job_salary_period="YEAR"
        )
        rows, request = self._fetch({"data": {"jobs": [self.job], "cursor": "next"}})
        request.assert_called_once()
        sent = request.call_args.args[0]
        self.assertEqual(parse_qs(urlsplit(sent.full_url).query)["num_pages"], ["8"])
        self.assertEqual(parse_qs(urlsplit(sent.full_url).query)["radius"], ["50"])
        self.assertEqual(sent.get_header("X-api-key"), "synthetic-key")
        row = rows[0]
        self.assertEqual(row["id"], "jsearch:abc")
        self.assertEqual(row["source"], "JSearch")
        self.assertEqual(row["company"], {"display_name": "Bank"})
        self.assertEqual(row["location"], {"display_name": "London"})
        self.assertEqual(row["created"], self.job["job_posted_at_datetime_utc"])
        self.assertEqual(row["redirect_url"], self.job["job_apply_link"])
        self.assertEqual((row["salary_min"], row["salary_max"]), (30000, 40000))
        self.assertEqual(row["salary_currency"], "currency not supplied")
        self.assertEqual(row["salary_period"], "YEAR")
        self.assertNotIn("category", row)

    def test_bad_records_and_response_shapes_fail(self):
        """Reject incomplete records and unsafe application links."""
        payloads = [{}, {"data": []}, {"data": {"jobs": {}}}]
        for field in (
            "job_id",
            "job_title",
            "employer_name",
            "job_location",
            "job_apply_link",
        ):
            payloads.append({"data": {"jobs": [dict(self.job, **{field: ""})]}})
        payloads.append(
            {"data": {"jobs": [dict(self.job, job_apply_link="file:///tmp/job")]}}
        )
        for payload in payloads:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self._fetch(payload)

    def test_invalid_request_is_rejected_before_open(self):
        """Protect the key destination and bound requested page counts."""
        for change in (
            {"base_url": "https://example.com/search"},
            {"base_url": "http://api.openwebninja.com/jsearch/search-v2"},
            *({"num_pages": n} for n in (0, 21, True, "8")),
        ):
            with (
                self.subTest(change=change),
                patch("jobs_bot.jsearch.build_opener") as opener,
            ):
                with self.assertRaises(ValueError):
                    fetch_jsearch(dict(self.config, **change), "synthetic-key")
                opener.return_value.open.assert_not_called()

    def test_rate_limit_does_not_retry(self):
        """Let the caller handle a rejected search without further charges."""
        with patch("jobs_bot.jsearch.build_opener") as opener:
            request = opener.return_value.open
            request.side_effect = HTTPError(
                self.config["base_url"], 429, "limit", {}, None
            )
            with self.assertRaises(HTTPError):
                fetch_jsearch(self.config, "synthetic-key")
            request.assert_called_once()

    def test_transient_failures_retry_twice_with_configured_spacing(self):
        """Recover on attempt three without real waiting or paid requests."""
        self.config["retry_delays_seconds"] = [120, 120]
        with (
            patch("jobs_bot.jsearch.build_opener") as opener,
            patch("jobs_bot.jsearch.time.sleep") as sleep,
        ):
            opener.return_value.open.side_effect = [
                HTTPError("https://example.com", 503, "unavailable", {}, None),
                TimeoutError(),
                io.StringIO(json.dumps({"data": {"jobs": []}})),
            ]
            self.assertEqual(fetch_jsearch(self.config, "synthetic"), [])
        self.assertEqual(opener.return_value.open.call_count, 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [120, 120])

    def test_authentication_failure_does_not_retry(self):
        """Avoid repeating requests which need credential or subscription changes."""
        self.config["retry_delays_seconds"] = [120, 120]
        with (
            patch("jobs_bot.jsearch.build_opener") as opener,
            patch("jobs_bot.jsearch.time.sleep") as sleep,
        ):
            opener.return_value.open.side_effect = HTTPError(
                "https://example.com", 403, "forbidden", {}, None
            )
            with self.assertRaises(HTTPError):
                fetch_jsearch(self.config, "synthetic")
        self.assertEqual(opener.return_value.open.call_count, 1)
        sleep.assert_not_called()

    def test_retries_are_exhausted_without_a_fourth_request(self):
        """Bound downtime to the configured attempts."""
        self.config["retry_delays_seconds"] = [120, 120]
        with (
            patch("jobs_bot.jsearch.build_opener") as opener,
            patch("jobs_bot.jsearch.time.sleep") as sleep,
        ):
            opener.return_value.open.side_effect = TimeoutError()
            with self.assertRaises(TimeoutError):
                fetch_jsearch(self.config, "synthetic")
        self.assertEqual(opener.return_value.open.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_incomplete_vacancy_does_not_discard_valid_jobs_or_retry(self):
        """A single missing field must not prevent the remaining jobs reaching Jev."""
        malformed = {**self.job, "job_location": None}
        with self.assertLogs(level="WARNING") as logs:
            rows, request = self._fetch({"data": {"jobs": [malformed, self.job]}})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "jsearch:abc")
        request.assert_called_once()
        self.assertIn("job_location", " ".join(logs.output))
        self.assertIn("row=1", " ".join(logs.output))

    def test_bad_links_and_text_leave_complete_vacancies_available(self):
        """Reject unusable rows visibly without inventing their missing data."""
        rows, request = self._fetch(
            {
                "data": {
                    "jobs": [
                        {**self.job, "job_apply_link": "javascript:bad"},
                        {**self.job, "job_description": []},
                        self.job,
                    ]
                }
            }
        )
        self.assertEqual(len(rows), 1)
        request.assert_called_once()

    def test_all_incomplete_rows_fail_instead_of_claiming_no_matches(self):
        """An unusable nonempty provider response is still a search failure."""
        with self.assertRaisesRegex(ValueError, "no usable vacancies"):
            self._fetch({"data": {"jobs": [{"job_id": "incomplete"}]}})

    def test_invalid_optional_salary_metadata_becomes_unknown(self):
        """Non-string optional pay metadata must not crash the salary screen."""
        from jobs_bot.screening import screen_jobs

        self.job.update(job_salary_currency=123, job_salary_period=[])
        rows, _ = self._fetch({"data": {"jobs": [self.job]}})
        self.assertEqual(rows[0]["salary_currency"], "currency not supplied")
        self.assertEqual(rows[0]["salary_period"], "")
        self.assertEqual(
            len(screen_jobs(rows, {"max_salary_gbp": 50000}, "jsearch")), 1
        )
