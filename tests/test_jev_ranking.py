"""Verify Jev boundaries offline, without credentials, searches or email."""

import copy
import io
import json
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from jobs_bot.__main__ import _select
from jobs_bot.jev_ranking import rank_jobs
from jobs_bot.model_ranking import RankingFailure


class JevRankingTests(unittest.TestCase):
    """Test complete probabilities, bounded requests and normal-workflow wiring."""

    def setUp(self):
        """Load public settings and create three distinct accounting adverts."""
        with Path("config.toml").open("rb") as stream:
            self.config = tomllib.load(stream)
        self.jobs = [
            {
                "id": name,
                "title": "Finance " + name,
                "company": {"display_name": name},
                "location": {"display_name": "London"},
                "description": "Graduate accounting role",
            }
            for name in ("one", "two", "three")
        ]

    def response(self, request, **kwargs):
        """Return probabilities for precisely the questions in a mocked request."""
        payload = json.loads(request.data)
        answers = {
            name: {
                "type": "choice",
                "choice": "unknown" if name.startswith("salary_") else "strong_fit",
                "probabilities": {
                    label: float(
                        label
                        == ("unknown" if name.startswith("salary_") else "strong_fit")
                    )
                    for label in question["criteria"]
                },
            }
            for name, question in payload["questions"].items()
        }
        return io.StringIO(
            json.dumps(
                {
                    "model": self.config["jev"]["model"],
                    "answers": answers,
                    "usage": {"input_tokens": 100, "output_tokens": 10},
                }
            )
        )

    @patch("jobs_bot.jev_ranking.build_opener")
    def test_batches_preserve_ids_and_probabilities(self, opener):
        """Map short question IDs back to adverts across multiple batches."""
        self.config["jev"]["batch_size"] = 2
        self.config["ranking"]["max_description_chars"] = 5
        opener.return_value.open.side_effect = self.response
        selected, receipt = rank_jobs(self.jobs, set(), self.config, api_key="fake")
        self.assertEqual(len(selected), 3)
        self.assertEqual(receipt["calls"], 2)
        self.assertEqual(receipt["token_usage"]["input_tokens"], 200)
        self.assertEqual(
            {r["id"] for r in receipt["assessments"]}, {"one", "two", "three"}
        )
        self.assertTrue(all("probabilities" in row for row in receipt["assessments"]))
        self.assertEqual(set(receipt["truncation"]), {"one", "two", "three"})

    @patch("jobs_bot.jev_ranking.build_opener")
    def test_http_failure_stops_without_retry_or_secret_text(self, opener):
        """Keep service failures visible without echoing sensitive error text."""
        opener.return_value.open.side_effect = HTTPError(
            "https://example.com", 429, "PRIVATE", {}, None
        )
        with self.assertRaises(RankingFailure) as raised:
            rank_jobs(self.jobs, set(), self.config, api_key="fake")
        self.assertEqual(opener.return_value.open.call_count, 1)
        self.assertEqual(raised.exception.diagnostics["http_status"], 429)
        self.assertNotIn("PRIVATE", str(raised.exception))

    @patch("jobs_bot.jev_ranking.build_opener")
    def test_missing_answer_cannot_be_a_successful_ranking(self, opener):
        """Reject partial provider responses without silently losing vacancies."""

        def incomplete(request, **kwargs):
            response = json.load(self.response(request))
            response["answers"].pop("job_0")
            return io.StringIO(json.dumps(response))

        opener.return_value.open.side_effect = incomplete
        with self.assertRaises(RankingFailure):
            rank_jobs(self.jobs, set(), self.config, api_key="fake")
        self.assertEqual(opener.return_value.open.call_count, 1)

    @patch("jobs_bot.jev_ranking.build_opener")
    def test_invalid_probabilities_are_not_ranked(self, opener):
        """Reject numeric garbage before it can influence vacancy selection."""

        def invalid(request, **kwargs):
            response = json.load(self.response(request))
            response["answers"]["job_0"]["probabilities"]["strong_fit"] = float("nan")
            return io.StringIO(json.dumps(response))

        opener.return_value.open.side_effect = invalid
        with self.assertRaises(RankingFailure):
            rank_jobs(self.jobs, set(), self.config, api_key="fake")

    @patch("jobs_bot.jev_ranking.build_opener")
    def test_later_failure_keeps_earlier_validated_batch(self, opener):
        """Retain already paid assessments while rejecting an incomplete run."""
        self.config["jev"]["batch_size"] = 2
        calls = 0

        def fail_second(request, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise TimeoutError("PRIVATE")
            return self.response(request)

        opener.return_value.open.side_effect = fail_second
        with self.assertRaises(RankingFailure) as raised:
            rank_jobs(self.jobs, set(), self.config, api_key="fake")
        self.assertEqual(raised.exception.receipt["calls"], 1)
        self.assertEqual(len(raised.exception.receipt["assessments"]), 2)
        self.assertEqual(opener.return_value.open.call_count, 2)

    @patch("jobs_bot.jev_ranking.build_opener")
    def test_budget_and_endpoint_checks_precede_any_request(self, opener):
        """Reject unsafe destinations and excess calls before using credentials."""
        for mutation in ({"base_url": "https://other.example"}, {"batch_size": 0}):
            config = copy.deepcopy(self.config)
            config["jev"].update(mutation)
            with self.assertRaises(ValueError):
                rank_jobs(self.jobs, set(), config, api_key="fake")
        self.config["ranking"]["max_calls"] = 1
        self.config["jev"]["batch_size"] = 1
        with self.assertRaises(ValueError):
            rank_jobs(self.jobs, set(), self.config, api_key="fake")
        opener.assert_not_called()

    @patch("jobs_bot.jev_ranking.build_opener")
    def test_salary_questions_remove_high_pay_and_preserve_unknown(self, opener):
        """Salary decisions filter selection separately from suitability."""
        self.jobs = [
            {**self.jobs[0], "id": str(i), "company": {"display_name": str(i)}}
            for i in range(4)
        ]
        statuses = ["above_cap", "within_cap", "crosses_cap", "unknown"]

        def salary_response(request, **kwargs):
            payload = json.loads(request.data)
            self.assertEqual(len(payload["questions"]), 8)
            self.assertIn(
                "50000", payload["questions"]["salary_0"]["instructions"]["question"]
            )
            result = json.load(self.response(request))
            for i, status in enumerate(statuses):
                result["answers"][f"salary_{i}"]["choice"] = status
                result["answers"][f"salary_{i}"]["probabilities"] = {
                    label: float(label == status)
                    for label in payload["questions"][f"salary_{i}"]["criteria"]
                }
            return io.StringIO(json.dumps(result))

        opener.return_value.open.side_effect = salary_response
        selected, receipt = rank_jobs(self.jobs, set(), self.config, api_key="fake")
        self.assertEqual({j["id"] for j in selected}, {"1", "3"})
        self.assertEqual(receipt["salary_exclusions"], ["0", "2"])
        self.assertEqual(
            [a["salary_category"] for a in receipt["assessments"]], statuses
        )
        self.assertEqual(opener.return_value.open.call_count, 1)

    @patch("jobs_bot.jev_ranking.build_opener")
    def test_missing_salary_answer_fails_instead_of_bypassing_cap(self, opener):
        """A partial paid response must not silently disable salary screening."""

        def incomplete(request, **kwargs):
            result = json.load(self.response(request))
            result["answers"].pop("salary_0")
            return io.StringIO(json.dumps(result))

        opener.return_value.open.side_effect = incomplete
        with self.assertRaises(RankingFailure):
            rank_jobs(self.jobs, set(), self.config, api_key="fake")

    @patch("jobs_bot.__main__.rank_jev")
    def test_config_switch_uses_jev_and_saves_receipt_without_email(self, model):
        """Exercise the normal selector and its inspectable assessment record."""
        self.config["ranking"]["method"] = "jev"
        receipt = {"model": "jev-1.14.0", "calls": 1, "assessments": []}
        model.return_value = self.jobs, receipt
        with tempfile.TemporaryDirectory() as directory:
            self.config["ranking"]["receipt_directory"] = directory
            self.assertEqual(
                _select(self.jobs, set(), self.config, "adzuna"), self.jobs
            )
            records = list(Path(directory).glob("*.json"))
            self.assertEqual(json.loads(records[0].read_text())["receipt"], receipt)
        model.assert_called_once_with(self.jobs, set(), self.config)
