"""Exercise paid-inference boundaries with synthetic adverts and offline mocks."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from jobs_bot.model_ranking import (
    RankingFailure,
    _NoRedirect,
    prepare_candidates,
    rank_jobs,
    ranking_request,
    validate_assessments,
)
from jobs_bot.services import build_message


def _job(identifier="one", title="Senior finance manager"):
    return {
        "id": identifier,
        "title": title,
        "company": {"display_name": identifier},
        "location": {"display_name": "London"},
        "description": "Requires ten years experience.",
        "redirect_url": "https://example.com/apply",
        "created": "2026-11-16",
    }


def _assessment(job, label="strong_fit"):
    return {
        "id": job["id"],
        "suitability": label,
        "reason": "Relevant finance role",
        "evidence": [{"field": "title", "quote": job["title"]}],
    }


class ModelRankingTests(unittest.TestCase):
    """Check provenance, selection, validation and safe failure without API calls."""

    def setUp(self):
        """Create a public prompt and fully explicit inference limits."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        prompt = Path(self.temp.name) / "prompt.md"
        prompt.write_text("Assess candidate fit from advert evidence.")
        self.config = {
            "candidate": {"profile": "Finance graduate, zero to two years"},
            "search": {"shortlist_size": 20},
            "ranking": {
                "base_url": "https://api.tokenfactory.nebius.com/v1",
                "model": "test-model",
                "prompt_path": str(prompt),
                "batch_size": 10,
                "max_candidates": 100,
                "max_calls": 10,
                "max_output_tokens": 8192,
                "timeout_seconds": 90,
                "max_elapsed_seconds": 600,
                "max_description_chars": 12000,
                "max_reason_chars": 1200,
                "max_evidence_chars": 2000,
                "temperature": 0,
                "allowed_labels": [
                    "strong_fit",
                    "possible_fit",
                    "unlikely_fit",
                    "insufficient_information",
                ],
                "selected_labels": ["strong_fit", "possible_fit"],
            },
        }

    def test_pool_preserves_senior_jobs_and_removes_seen_duplicates_invalid(self):
        """Avoid borrowing deterministic suitability exclusions for the model."""
        jobs = [_job(), _job(), _job("seen"), {"id": "broken"}, _job("two")]
        prepared = prepare_candidates(jobs, {"id:seen"}, self.config)
        self.assertEqual([row["id"] for row in prepared], ["one", "two"])
        self.assertEqual(prepared[0]["title"], "Senior finance manager")

    def test_salary_provenance_survives_preparation_into_email(self):
        """Label estimates after model preparation without relabelling real pay."""
        for predicted in ("1", "0"):
            with self.subTest(predicted=predicted):
                job = {
                    **_job(),
                    "salary_min": 30000,
                    "salary_max": 40000,
                    "salary_is_predicted": predicted,
                    "salary_currency": "EUR",
                    "salary_period": "YEAR",
                }
                prepared = prepare_candidates([job], set(), self.config)
                message = build_message(
                    prepared,
                    {"sender": "sender@example.com", "subject": "Jobs"},
                    ["recipient@example.com"],
                    "2026-11-22",
                )
                body = message.get_content()
                self.assertIn("30000 to 40000 EUR (YEAR)", body)
                self.assertEqual("(Adzuna estimate)" in body, predicted == "1")

    def test_explicit_truncation_and_request_hashes(self):
        """Bind request identity to the exact supplied shortened description."""
        self.config["ranking"]["max_description_chars"] = 5
        candidates = prepare_candidates([_job()], set(), self.config)
        self.assertEqual(candidates[0]["description"], "Requi")
        self.assertTrue(candidates[0]["description_truncated"])
        request = ranking_request(candidates, self.config)
        self.assertEqual(
            request["input_hash"],
            ranking_request(candidates, self.config)["input_hash"],
        )
        schema = request["response_format"]["json_schema"]["schema"]
        self.assertEqual(
            schema["properties"]["assessments"]["items"]["properties"]["id"]["enum"],
            ["one"],
        )
        self.config["candidate"]["profile"] += " changed"
        self.assertNotEqual(
            request["input_hash"],
            ranking_request(candidates, self.config)["input_hash"],
        )

    def test_rejects_incomplete_duplicate_and_invented_ids(self):
        """Require exactly one result for every supplied ID."""
        candidates = prepare_candidates([_job(), _job("two")], set(), self.config)
        for rows in (
            [],
            [_assessment(candidates[0])] * 2,
            [_assessment(candidates[0]), _assessment(_job("invented"))],
        ):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                validate_assessments({"assessments": rows}, candidates, self.config)

    def test_evidence_and_output_shape_validation(self):
        """Reject unsupported quotes, extra fields, unknown labels and long reasons."""
        candidates = prepare_candidates([_job()], set(), self.config)
        base = _assessment(candidates[0])
        mutations = [
            {"suitability": "eligible"},
            {"reason": "x" * 1201},
            {"extra": True},
            {"evidence": []},
            {"evidence": [{"field": "title", "quote": "Graduate"}]},
            {"evidence": [{"field": "company", "quote": "one"}]},
        ]
        for mutation in mutations:
            row = dict(base, **mutation)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_assessments({"assessments": [row]}, candidates, self.config)
        row = dict(base, suitability="insufficient_information", evidence=[])
        self.assertEqual(
            validate_assessments({"assessments": [row]}, candidates, self.config), [row]
        )

    @patch("jobs_bot.model_ranking._infer")
    def test_runtime_credential_uses_nebius_key_name(self, infer):
        """Use the shared uppercase credential name without reading real secrets."""
        job = _job()
        infer.return_value = ({"assessments": [_assessment(job)]}, {})
        with patch(
            "jobs_bot.model_ranking.os.getenv", return_value="synthetic"
        ) as lookup:
            selected, _ = rank_jobs([job], set(), self.config)
        lookup.assert_called_once_with("NEBIUS_KEY")
        self.assertEqual(len(selected), 1)
        self.assertEqual(infer.call_args.args[2], "synthetic")

    @patch("jobs_bot.model_ranking._infer")
    def test_tiers_batch_order_and_receipt(self, infer):
        """Preserve model order within each label tier across bounded batches."""
        jobs = [_job("one"), _job("two"), _job("three")]
        self.config["ranking"]["batch_size"] = 2
        infer.side_effect = [
            (
                {
                    "assessments": [
                        _assessment(jobs[1], "possible_fit"),
                        _assessment(jobs[0]),
                    ]
                },
                {"total_tokens": 9},
            ),
            ({"assessments": [_assessment(jobs[2])]}, {"total_tokens": 4}),
        ]
        selected, receipt = rank_jobs(jobs, set(), self.config, api_key="fake-test-key")
        self.assertEqual([job["id"] for job in selected], ["one", "three", "two"])
        self.assertEqual(receipt["calls"], 2)
        self.assertEqual(receipt["token_usage"]["total_tokens"], 13)
        self.assertEqual(len(receipt["assessments"]), 3)
        second = infer.call_args.args[0]["response_format"]["json_schema"]["schema"]
        self.assertEqual(
            second["properties"]["assessments"]["items"]["properties"]["id"]["enum"],
            ["three"],
        )

    @patch("jobs_bot.model_ranking._infer")
    def test_budgets_and_empty_pool_make_no_paid_calls(self, infer):
        """Reject excessive candidates or required calls before contacting inference."""
        self.assertEqual(rank_jobs([], set(), self.config)[0], [])
        self.config["ranking"].update(batch_size=1, max_calls=1)
        with self.assertRaises(ValueError):
            rank_jobs([_job(), _job("two")], set(), self.config, api_key="fake")
        self.config["ranking"]["max_candidates"] = 1
        with self.assertRaises(ValueError):
            prepare_candidates([_job(), _job("two")], set(), self.config)
        infer.assert_not_called()

    @patch("jobs_bot.model_ranking.build_opener")
    def test_http_error_safe_and_not_retried(self, opener):
        """Keep provider error bodies out of user-visible exceptions."""
        opener.return_value.open.side_effect = HTTPError(
            "https://example.com", 429, "SECRET", {}, None
        )
        with self.assertRaisesRegex(RuntimeError, "status 429") as raised:
            rank_jobs([_job()], set(), self.config, api_key="fake")
        self.assertNotIn("SECRET", str(raised.exception))
        self.assertEqual(raised.exception.diagnostics["http_status"], 429)
        self.assertEqual(raised.exception.diagnostics["batch"], 1)
        self.assertEqual(raised.exception.receipt["attempted_calls"], 1)
        self.assertEqual(opener.return_value.open.call_count, 1)
        self.assertIsNone(
            _NoRedirect().redirect_request(
                None, None, 302, "", {}, "https://example.com"
            )
        )

    @patch("jobs_bot.model_ranking.build_opener")
    def test_http_success_and_invalid_finish(self, opener):
        """Require completed structured content and expose token omissions honestly."""
        response = MagicMock()
        opener.return_value.open.return_value.__enter__.return_value = response
        result = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": json.dumps({"assessments": [_assessment(_job())]})
                    },
                }
            ]
        }
        response.read.return_value = json.dumps(result)
        _, receipt = rank_jobs([_job()], set(), self.config, api_key="fake")
        self.assertIsNone(receipt["token_usage"]["total_tokens"])
        bad = copy.deepcopy(result)
        bad["choices"][0]["finish_reason"] = "length"
        bad["usage"] = {"completion_tokens": 8192, "total_tokens": 9000}
        response.read.return_value = json.dumps(bad)
        with self.assertRaises(RankingFailure) as raised:
            rank_jobs([_job()], set(), self.config, api_key="fake")
        diagnostic = raised.exception.diagnostics
        self.assertEqual(diagnostic["category"], "incomplete_output")
        self.assertEqual(diagnostic["finish_reason"], "length")
        self.assertEqual(diagnostic["token_usage"]["completion_tokens"], 8192)
        self.assertGreater(diagnostic["response_characters"], 0)

    @patch("jobs_bot.model_ranking._infer")
    def test_later_failure_retains_completed_assessments_without_retry(self, infer):
        """Keep paid, validated results when the next batch cannot complete."""
        jobs = [_job("one"), _job("two")]
        self.config["ranking"]["batch_size"] = 1
        infer.side_effect = [
            ({"assessments": [_assessment(jobs[0])]}, {"total_tokens": 37}),
            RankingFailure("timeout"),
        ]
        with self.assertRaises(RankingFailure) as raised:
            rank_jobs(jobs, set(), self.config, api_key="fake")
        receipt = raised.exception.receipt
        self.assertEqual(receipt["attempted_calls"], 2)
        self.assertEqual(receipt["completed_batches"], 1)
        self.assertEqual(receipt["token_usage"]["total_tokens"], 37)
        self.assertEqual([r["id"] for r in receipt["assessments"]], ["one"])
        self.assertEqual(infer.call_count, 2)

    @patch("jobs_bot.model_ranking.build_opener")
    def test_timeout_is_distinct_from_invalid_response(self, opener):
        """Distinguish a transport timeout without including exception text."""
        opener.return_value.open.side_effect = TimeoutError("sensitive transport text")
        with self.assertRaises(RankingFailure) as raised:
            rank_jobs([_job()], set(), self.config, api_key="fake")
        self.assertEqual(raised.exception.diagnostics["category"], "timeout")
        self.assertNotIn("sensitive", str(raised.exception))

    def test_configuration_checks_before_inference(self):
        """Reject invalid numeric limits and credential recipient changes."""
        for mutation in (
            {"base_url": "https://other.example/v1"},
            {"batch_size": True},
            {"temperature": float("nan")},
        ):
            config = copy.deepcopy(self.config)
            config["ranking"].update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                prepare_candidates([_job()], set(), config)

    @patch("jobs_bot.model_ranking._infer")
    @patch("jobs_bot.model_ranking.time.monotonic")
    def test_elapsed_budget_prevents_late_paid_call(self, clock, infer):
        """Stop before inference when preparation already consumed the budget."""
        clock.side_effect = [0, 601]
        with self.assertRaisesRegex(ValueError, "elapsed-time"):
            rank_jobs([_job()], set(), self.config, api_key="fake")
        infer.assert_not_called()

    def test_nested_provider_properties_are_not_forwarded(self):
        """Send only normalized employer and location names to the ranker."""
        job = _job()
        job["company"]["unrelated_provider_metadata"] = "unnecessary"
        candidates = prepare_candidates([job], set(), self.config)
        self.assertEqual(candidates[0]["company"], {"display_name": "one"})
