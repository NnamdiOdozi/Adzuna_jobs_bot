"""Verify bounded Adzuna searches without credentials or network access."""

import io
import json
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

from jobs_bot.services import fetch_jobs


def _response(rows):
    return io.BytesIO(json.dumps({"results": rows}).encode())


def _error(status):
    return HTTPError(
        "https://api.adzuna.com/private?app_key=synthetic-sensitive-key",
        status,
        "synthetic-sensitive-message",
        {},
        io.BytesIO(b"synthetic-sensitive-body"),
    )


class SearchRequestTests(unittest.TestCase):
    """Keep request use explicit and retry only a rejected large page."""

    def setUp(self):
        """Load the same search settings that production will use."""
        with Path("config.toml").open("rb") as stream:
            self.config = tomllib.load(stream)["search"]
        self.job = {
            "id": "synthetic-job",
            "title": "Graduate Finance Analyst",
            "created": "2026-11-09T06:00:00Z",
            "company": {"display_name": "Example Bank"},
            "location": {"display_name": "London"},
            "redirect_url": "https://example.com/job",
        }

    def _fetch(self, responses):
        with patch("jobs_bot.services.urlopen", side_effect=responses) as request:
            result = fetch_jobs(
                self.config, "synthetic-sensitive-app", "synthetic-sensitive-key"
            )
        return result, request

    def test_combined_search_requests_one_page_once(self):
        """Send all alternatives through what_or in a single request."""
        rows, request = self._fetch([_response([self.job])])
        self.assertEqual(rows, [self.job])
        request.assert_called_once()
        url = urlsplit(request.call_args.args[0].full_url)
        params = parse_qs(url.query)
        self.assertTrue(url.path.endswith("/search/1"))
        self.assertEqual(params["what_or"], [" ".join(self.config["query_terms"])])
        self.assertNotIn("what", params)
        self.assertEqual(params["results_per_page"], ["400"])

    def test_page_rejection_retries_once_with_only_smaller_size(self):
        """Fall back from 400 to 100 without changing the search or exposing keys."""
        with self.assertLogs(level="INFO") as logs:
            rows, request = self._fetch([_error(400), _response([self.job])])
        self.assertEqual(rows, [self.job])
        self.assertEqual(request.call_count, 2)
        params = [
            parse_qs(urlsplit(call.args[0].full_url).query)
            for call in request.call_args_list
        ]
        self.assertEqual(params[0].pop("results_per_page"), ["400"])
        self.assertEqual(params[1].pop("results_per_page"), ["100"])
        self.assertEqual(params[0], params[1])
        output = "\n".join(logs.output)
        self.assertIn("adzuna", output)
        for private in (
            "synthetic-sensitive-key",
            "synthetic-sensitive-app",
            "synthetic-sensitive-message",
            "synthetic-sensitive-body",
            "https://",
        ):
            self.assertNotIn(private, output)

    def test_second_rejection_stops_after_two_requests(self):
        """Do not loop through further page sizes after the fallback fails."""
        with patch(
            "jobs_bot.services.urlopen", side_effect=[_error(400), _error(400)]
        ) as request:
            with self.assertRaises(HTTPError):
                fetch_jobs(self.config, "synthetic-app", "synthetic-key")
        self.assertEqual(request.call_count, 2)

    def test_authentication_quota_and_server_failures_do_not_retry(self):
        """A smaller result page cannot repair credentials, quota or server faults."""
        for status in (401, 403, 410, 429, 500):
            with self.subTest(status=status):
                with patch(
                    "jobs_bot.services.urlopen", side_effect=_error(status)
                ) as request:
                    with self.assertRaises(HTTPError):
                        fetch_jobs(self.config, "synthetic-app", "synthetic-key")
                request.assert_called_once()

    def test_network_failure_does_not_retry(self):
        """Propagate connection failure rather than spending another request."""
        with patch(
            "jobs_bot.services.urlopen", side_effect=URLError("unavailable")
        ) as request:
            with self.assertRaises(URLError):
                fetch_jobs(self.config, "synthetic-app", "synthetic-key")
        request.assert_called_once()

    def test_empty_results_are_accepted_without_more_requests(self):
        """A successful short page is valid and must not cause another search."""
        rows, request = self._fetch([_response([])])
        self.assertEqual(rows, [])
        request.assert_called_once()

    def test_invalid_results_fail_without_size_fallback(self):
        """Reject damaged response data instead of retrying or hiding the failure."""
        with patch(
            "jobs_bot.services.urlopen", side_effect=[_response("invalid-results")]
        ) as request:
            with self.assertRaises(ValueError):
                fetch_jobs(self.config, "synthetic-app", "synthetic-key")
        request.assert_called_once()
