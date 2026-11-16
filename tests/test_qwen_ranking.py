"""Verify compact Qwen ranking without inference or vacancy API requests."""

import json
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from jobs_bot.__main__ import _select
from jobs_bot.model_ranking import RankingFailure
from jobs_bot.qwen_ranking import rank_jobs
from jobs_bot.shortlist import job_keys


class QwenRankingTests(unittest.TestCase):
    """Check fixed answer slots, global scores and explicit method routing."""

    def setUp(self):
        """Use public configuration with independent synthetic employers."""
        with Path("config.toml").open("rb") as stream:
            self.config = tomllib.load(stream)
        self.jobs = [
            {
                "id": name,
                "title": "Graduate Accountant",
                "company": {"display_name": "Employer " + name[-3:]},
                "location": {"display_name": "London"},
                "description": "Training provided",
            }
            for name in ("opaque-original-one", "opaque-original-two")
        ]

    @patch("jobs_bot.qwen_ranking._infer")
    def test_fixed_slots_and_global_scores(self, infer):
        """Enforce exactly one output slot per job and restore original adverts."""
        infer.return_value = (
            {
                "job_0": {"suitability": "possible_fit", "score": 3},
                "job_1": {"suitability": "strong_fit", "score": 5},
            },
            {"total_tokens": 100},
        )
        selected, receipt = rank_jobs(self.jobs, set(), self.config, api_key="fake")
        self.assertEqual(
            [j["id"] for j in selected], [self.jobs[1]["id"], self.jobs[0]["id"]]
        )
        request = infer.call_args.args[0]
        schema = request["response_format"]["json_schema"]["schema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["required"], ["job_0", "job_1"])
        self.assertFalse(schema["additionalProperties"])
        self.assertNotIn("opaque-original", json.dumps(request))
        self.assertEqual(receipt["calls"], 1)

    @patch("jobs_bot.qwen_ranking._infer")
    def test_seen_jobs_and_bad_endpoint_make_no_request(self, infer):
        """Avoid paying for history duplicates or sending keys to another host."""
        selected, receipt = rank_jobs(
            [self.jobs[0]], job_keys(self.jobs[0]), self.config
        )
        self.assertEqual(selected, [])
        self.assertEqual(receipt["calls"], 0)
        self.config["qwen"]["base_url"] = "https://other.example"
        with self.assertRaises(ValueError):
            rank_jobs(self.jobs, set(), self.config, api_key="fake")
        infer.assert_not_called()

    @patch("jobs_bot.qwen_ranking._infer")
    def test_later_bad_output_preserves_first_batch_without_retry(self, infer):
        """Keep completed assessments but fail an incomplete paid run visibly."""
        self.config["qwen"]["batch_size"] = 1
        infer.side_effect = [
            (
                {"job_0": {"suitability": "strong_fit", "score": 5}},
                {"total_tokens": 19},
            ),
            ({}, {"total_tokens": 11}),
        ]
        with self.assertRaises(RankingFailure) as raised:
            rank_jobs(self.jobs, set(), self.config, api_key="fake")
        self.assertEqual(len(raised.exception.receipt["assessments"]), 1)
        self.assertEqual(raised.exception.receipt["calls"], 1)
        self.assertEqual(infer.call_count, 2)

    @patch("jobs_bot.__main__.rank_qwen")
    @patch("jobs_bot.__main__._record_ranking")
    def test_qwen_switch_routes_normal_workflow(self, record, model):
        """Selecting qwen must invoke the compact adapter, not legacy inference."""
        self.config["ranking"]["method"] = "qwen"
        model.return_value = self.jobs, {"calls": 1, "model": "test-qwen"}
        self.assertEqual(_select(self.jobs, set(), self.config, "adzuna"), self.jobs)
        model.assert_called_once_with(self.jobs, set(), self.config)
        self.assertEqual(record.call_args.args[0]["method"], "qwen")
