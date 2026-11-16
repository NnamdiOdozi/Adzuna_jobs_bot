"""Verify manual replay, ranking reports and sender-only test delivery offline."""

import copy
import json
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from jobs_bot import experiments
from jobs_bot.model_ranking import RankingFailure, prepare_candidates, ranking_request
from jobs_bot.snapshots import create_snapshot


class ExperimentTests(unittest.TestCase):
    """Keep experiment artifacts separate from normal delivery and history."""

    def setUp(self):
        """Use synthetic vacancies and isolated artifact paths."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        with Path("config.toml").open("rb") as stream:
            self.config = tomllib.load(stream)
        self.config["history"] = {"path": str(self.directory / "seen.json")}
        self.job = {
            "id": "one",
            "title": "Graduate Finance Analyst",
            "description": "No experience required",
            "created": "2026-11-16",
            "company": {"display_name": "Example"},
            "location": {"display_name": "London"},
            "category": {"tag": self.config["search"]["category"]},
            "redirect_url": "https://example.com/job",
        }
        self.snapshot = create_snapshot([self.job], "adzuna", self.config, set())
        self.snapshot_path = self.directory / "snapshot.json"
        self.snapshot_path.write_text(json.dumps(self.snapshot))
        self.output = self.directory / "output.json"
        self.config_patch = patch(
            "jobs_bot.experiments.tomllib.load", return_value=self.config
        )
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)

    def _run(self, command, *arguments):
        experiments.main([command, *map(str, arguments)])

    def _rank(self, method):
        self._run(
            "rank",
            "--snapshot",
            self.snapshot_path,
            "--method",
            method,
            "--output",
            self.output,
        )
        return json.loads(self.output.read_text())

    def _receipt(self):
        candidates = prepare_candidates([self.job], set(), self.config)
        request = ranking_request(candidates, self.config)
        row = {
            "id": "one",
            "suitability": "strong_fit",
            "reason": "Junior finance role",
            "evidence": [{"field": "title", "quote": "Finance"}],
        }
        return candidates, {
            **{
                key: request[key]
                for key in ("input_hash", "prompt_hash", "config_hash", "model")
            },
            "assessments": [row],
        }

    def _comparison_inputs(self):
        rules = self._rank("rules")
        rules_path = self.directory / "rules.json"
        rules_path.write_text(json.dumps(rules))
        candidates, receipt = self._receipt()
        with patch(
            "jobs_bot.experiments.rank_jobs", return_value=(candidates, receipt)
        ):
            direct = self._rank("nebius_llm")
        direct_path = self.directory / "direct.json"
        direct_path.write_text(json.dumps(direct))
        return rules_path, direct_path, receipt

    def _compare(self, rules, direct, *arguments):
        self._run(
            "compare",
            "--snapshot",
            self.snapshot_path,
            "--rules",
            rules,
            "--direct",
            direct,
            "--output-dir",
            self.directory,
            *arguments,
        )
        return json.loads((self.directory / "comparison.json").read_text())

    def test_replay_does_not_fetch_or_read_history(self):
        """A downloaded snapshot suffices when providers and history are unavailable."""
        with patch("jobs_bot.experiments.fetch_jobs") as fetch:
            self._run(
                "prepare", "--snapshot", self.snapshot_path, "--output", self.output
            )
        fetch.assert_not_called()
        self.assertEqual(json.loads(self.output.read_text()), self.snapshot)
        self.assertFalse((self.directory / "seen.json").exists())

    def test_fresh_empty_fetch_does_not_fallback(self):
        """An explicit Adzuna experiment uses only that provider even for zero rows."""
        with (
            patch("jobs_bot.experiments.fetch_jobs", return_value=[]) as fetch,
            patch("jobs_bot.experiments.fetch_jsearch") as backup,
            patch.dict(
                "os.environ",
                {"ADZUNA_APP_ID": "synthetic", "ADZUNA_API_KEY": "synthetic"},
            ),
        ):
            self._run(
                "prepare", "--fresh", "--provider", "adzuna", "--output", self.output
            )
        fetch.assert_called_once()
        backup.assert_not_called()
        self.assertEqual(json.loads(self.output.read_text())["jobs"], [])

    def test_prepare_requires_deliberate_fresh_choice(self):
        """A missing replay path must not implicitly spend provider credits."""
        with self.assertRaises(ValueError):
            self._run("prepare", "--output", self.output)
        with self.assertRaises(ValueError):
            self._run(
                "prepare",
                "--snapshot",
                self.snapshot_path,
                "--fresh",
                "--output",
                self.output,
            )

    def test_rules_bind_snapshot_provider_and_seen(self):
        """Replay source and history win over today's runtime provider choice."""
        self.snapshot = create_snapshot([self.job], "jsearch", self.config, {"id:one"})
        self.snapshot_path.write_text(json.dumps(self.snapshot))
        with patch("jobs_bot.experiments.select_jobs", return_value=[]) as select:
            report = self._rank("rules")
        self.assertEqual(select.call_args.args[1], {"id:one"})
        self.assertEqual(select.call_args.args[2]["provider"], "jsearch")
        self.assertEqual(report["snapshot_hash"], self.snapshot["content_hash"])

    def test_model_failure_persists_failed_status(self):
        """Failure artifacts contain a safe type rather than false rules success."""
        with (
            patch(
                "jobs_bot.experiments.rank_jobs",
                side_effect=RuntimeError("sensitive body"),
            ),
            self.assertRaises(RuntimeError),
        ):
            self._rank("nebius_llm")
        text = self.output.read_text()
        self.assertNotIn("sensitive body", text)
        self.assertEqual(json.loads(text)["status"], "failed")

    def test_jev_replay_uses_saved_pool_without_nebius(self):
        """Route the explicit replay method to Jev without fetching more adverts."""
        with (
            patch(
                "jobs_bot.experiments.rank_jev", return_value=([self.job], {"calls": 1})
            ) as jev,
            patch("jobs_bot.experiments.rank_jobs") as nebius,
        ):
            report = self._rank("jev")
        self.assertEqual(report["method"], "jev")
        jev.assert_called_once()
        nebius.assert_not_called()

    def test_model_failure_saves_safe_diagnostics_and_partial_receipt(self):
        """Persist recovery evidence without presenting partial work as success."""
        failure = RankingFailure("incomplete_output", finish_reason="length", batch=2)
        failure.receipt = {"completed_batches": 1, "assessments": []}
        with (
            patch("jobs_bot.experiments.rank_jobs", side_effect=failure),
            self.assertRaises(RuntimeError),
        ):
            self._rank("nebius_llm")
        report = json.loads(self.output.read_text())
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["diagnostics"]["finish_reason"], "length")
        self.assertEqual(report["partial_receipt"]["completed_batches"], 1)

    def test_agent_input_and_optional_absence_are_explicit(self):
        """An absent agent run is never presented as successful inference."""
        self._run(
            "agent-input", "--snapshot", self.snapshot_path, "--output", self.output
        )
        prepared = json.loads(self.output.read_text())
        rules, direct, receipt = self._comparison_inputs()
        report = self._compare(rules, direct)
        self.assertEqual(prepared["request"]["input_hash"], receipt["input_hash"])
        self.assertEqual(report["reports"]["agent"]["status"], "not_run")

    def test_compare_validates_agent_hash_coverage_and_evidence(self):
        """Only complete bound assessments yield a validated-output artifact."""
        rules, direct, receipt = self._comparison_inputs()
        payload = {
            "snapshot_hash": self.snapshot["content_hash"],
            "input_hash": receipt["input_hash"],
            "assessments": receipt["assessments"],
        }
        self.output.write_text(json.dumps(payload))
        report = self._compare(rules, direct, "--agent", self.output)
        self.assertEqual(report["reports"]["agent"]["status"], "validated_output")
        for corrupt in ("hash", "coverage", "evidence"):
            bad = copy.deepcopy(payload)
            if corrupt == "hash":
                bad["input_hash"] = "wrong"
            elif corrupt == "coverage":
                bad["assessments"] = []
            else:
                bad["assessments"][0]["evidence"][0]["quote"] = "invented"
            self.output.write_text(json.dumps(bad))
            with self.assertRaises(ValueError):
                self._compare(rules, direct, "--agent", self.output)

    def test_direct_receipt_must_bind_request(self):
        """A report from a different profile cannot reuse this comparison."""
        rules, direct, _ = self._comparison_inputs()
        report = json.loads(direct.read_text())
        report["receipt"]["input_hash"] = "different"
        direct.write_text(json.dumps(report))
        with self.assertRaises(ValueError):
            self._compare(rules, direct)

    def test_test_email_only_uses_sender_and_password(self):
        """A single plain-text test message never consults normal recipient settings."""
        rules, direct, _ = self._comparison_inputs()
        self._compare(rules, direct)
        credentials = {
            "GMAIL_SENDER": "sender@example.com",
            "gmail_app_password": "synthetic",
        }
        accessed = []

        def credential(key):
            accessed.append(key)
            return credentials[key]

        with (
            patch(
                "jobs_bot.experiments.os.environ",
                new=type(
                    "Credentials", (), {"__getitem__": staticmethod(credential)}
                )(),
            ),
            patch("jobs_bot.experiments.send_message") as send,
        ):
            experiments._test_email(
                type(
                    "Args",
                    (),
                    {
                        "report": self.directory / "comparison.json",
                        "snapshot": self.snapshot_path,
                    },
                )(),
                self.config,
            )
        send.assert_called_once()
        message = send.call_args.args[0]
        self.assertEqual(message["To"], "sender@example.com")
        self.assertTrue(message["Subject"].startswith("[TEST]"))
        self.assertEqual(message.get_content_type(), "text/plain")
        self.assertEqual(accessed, ["GMAIL_SENDER", "gmail_app_password"])
        self.assertFalse((self.directory / "seen.json").exists())

    def test_test_email_rejects_multiple_addresses_and_header_injection(self):
        """Reject sender strings that could add another recipient or header."""
        rules, direct, _ = self._comparison_inputs()
        self._compare(rules, direct)
        for sender in (
            "one@example.com,two@example.com",
            "one@example.com\r\nBcc: two@example.com",
        ):
            with (
                patch.dict("os.environ", {"GMAIL_SENDER": sender}),
                patch("jobs_bot.experiments.send_message") as send,
                self.assertRaises(ValueError),
            ):
                self._run(
                    "test-email",
                    "--snapshot",
                    self.snapshot_path,
                    "--report",
                    self.directory / "comparison.json",
                )
            send.assert_not_called()

    def test_markdown_never_loads_advert_images_or_html(self):
        """Vacancy text cannot create remote images, markup or extra headings."""
        report = {
            "snapshot_hash": "synthetic",
            "reports": {
                "rules": {
                    "status": "success",
                    "selected": [
                        {
                            "id": "![identifier](https://example.com/track)",
                            "title": (
                                "![image](https://example.com/track) "
                                '<img src="remote">\n# heading'
                            ),
                        }
                    ],
                }
            },
        }
        text = experiments._summary(report)
        self.assertNotIn("![", text)
        self.assertNotIn("<img", text)
        self.assertNotIn("\n# heading", text)
        self.assertIn("&lt;img", text)

    def test_empty_snapshot_has_shared_request_and_zero_inference(self):
        """An empty archive still produces comparable request identities."""
        self.snapshot = create_snapshot([], "adzuna", self.config, set())
        self.snapshot_path.write_text(json.dumps(self.snapshot))
        self._run(
            "agent-input", "--snapshot", self.snapshot_path, "--output", self.output
        )
        request = json.loads(self.output.read_text())["request"]
        direct = self._rank("nebius_llm")
        self.assertEqual(direct["receipt"]["calls"], 0)
        self.assertEqual(direct["receipt"]["input_hash"], request["input_hash"])
        self.assertEqual(direct["selected"], [])

    def test_failed_direct_result_remains_failed_in_comparison(self):
        """A safe failure report can be compared without fabricating model success."""
        rules, direct, _ = self._comparison_inputs()
        direct.write_text(
            json.dumps(
                experiments._report(
                    self.snapshot,
                    "nebius_llm",
                    "failed",
                    error_type="RuntimeError",
                )
            )
        )
        report = self._compare(rules, direct)
        self.assertEqual(report["reports"]["nebius_llm"]["status"], "failed")

    def test_requested_agent_failure_remains_failed_without_output(self):
        """A failed workflow produces an artifact without needing an output file."""
        rules, direct, _ = self._comparison_inputs()
        report = self._compare(rules, direct, "--agent-status", "failed")
        self.assertEqual(report["reports"]["agent"]["method"], "gh_aw")
        self.assertEqual(report["reports"]["agent"]["status"], "failed")
        self.assertEqual(report["reports"]["agent"]["selected"], [])

    def test_agent_failure_does_not_trust_existing_output(self):
        """Leftover output cannot turn an observed workflow failure into success."""
        rules, direct, _ = self._comparison_inputs()
        report = self._compare(
            rules,
            direct,
            "--agent-status",
            "failed",
            "--agent",
            self.directory / "missing.json",
        )
        self.assertEqual(report["reports"]["agent"]["status"], "failed")

    def test_successful_agent_status_requires_valid_output(self):
        """A controller success signal alone cannot stand in for assessments."""
        rules, direct, receipt = self._comparison_inputs()
        with self.assertRaises(ValueError):
            self._compare(rules, direct, "--agent-status", "success")
        payload = {
            "snapshot_hash": self.snapshot["content_hash"],
            "input_hash": receipt["input_hash"],
            "assessments": receipt["assessments"],
        }
        self.output.write_text(json.dumps(payload))
        report = self._compare(
            rules, direct, "--agent-status", "success", "--agent", self.output
        )
        self.assertEqual(report["reports"]["agent"]["status"], "validated_output")
        payload["assessments"] = []
        self.output.write_text(json.dumps(payload))
        with self.assertRaises(ValueError):
            self._compare(
                rules, direct, "--agent-status", "success", "--agent", self.output
            )

    def test_test_email_uses_configured_subject_and_keeps_test_prefix(self):
        """Operator wording remains configurable while test emails stay labelled."""
        rules, direct, _ = self._comparison_inputs()
        self._compare(rules, direct)
        for subject in ("Custom comparison", "[TEST] Custom comparison"):
            self.config["experiment"] = {"test_subject": subject}
            with (
                patch.dict(
                    "os.environ",
                    {
                        "GMAIL_SENDER": "sender@example.com",
                        "gmail_app_password": "synthetic",
                    },
                ),
                patch("jobs_bot.experiments.send_message") as send,
            ):
                self._run(
                    "test-email",
                    "--snapshot",
                    self.snapshot_path,
                    "--report",
                    self.directory / "comparison.json",
                )
            self.assertEqual(
                send.call_args.args[0]["Subject"], "[TEST] Custom comparison"
            )
        self.config["experiment"]["test_subject"] = "Unsafe\nBcc: extra@example.com"
        with (
            patch.dict("os.environ", {"GMAIL_SENDER": "sender@example.com"}),
            patch("jobs_bot.experiments.send_message") as send,
            self.assertRaises(ValueError),
        ):
            self._run(
                "test-email",
                "--snapshot",
                self.snapshot_path,
                "--report",
                self.directory / "comparison.json",
            )
        send.assert_not_called()

    def test_failed_direct_cannot_include_invented_jobs(self):
        """A failure state cannot carry a shortlist into the rendered report."""
        rules, direct, _ = self._comparison_inputs()
        failed = experiments._report(
            self.snapshot, "nebius_llm", "failed", selected=[self.job]
        )
        direct.write_text(json.dumps(failed))
        with self.assertRaises(ValueError):
            self._compare(rules, direct)

    def test_direct_not_run_placeholder_is_supported(self):
        """Agent-only comparisons can explicitly record no direct-model run."""
        rules, direct, _ = self._comparison_inputs()
        direct.write_text(
            json.dumps(
                experiments._report(self.snapshot, "nebius_llm", "not_run", selected=[])
            )
        )
        report = self._compare(rules, direct, "--agent-status", "failed")
        self.assertEqual(report["reports"]["nebius_llm"]["status"], "not_run")
        self.assertEqual(report["reports"]["agent"]["status"], "failed")

    def test_email_revalidates_edited_comparison_before_credentials(self):
        """Artifact edits cannot bypass snapshot and assessment checks at delivery."""
        rules, direct, _ = self._comparison_inputs()
        original = self._compare(rules, direct)
        path = self.directory / "comparison.json"
        for corrupt in ("snapshot", "rules", "direct", "failed", "overlaps", "receipt"):
            bad = copy.deepcopy(original)
            if corrupt == "snapshot":
                bad["snapshot_id"] = "invented"
            elif corrupt == "rules":
                bad["reports"]["rules"]["selected"][0]["title"] = "Invented job"
            elif corrupt == "direct":
                bad["reports"]["nebius_llm"]["selected"][0]["title"] = "Invented job"
            elif corrupt == "failed":
                bad["reports"]["agent"]["selected"] = [self.job]
            elif corrupt == "overlaps":
                bad["overlap_with_rules"]["rules"] = 999
            else:
                bad["reports"]["nebius_llm"]["receipt"]["input_hash"] = "different"
            path.write_text(json.dumps(bad))
            with (
                patch("jobs_bot.experiments.send_message") as send,
                patch("jobs_bot.experiments.os.environ", {}),
                self.assertRaises(ValueError),
            ):
                self._run(
                    "test-email", "--snapshot", self.snapshot_path, "--report", path
                )
            send.assert_not_called()

    def test_email_revalidates_agent_assessments(self):
        """An agent result's selection and evidence remain checked before email."""
        rules, direct, receipt = self._comparison_inputs()
        self.output.write_text(
            json.dumps(
                {
                    "snapshot_hash": self.snapshot["content_hash"],
                    "input_hash": receipt["input_hash"],
                    "assessments": receipt["assessments"],
                }
            )
        )
        original = self._compare(rules, direct, "--agent", self.output)
        for field in ("input_hash", "assessments", "selected"):
            bad = copy.deepcopy(original)
            agent = bad["reports"]["agent"]
            if field == "input_hash":
                agent["receipt"][field] = "different"
            elif field == "assessments":
                agent["receipt"][field][0]["evidence"][0]["quote"] = "invented"
            else:
                agent["selected"] = []
            path = self.directory / "comparison.json"
            path.write_text(json.dumps(bad))
            with (
                patch("jobs_bot.experiments.send_message") as send,
                self.assertRaises(ValueError),
            ):
                self._run(
                    "test-email", "--snapshot", self.snapshot_path, "--report", path
                )
            send.assert_not_called()

    def test_reports_show_matching_reasons_evidence_and_receipt_identity(self):
        """Readers can inspect the model's rationale beside the exact vacancy."""
        rules, direct, receipt = self._comparison_inputs()
        report = self._compare(rules, direct)
        text = experiments._summary(report)
        self.assertIn("Reason: Junior finance role", text)
        self.assertIn("Evidence from title: Finance", text)
        self.assertIn("Model: " + receipt["model"], text)
        self.assertIn("Ranking input: " + receipt["input_hash"], text)
        self.assertIn("Prompt: " + receipt["prompt_hash"], text)
        self.assertIn("This method was not run.", text)
        report["reports"]["agent"]["status"] = "failed"
        self.assertIn("Execution failed.", experiments._summary(report))

    def test_explanations_cannot_inject_markdown_or_html(self):
        """Reasons and evidence remain text even when adverts contain markup."""
        rules, direct, _ = self._comparison_inputs()
        report = self._compare(rules, direct)
        row = report["reports"]["nebius_llm"]["receipt"]["assessments"][0]
        row["reason"] = (
            '![track](https://example.com/private) <img src="remote">\n# heading'
        )
        row["evidence"][0]["quote"] = "![evidence](https://example.com/track) <script>"
        text = experiments._summary(report)
        self.assertNotIn("![", text)
        self.assertNotIn("<img", text)
        self.assertNotIn("<script>", text)
        self.assertNotIn("\n# heading", text)
        self.assertIn("&lt;img", text)
        self.assertIn("&lt;script&gt;", text)
