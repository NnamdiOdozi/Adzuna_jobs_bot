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
        "category": {"tag": "accounting-finance-jobs"},
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
            _job("junior", "Junior Finance Analyst", "2026-11-01T03:00:00Z"),
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
            _job("entry", "Entry-level Finance Analyst"),
            _job("juniorish", "Juniorish Banking Investment Finance Analyst"),
        ]
        selected = select_jobs(jobs, set(), self.config)
        self.assertEqual(
            [job["id"] for job in selected], ["entry", "overhead", "juniorish"]
        )

    def test_experience_requirements_override_misleading_junior_titles(self):
        """Screen the description for both providers before filling slots."""
        descriptions = [
            "Requires 3+ years of experience.",
            "At least three years' relevant experience required.",
            "Minimum of 4–6 years of professional experience.",
            "No less than 3 years experience required.",
            "You need five to seven years of finance experience.",
            "2 years experience in finance; 3 years audit experience required.",
        ]
        for provider in ("adzuna", "jsearch"):
            for description in descriptions:
                with self.subTest(provider=provider, description=description):
                    config = dict(self.config, provider=provider, shortlist_size=1)
                    junior = dict(
                        _job("junior", "Junior Finance Analyst"),
                        description=description,
                    )
                    eligible = _job("eligible", "Credit Analyst")
                    self.assertEqual(
                        select_jobs([junior, eligible], set(), config), [eligible]
                    )

    def test_experience_in_title_is_also_checked(self):
        """Apply experience checks to requirements embedded in titles."""
        job = _job("one", "Finance Analyst - 3+ years experience required")
        self.assertEqual(select_jobs([job], set(), self.config), [])

    def test_supported_experience_precedes_uncertain_junior_title(self):
        """Explicit requirements are stronger evidence than a junior label."""
        for description in (
            "0–2 years of experience required.",
            "One to three years of relevant experience required.",
            "2+ years experience required.",
            "Two or more years experience required.",
            "Zero to three years experience required.",
            "No prior experience is required.",
        ):
            with self.subTest(description=description):
                supported = dict(
                    _job("supported", "Credit Analyst"), description=description
                )
                unknown = _job("unknown", "Graduate Finance Analyst")
                self.assertEqual(
                    select_jobs([unknown, supported], set(), self.config),
                    [supported, unknown],
                )

    def test_optional_experience_and_upper_bounds_do_not_imply_a_minimum(self):
        """Retain uncertain roles without promoting them as confirmed fits."""
        for description in (
            "3 years experience preferred.",
            "Ideally five years of experience.",
            "4 years of experience would be a bonus.",
            "Up to 5 years of experience.",
            "At most 4 years experience.",
            "Maximum of 5 years experience.",
            "Less than 4 years experience.",
            "3 years experience is not required.",
        ):
            with self.subTest(description=description):
                uncertain = dict(
                    _job("uncertain", "Credit Analyst"), description=description
                )
                junior = _job("junior", "Graduate Finance Analyst")
                self.assertEqual(
                    select_jobs([uncertain, junior], set(), self.config),
                    [junior, uncertain],
                )

    def test_missing_description_and_unrelated_years_are_uncertain(self):
        """Retain adverts without direct evidence about applicant experience."""
        for provider in ("adzuna", "jsearch"):
            for description in (
                None,
                "",
                "Founded 30 years ago. Salary £35000.",
                "A two year training programme.",
                "Support a manager with ten years’ experience.",
                "Must support a manager with ten years experience.",
                "Our company has 30 years experience.",
                "3 years experience.",
            ):
                with self.subTest(provider=provider, description=description):
                    job = dict(_job("one", "Finance Analyst"), description=description)
                    config = dict(self.config, provider=provider)
                    self.assertEqual(select_jobs([job], set(), config), [job])

    def test_required_experience_is_not_cancelled_by_optional_clause(self):
        """A separate preferred requirement does not weaken a mandatory minimum."""
        for separator in ("; ", ", ", " but ", ". ", "\n"):
            with self.subTest(separator=separator):
                job = dict(
                    _job("one", "Graduate Finance Analyst"),
                    description=(
                        "3 years experience required"
                        + separator
                        + "5 years experience preferred."
                    ),
                )
                self.assertEqual(select_jobs([job], set(), self.config), [])

    def test_graduate_associate_retains_explicit_junior_preference(self):
        """Keep graduate associate programmes ahead of uncertain generic titles."""
        jobs = [
            _job("associate", "Graduate Investment Associate"),
            _job("analyst", "Credit Analyst"),
        ]
        self.assertEqual(select_jobs(jobs, set(), self.config), jobs)

    def test_finance_keyword_count_does_not_outweigh_recency(self):
        """Prefer a newer relevant role over a title containing more finance words."""
        jobs = [
            _job("crowded", "Banking Investment Finance Analyst", "2026-11-01"),
            _job("plain", "Credit Analyst", "2026-11-04"),
        ]
        self.assertEqual(select_jobs(jobs, set(), self.config), jobs[::-1])

    def test_equal_rank_preserves_input_order(self):
        """Keep provider order when candidate evidence and publication date tie."""
        jobs = [_job("first", "Credit Analyst"), _job("second", "Finance Analyst")]
        self.assertEqual(select_jobs(jobs, set(), self.config), jobs)

    def test_experience_exclusions_are_logged(self):
        """Make exclusions visible without quoting advert descriptions in logs."""
        job = dict(
            _job("one", "Finance Analyst"), description="3 years experience required."
        )
        with self.assertLogs(level="INFO") as logs:
            self.assertEqual(select_jobs([job], set(), self.config), [])
        self.assertTrue(
            any(
                "reason=experience_above_limit count=1" in message
                for message in logs.output
            )
        )

    def test_fractional_experience_uses_the_actual_lower_bound(self):
        """Retain fractions within the limit and reject mandatory higher minima."""
        for provider in ("adzuna", "jsearch"):
            for amount, retained in (
                ("0.5", True),
                (".5", True),
                ("1.5", True),
                ("1.5–3.5", True),
                ("2.0", True),
                ("2.5", False),
                ("2.25", False),
                ("2.5 to 4", False),
                ("3.5", False),
            ):
                with self.subTest(provider=provider, amount=amount):
                    job = dict(
                        _job("one", "Junior Finance Analyst"),
                        description=f"{amount} years experience required.",
                    )
                    config = dict(self.config, provider=provider)
                    self.assertEqual(
                        select_jobs([job], set(), config), [job] if retained else []
                    )

    def test_alternatives_and_conditional_requirements_remain_unknown(self):
        """Do not exclude or promote a job on an uncertain conditional requirement."""
        descriptions = (
            "Requires 3 years experience or a relevant masters degree.",
            "No experience required for graduates; "
            "3 years experience required for non-graduates.",
            "3 years experience required unless you hold a master's degree.",
            "3 years experience required if you do not hold a relevant degree.",
            "3 years experience required, or equivalent qualifications.",
            "1 year experience required or a relevant degree.",
        )
        for provider in ("adzuna", "jsearch"):
            for description in descriptions:
                with self.subTest(provider=provider, description=description):
                    unknown = dict(
                        _job("unknown", "Finance Analyst"), description=description
                    )
                    junior = _job("junior", "Graduate Finance Analyst")
                    config = dict(self.config, provider=provider)
                    self.assertEqual(
                        select_jobs([unknown, junior], set(), config),
                        [junior, unknown],
                    )

    def test_optional_modifiers_belong_to_their_own_requirement(self):
        """An optional skill cannot cancel a separate mandatory experience minimum."""
        for description in (
            "3 years experience required and Python preferred.",
            "3 years experience required with Python preferred.",
            "Python preferred and 3 years experience required.",
            "3 years experience required but Python is desirable.",
            "3 years experience required; knowledge of Python is a bonus.",
            "3 years experience required, ideally with Python skills.",
            "3 years experience required and 5 years experience preferred.",
            "Requires 3 years experience, but 5 years would be preferred.",
        ):
            with self.subTest(description=description):
                job = dict(
                    _job("one", "Junior Finance Analyst"), description=description
                )
                self.assertEqual(select_jobs([job], set(), self.config), [])
        for description in (
            "3 years experience preferred and Python required.",
            "Python required and 3 years experience preferred.",
            "Ideally 3 years experience and Python required.",
        ):
            with self.subTest(description=description):
                job = dict(_job("one", "Finance Analyst"), description=description)
                self.assertEqual(select_jobs([job], set(), self.config), [job])

    def test_direct_applicant_requirements_are_recognized(self):
        """Handle ordinary applicant subjects without borrowing a manager's years."""
        for description in (
            "The successful candidate must have 5 years experience.",
            "You will need at least 3 years experience.",
            "Applicants must have 3 years experience.",
        ):
            with self.subTest(description=description):
                job = dict(
                    _job("one", "Junior Finance Analyst"), description=description
                )
                self.assertEqual(select_jobs([job], set(), self.config), [])
        for description in (
            "The successful candidate must support a manager with 5 years experience.",
            "You will need to support a manager with at least 3 years experience.",
            "Our company has 30 years experience and Python skills are required.",
        ):
            with self.subTest(description=description):
                job = dict(_job("one", "Finance Analyst"), description=description)
                self.assertEqual(select_jobs([job], set(), self.config), [job])

    def test_title_requirement_punctuation_does_not_change_the_result(self):
        """Recognize title requirements after separators and inside parentheses."""
        for title in (
            "Finance Analyst - 3 years experience required",
            "Finance Analyst: 3 years experience required",
            "Finance Analyst (3 years experience required)",
            "Finance Analyst | 3 years experience required",
        ):
            with self.subTest(title=title):
                self.assertEqual(
                    select_jobs([_job("one", title)], set(), self.config), []
                )

    def test_separate_alternative_does_not_cancel_an_unconditional_requirement(self):
        """An uncertain second sentence leaves an independent minimum intact."""
        job = dict(
            _job("one", "Junior Finance Analyst"),
            description="3 years experience required. "
            "Python or another programming language is preferred.",
        )
        self.assertEqual(select_jobs([job], set(), self.config), [])

    def test_candidate_experience_limit_is_configurable(self):
        """Use the configured number for rejection and compatible-experience ranking."""
        for limit, required, retained in (
            (0, 0, True),
            (0, 1, False),
            (1.5, 1.5, True),
            (1.5, 2, False),
            (3, 3, True),
            (3, 4, False),
        ):
            with self.subTest(limit=limit, required=required):
                job = dict(
                    _job("one", "Finance Analyst"),
                    description=f"{required} years experience required.",
                )
                config = dict(self.config, max_experience_years=limit)
                self.assertEqual(
                    select_jobs([job], set(), config), [job] if retained else []
                )
        config = dict(self.config)
        del config["max_experience_years"]
        job = dict(
            _job("one", "Finance Analyst"), description="3 years experience required."
        )
        self.assertEqual(select_jobs([job], set(), config), [])

    def test_invalid_experience_limits_fail_explicitly(self):
        """Reject invalid limits instead of silently accepting every requirement."""
        for limit in (-1, "2", None, True, float("nan"), float("inf")):
            with (
                self.subTest(limit=limit),
                self.assertRaisesRegex(ValueError, "max_experience_years"),
            ):
                select_jobs([], set(), dict(self.config, max_experience_years=limit))

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

    def test_controller_is_excluded_even_with_assistant_preference(self):
        """Apply the user's controller exclusion before junior ranking."""
        jobs = [
            _job("controller", "Financial Controller"),
            _job("assistant_controller", "Assistant Financial Controller"),
            _job("credit_controller", "Credit Controller"),
            _job("assistant", "Finance Assistant"),
        ]
        self.assertEqual(select_jobs(jobs, set(), self.config), [jobs[-1]])

    def test_unrelated_bulletin_titles_cannot_qualify_even_in_finance_category(self):
        """Reject the unrelated November 10 titles instead of filling 20 slots."""
        titles = [
            "Entry-Level Executive Search Consultant",
            "Static Maintenance Engineer",
            "Pharmacy Support Worker - Bank",
            "Bank Barista",
            "Barista Supervisor",
            "Administrator",
            "Demand Planner",
            "Hotel Kitchen Team Leader",
            "Contract Support Administrator",
            "Chef de Partie",
            "Mechanical Maintenance Engineer",
            "Business Operations Specialist",
            "Head Baker",
            "Asbestos Surveyor & Analyst - Duel Role",
            "Beauty Artist - Selfridges London",
            "Our clients are searching carpenters for garden furniture in Northolt",
            "OSINT Analyst",
            "Veterinary Surgeon",
        ]
        jobs = [_job(str(index), title) for index, title in enumerate(titles)]
        self.assertEqual(select_jobs(jobs, set(), self.config), [])

    def test_relevant_finance_titles_remain_eligible(self):
        """Keep explicit finance roles, including accounts and payroll assistants."""
        titles = [
            "Part Time Finance support",
            "Accountant - Hybrid",
            "Accounts Assistant",
            "Payroll Assistant",
        ]
        jobs = [_job(str(index), title) for index, title in enumerate(titles)]
        selected = select_jobs(jobs, set(), self.config)
        self.assertEqual({job["id"] for job in selected}, {job["id"] for job in jobs})

    def test_finance_title_requires_valid_matching_category(self):
        """Do not infer finance category from the employer or a title keyword."""
        for category in ({"tag": "it-jobs"}, {}, None, "accounting-finance-jobs"):
            with self.subTest(category=category):
                job = _job("one", "Graduate Financial Software Developer")
                job["category"] = category
                self.assertEqual(select_jobs([job], set(), self.config), [])
        missing = _job("missing", "Graduate Finance Analyst")
        del missing["category"]
        self.assertEqual(select_jobs([missing], set(), self.config), [])

    def test_finance_relevance_uses_whole_words(self):
        """Generic bank work and substrings must not count as finance evidence."""
        jobs = [
            _job("risky", "Junior Risky Business Assistant"),
            _job("bank", "Bank Support Worker"),
            _job("analyst", "Junior Analyst"),
            _job("banking", "Junior Banking Analyst"),
        ]
        self.assertEqual(select_jobs(jobs, set(), self.config), [jobs[-1]])


if __name__ == "__main__":
    unittest.main()
