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
