"""Check graduate title screening with synthetic adverts and no service calls."""

import tomllib
import unittest
from pathlib import Path

from jobs_bot.shortlist import job_keys, select_jobs


def _job(identifier, title, created="2026-11-04T03:00:00Z"):
    return {
        "id": identifier,
        "title": title,
        "created": created,
        "company": {"display_name": "Example Bank"},
        "location": {"display_name": "London"},
    }


class ShortlistTests(unittest.TestCase):
    """Exercise configured career-level rules before the shortlist limit."""

    def setUp(self):
        """Use the same editable search preferences as normal bot runs."""
        with Path("config.toml").open("rb") as stream:
            self.config = tomllib.load(stream)["search"]

    def test_clearly_senior_titles_from_november_shortlist_are_excluded(self):
        """Reject all seven clear senior titles from the reported email."""
        titles = [
            "Investment Banking Senior Analyst, UK Banking",
            "Senior Analyst, Loan Capital Markets (EMEA) - Investment Banking",
            "Finance and Administration Manager",
            "Audit and Accounts Assistant Manager / Manager",
            "Senior Accountant (Accountancy Practice)",
            "Director / Sr VP - Warehouse Finance (ABL/Securitisation)",
            "Managing Director, Head of UK, Europe and Middle East & Africa "
            "(MEA) Digital Technology & Communications, Commercial Banking",
        ]
        jobs = [_job(str(index), title) for index, title in enumerate(titles)]
        self.assertEqual(select_jobs(jobs, set(), self.config), [])

    def test_junior_signals_outweigh_finance_keyword_count_and_recency(self):
        """Prefer explicit junior roles to newer, keyword-heavy generic roles."""
        jobs = [
            _job("generic", "Banking Investment Finance Analyst"),
            _job("junior", "Junior Analyst", "2026-11-01T03:00:00Z"),
        ]
        selected = select_jobs(jobs, set(), self.config)
        self.assertEqual([job["id"] for job in selected], ["junior", "generic"])

    def test_associate_is_retained_below_generic_analyst(self):
        """Treat associate seniority as uncertain rather than a hard rejection."""
        jobs = [
            _job("associate", "Banking Investment Finance Associate"),
            _job("analyst", "Credit Analyst"),
        ]
        selected = select_jobs(jobs, set(), self.config)
        self.assertEqual([job["id"] for job in selected], ["analyst", "associate"])

    def test_senior_exclusions_override_assistant_and_junior_preferences(self):
        """Keep Finance Assistant but reject Assistant Manager and Junior VP."""
        jobs = [
            _job("assistant", "Finance Assistant"),
            _job("manager", "Finance Assistant Manager"),
            _job("vp", "Junior Finance VP"),
        ]
        self.assertEqual(select_jobs(jobs, set(), self.config), [jobs[0]])

    def test_title_phrases_use_words_and_normalise_punctuation(self):
        """Recognize Sr. and head-of without matching an unrelated overhead word."""
        jobs = [
            _job("sr", "Sr. Finance Analyst"),
            _job("vp", "VP, Credit"),
            _job("head", "Head-of Finance"),
            _job("overhead", "Overhead Finance Analyst"),
            _job("entry", "Entry-level Analyst"),
            _job("juniorish", "Juniorish Banking Investment Finance Analyst"),
        ]
        selected = select_jobs(jobs, set(), self.config)
        self.assertEqual(
            [job["id"] for job in selected], ["entry", "juniorish", "overhead"]
        )

    def test_deduplication_and_limit_still_apply_after_senior_filter(self):
        """Fill slots from eligible unseen roles, never duplicates or senior roles."""
        self.config["shortlist_size"] = 2
        sent = _job("sent", "Graduate Finance Analyst")
        jobs = [
            sent,
            _job("repost", sent["title"]),
            _job("senior", "Senior Finance Analyst"),
            _job("junior", "Junior Finance Analyst"),
            _job("copy", "Junior Finance Analyst"),
            _job("trainee", "Trainee Accountant"),
            _job("generic", "Credit Analyst"),
        ]
        selected = select_jobs(jobs, job_keys(sent), self.config)
        self.assertEqual([job["id"] for job in selected], ["junior", "trainee"])

    def test_shortlist_does_not_pad_with_excluded_roles(self):
        """Return one eligible vacancy when the other adverts are too senior."""
        junior = _job("junior", "Graduate Finance Analyst")
        jobs = [junior, _job("senior", "Senior Finance Analyst")]
        self.assertEqual(select_jobs(jobs, set(), self.config), [junior])


if __name__ == "__main__":
    unittest.main()
