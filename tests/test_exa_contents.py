"""Check Exa enrichment offline without API charges or email delivery."""

import io
import json
import unittest
from unittest.mock import patch

from jobs_bot.exa_contents import enrich_jobs
from jobs_bot.shortlist import job_keys


def vacancy(identifier="1", url="https://example.com/job"):
    """Build a minimal normalized vacancy."""
    return {
        "id": identifier,
        "title": "Finance Graduate",
        "description": "Short",
        "company": {"display_name": identifier},
        "location": {"display_name": "London"},
        "redirect_url": url,
    }


class ExaTests(unittest.TestCase):
    """Exercise extraction and its safe fallback boundary."""

    def setUp(self):
        """Verify the documented extraction boundary offline."""
        self.config = {"exa": {"enabled": True, "max_pages": 1, "timeout_seconds": 10}}

    def test_malformed_url_cannot_prevent_fallback(self):
        """An unparsable advert link must not stop ranking the original vacancy."""
        job = vacancy(url="https://[broken")
        with patch("jobs_bot.exa_contents.urlopen") as request:
            self.assertEqual(enrich_jobs([job], (), self.config), [job])
        request.assert_not_called()

    def test_disabled_and_seen_do_not_request(self):
        """Verify the documented extraction boundary offline."""
        job = vacancy()
        with patch("jobs_bot.exa_contents.urlopen") as request:
            self.assertEqual(enrich_jobs([job], (), {}), [job])
            self.assertEqual(enrich_jobs([job], job_keys(job), self.config), [job])
        request.assert_not_called()

    def test_enrichment_preserves_original_and_caps_urls(self):
        """Verify the documented extraction boundary offline."""
        jobs = [vacancy(), vacancy("2", "https://example.com/second")]
        response = {
            "results": [
                {"url": jobs[0]["redirect_url"], "text": "Longer complete vacancy text"}
            ]
        }
        with (
            patch.dict("os.environ", {"EXA_API_KEY": "offline-placeholder"}),
            patch("jobs_bot.exa_contents.urlopen") as request,
        ):
            request.return_value.__enter__.return_value = io.BytesIO(
                json.dumps(response).encode()
            )
            result = enrich_jobs(jobs, (), self.config)
        sent = request.call_args.args[0]
        self.assertEqual(sent.full_url, "https://api.exa.ai/contents")
        self.assertEqual(json.loads(sent.data)["urls"], [jobs[0]["redirect_url"]])
        self.assertEqual(result[0]["exa_status"], "enriched")
        self.assertEqual(result[0]["original_description"], "Short")
        self.assertEqual(jobs[0]["description"], "Short")
        self.assertNotIn("exa_status", result[1])

    def test_service_failure_keeps_original(self):
        """Verify the documented extraction boundary offline."""
        with (
            patch.dict("os.environ", {"EXA_API_KEY": "offline-placeholder"}),
            patch("jobs_bot.exa_contents.urlopen", side_effect=TimeoutError),
        ):
            result = enrich_jobs([vacancy()], (), self.config)
        self.assertEqual(result[0]["description"], "Short")
        self.assertEqual(result[0]["exa_status"], "unavailable")

    def test_unrelated_or_short_text_is_not_used(self):
        """Verify the documented extraction boundary offline."""
        response = {
            "results": [
                {"url": "https://elsewhere.com/job", "text": "Wrong"},
                {"url": "https://example.com/job", "text": "No"},
            ]
        }
        with (
            patch.dict("os.environ", {"EXA_API_KEY": "offline-placeholder"}),
            patch("jobs_bot.exa_contents.urlopen") as request,
        ):
            request.return_value.__enter__.return_value = io.BytesIO(
                json.dumps(response).encode()
            )
            result = enrich_jobs([vacancy()], (), self.config)
        self.assertEqual(result[0]["description"], "Short")
        self.assertEqual(result[0]["exa_status"], "original_longer")
