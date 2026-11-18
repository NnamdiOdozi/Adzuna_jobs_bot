"""Check daily ranker selection without provider requests or history changes."""

import unittest
from unittest.mock import patch

from jobs_bot.__main__ import _select
from jobs_bot.model_ranking import RankingFailure


class RankingIntegrationTests(unittest.TestCase):
    """Require explicit method selection and preserve the original candidate pool."""

    def test_saved_assessments_include_full_description_matched_by_id(self):
        """Keep advert wording beside decisions without changing model responses."""
        description = (
            "Billing manager, our client, an elite US law firm in central London. "
            + "Full duties and requirements. " * 600
        )
        jobs = [
            {"id": "first", "title": "Billing Manager", "description": description},
            {
                "id": "second",
                "title": "Graduate Finance Analyst",
                "description": "Graduate finance training provided.",
            },
        ]
        receipt = {
            "calls": 1,
            "input_hash": "original-input",
            "assessments": [{"id": "second"}, {"id": "first"}],
        }
        config = {"ranking": {"method": "jev", "model": "test-model"}}
        records = []
        with (
            patch("jobs_bot.__main__.rank_jev", return_value=([], receipt)),
            patch("jobs_bot.__main__._record_ranking") as save,
        ):
            _select(jobs, set(), config, "adzuna", records)
        saved = save.call_args.args[0]["receipt"]
        self.assertEqual(saved["assessments"][1]["vacancy"], description)
        self.assertEqual(saved["assessments"][1]["title"], "Billing Manager")
        self.assertEqual(saved["assessments"][0]["title"], "Graduate Finance Analyst")
        self.assertEqual(saved["assessments"][0]["vacancy"], jobs[1]["description"])
        self.assertEqual(records[0]["receipt"], saved)
        self.assertEqual(saved["input_hash"], "original-input")
        self.assertNotIn("vacancy", receipt["assessments"][0])

    def test_failed_partial_assessments_keep_their_description(self):
        """A later failed batch must not discard context from completed decisions."""
        failure = RankingFailure("jev_request_failed", batch=2)
        failure.receipt = {"calls": 1, "assessments": [{"id": "first"}]}
        config = {"ranking": {"method": "jev", "model": "test-model"}}
        with (
            patch("jobs_bot.__main__.rank_jev", side_effect=failure),
            patch("jobs_bot.__main__._record_ranking") as save,
            self.assertRaises(RankingFailure),
        ):
            _select(
                [{"id": "first", "description": "Full advert"}], set(), config, "adzuna"
            )
        partial = save.call_args.args[0]["partial_receipt"]
        self.assertEqual(partial["assessments"][0]["vacancy"], "Full advert")

    @patch("jobs_bot.__main__.rank_jobs")
    @patch("jobs_bot.__main__.select_jobs")
    def test_default_and_explicit_rules_select_existing_ranker(self, rules, model):
        """Keep daily operation on deterministic rules unless deliberately changed."""
        jobs, seen = [{"id": "one"}], {"id:old"}
        rules.return_value = jobs
        for ranking in ({}, {"method": "rules"}):
            config = {"search": {"shortlist_size": 2}, "ranking": ranking}
            self.assertEqual(_select(jobs, seen, config, "jsearch"), jobs)
            rules.assert_called_with(
                jobs, seen, {"shortlist_size": 2, "provider": "jsearch"}
            )
        model.assert_not_called()

    @patch("jobs_bot.__main__.rank_jobs")
    @patch("jobs_bot.__main__.select_jobs")
    def test_model_method_receives_unfiltered_pool_and_logs_receipt(self, rules, model):
        """Pass original provider candidates to inference and expose observed calls."""
        jobs, seen = [{"id": "senior", "title": "Senior finance manager"}], set()
        selected = [{"id": "selected"}]
        config = {
            "search": {},
            "ranking": {"method": "nebius_llm", "model": "test-model"},
        }
        model.return_value = selected, {"calls": 3}
        with self.assertLogs(level="INFO") as logged:
            self.assertEqual(_select(jobs, seen, config, "adzuna"), selected)
        model.assert_called_once_with(jobs, seen, config)
        rules.assert_not_called()
        self.assertIn("calls=3", logged.output[0])
        self.assertIn("model=test-model", logged.output[0])

    @patch("jobs_bot.__main__.rank_jobs")
    @patch("jobs_bot.__main__.select_jobs")
    def test_invalid_method_fails_without_fallback(self, rules, model):
        """Avoid silently replacing a failed model experiment with rules results."""
        with self.assertRaises(ValueError):
            _select(
                [], set(), {"search": {}, "ranking": {"method": "unknown"}}, "adzuna"
            )
        rules.assert_not_called()
        model.assert_not_called()

    @patch(
        "jobs_bot.__main__.rank_jobs", side_effect=RuntimeError("Provider unavailable")
    )
    @patch("jobs_bot.__main__.select_jobs")
    def test_model_error_remains_failure(self, rules, model):
        """Propagate inference failure without claiming a successful rule comparison."""
        config = {
            "search": {},
            "ranking": {"method": "nebius_llm", "model": "test-model"},
        }
        with self.assertRaisesRegex(RuntimeError, "Provider unavailable"):
            _select([], set(), config, "adzuna")
        rules.assert_not_called()
