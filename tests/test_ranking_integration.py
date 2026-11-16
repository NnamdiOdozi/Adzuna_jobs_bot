"""Check daily ranker selection without provider requests or history changes."""

import unittest
from unittest.mock import patch

from jobs_bot.__main__ import _select


class RankingIntegrationTests(unittest.TestCase):
    """Require explicit method selection and preserve the original candidate pool."""

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
