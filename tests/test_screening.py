"""Check exact salary exclusions before ranking without network or email."""

import unittest
from unittest.mock import patch

from jobs_bot.__main__ import _select
from jobs_bot.screening import salary_details, screen_jobs


class ScreeningTests(unittest.TestCase):
    """Keep unknown pay eligible while enforcing comparable upper salaries."""

    def test_annual_cap_includes_estimates_and_overlapping_ranges(self):
        """Retain the boundary and exclude upper amounts exceeding it."""
        jobs = [
            {"id": "boundary", "salary_max": 50000},
            {"id": "range", "salary_min": 45000, "salary_max": 55000},
            {"id": "estimate", "salary_max": 51000, "salary_is_predicted": "1"},
            {"id": "missing"},
        ]
        result = screen_jobs(jobs, {"max_salary_gbp": 50000}, "adzuna")
        self.assertEqual([j["id"] for j in result], ["boundary", "missing"])

    def test_jsearch_requires_annual_gbp_and_numeric_pay(self):
        """Never compare dollars, day rates or missing units to annual pounds."""
        jobs = [
            {"id": "annual", "salary_currency": "GBP", "salary_period": "YEAR"},
            {"id": "usd", "salary_currency": "USD", "salary_period": "YEAR"},
            {"id": "daily", "salary_currency": "GBP", "salary_period": "DAY"},
            {"id": "unknown"},
        ]
        for job in jobs:
            job["salary_max"] = 60000
        result = screen_jobs(jobs, {"max_salary_gbp": 50000}, "jsearch")
        self.assertEqual([j["id"] for j in result], ["usd", "daily", "unknown"])
        self.assertEqual(screen_jobs(jobs, {}, "jsearch"), jobs)
        with self.assertRaises(ValueError):
            screen_jobs(jobs, {"max_salary_gbp": -1}, "jsearch")

    @patch("jobs_bot.__main__.rank_jev")
    def test_daily_coordinator_screens_before_model_call(self, ranker):
        """A model cannot re-admit a vacancy removed by the salary cap."""
        ranker.return_value = ([], {"calls": 0, "model": "test", "assessments": []})
        config = {
            "search": {"max_salary_gbp": 50000},
            "ranking": {"method": "jev", "model": "test"},
        }
        _select([{"id": "expensive", "salary_max": 60000}], set(), config, "adzuna")
        self.assertEqual(ranker.call_args.args[0], [])

    def test_description_salary_figures_are_copied_not_estimated(self):
        """Expose explicit ranges, preserve open lower bounds and unknown pay."""
        row = {"salary_category": "within_cap", "salary_probabilities": {}}
        for text, low, high in (
            ("Annual starting salary ranging from £36,000 to £50,000", 36000, 50000),
            ("Starting salary of GBP 30k–35k plus bonus", 30000, 35000),
            ("Basic salary: up to £65k", None, 65000),
        ):
            with self.subTest(text=text):
                detail = salary_details({"description": text}, row)
                self.assertEqual((detail["min"], detail["max"]), (low, high))
                self.assertEqual(detail["source"], "advert_description")
        unknown = salary_details(
            {"description": "Potential earnings £85,000 including commission"},
            {**row, "salary_category": "unknown"},
        )
        self.assertIsNone(unknown["max"])
        self.assertEqual(unknown["source"], "not_established")
