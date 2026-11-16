"""Check archive replay and safe GitHub step outputs without external services."""

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from jobs_bot.snapshots import create_snapshot
from jobs_bot.workflow_inputs import choose_snapshot, main, settings


def _config():
    return {
        "archive": {
            "directory": "artifacts/candidates",
            "artifact_name": "candidates",
            "retention_days": 30,
        },
        "experiment": {"result_artifact_name": "ranking-results", "retention_days": 30},
        "ranking": {
            "model": "nvidia/nemotron-3-super-120b-a12b",
            "base_url": "https://api.tokenfactory.nebius.com/v1",
            "max_output_tokens": 8192,
        },
        "agentic": {"max_prompt_tokens": 65536},
    }


class WorkflowInputTests(unittest.TestCase):
    """Exercise archive provenance checks and workflow output injection boundaries."""

    def setUp(self):
        """Give every archive test its own temporary public input directory."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def _snapshot(self, filename, captured_at):
        snapshot = create_snapshot([], "adzuna", {}, set(), captured_at=captured_at)
        path = self.root / filename
        path.write_text(json.dumps(snapshot), encoding="utf-8")
        return path

    def test_explicit_filename_and_latest_capture(self):
        """Select by captured time rather than filename or file write order."""
        newest = self._snapshot("a.json", "2026-11-16T12:00:00+00:00")
        oldest = self._snapshot("z.json", "2026-11-15T12:00:00+00:00")
        self.assertEqual(choose_snapshot(self.root), newest)
        self.assertEqual(choose_snapshot(self.root, "z.json"), oldest)

    def test_corrupt_and_hash_tampered_archives_fail(self):
        """Do not silently replay another archive when downloaded content is broken."""
        self._snapshot("valid.json", "2026-11-16T12:00:00+00:00")
        corrupt = self.root / "corrupt.json"
        corrupt.write_text("{broken", encoding="utf-8")
        with self.assertRaises(ValueError):
            choose_snapshot(self.root)
        with self.assertRaises(ValueError):
            choose_snapshot(self.root, "corrupt.json")
        valid = json.loads((self.root / "valid.json").read_text())
        valid["provider"] = "jsearch"
        corrupt.write_text(json.dumps(valid), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash"):
            choose_snapshot(self.root, "corrupt.json")

    def test_rejects_paths_symlinks_missing_and_empty_directory(self):
        """Keep archive selection inside downloaded regular JSON files."""
        with self.assertRaises(ValueError):
            choose_snapshot(self.root)
        target = self._snapshot("target.json", "2026-11-16T12:00:00+00:00")
        for filename in (
            "../target.json",
            str(target),
            "nested/target.json",
            "target.txt",
        ):
            with self.subTest(filename=filename), self.assertRaises(ValueError):
                choose_snapshot(self.root, filename)
        linked = self.root / "linked.json"
        linked.symlink_to(target)
        with self.assertRaises(ValueError):
            choose_snapshot(self.root, "linked.json")
        with self.assertRaises(ValueError):
            choose_snapshot(self.root)
        with self.assertRaises((ValueError, FileNotFoundError)):
            choose_snapshot(self.root, "absent.json")

    def test_settings_exposes_only_intended_public_values(self):
        """Return a bounded list of public workflow parameters."""
        config = _config()
        config["unrelated"] = {"private_setting": "not an output"}
        result = settings(config)
        self.assertEqual(
            result,
            {
                "archive_directory": "artifacts/candidates",
                "archive_name": "candidates",
                "archive_retention": 30,
                "result_name": "ranking-results",
                "result_retention": 30,
                "model": "nvidia/nemotron-3-super-120b-a12b",
                "base_url": "https://api.tokenfactory.nebius.com/v1",
                "prompt_tokens": 65536,
                "output_tokens": 8192,
            },
        )

    def test_agentic_model_is_independent_of_daily_method(self):
        """Selecting Jev for daily delivery must not replace the agent driver."""
        config = _config()
        config["ranking"]["method"] = "jev"
        config["agentic"]["model"] = "Qwen/Qwen3-235B-A22B-Instruct-2507"
        self.assertEqual(settings(config)["model"], config["agentic"]["model"])

    def test_settings_rejects_newline_output_injection(self):
        """Prevent a setting from writing an extra GitHub step-output variable."""
        for section, key in (
            ("archive", "directory"),
            ("archive", "artifact_name"),
            ("experiment", "result_artifact_name"),
            ("ranking", "model"),
            ("ranking", "base_url"),
        ):
            for suffix in ("\nOTHER=bad", "\rOTHER=bad", ""):
                config = _config()
                config[section][key] = suffix
                with (
                    self.subTest(section=section, key=key, suffix=suffix),
                    self.assertRaises(ValueError),
                ):
                    settings(config)

    def test_settings_rejects_invalid_numbers_and_retention(self):
        """Reject booleans, nonpositive values and excessive archive retention."""
        numeric = [
            ("archive", "retention_days"),
            ("experiment", "retention_days"),
            ("ranking", "max_output_tokens"),
            ("agentic", "max_prompt_tokens"),
        ]
        for section, key in numeric:
            for value in (0, -1, True, 2.5, "30"):
                config = _config()
                config[section][key] = value
                with (
                    self.subTest(section=section, key=key, value=value),
                    self.assertRaises(ValueError),
                ):
                    settings(config)
        for section in ("archive", "experiment"):
            config = _config()
            config[section]["retention_days"] = 91
            with self.assertRaises(ValueError):
                settings(config)
        config = _config()
        config["archive"]["retention_days"] = 90
        self.assertEqual(settings(config)["archive_retention"], 90)

    def test_settings_rejects_wrong_credential_endpoint(self):
        """Reject a different provider as the intended credential recipient."""
        for endpoint in (
            "http://api.tokenfactory.nebius.com/v1",
            "https://other.example/v1",
            "https://api.tokenfactory.nebius.com/v1?redirect=elsewhere",
        ):
            config = _config()
            config["ranking"]["base_url"] = endpoint
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                settings(config)

    def test_choose_cli_prints_selected_archive(self):
        """Expose the chosen validated file for the next workflow step."""
        selected = self._snapshot("selected.json", "2026-11-16T12:00:00+00:00")
        output = io.StringIO()
        with (
            patch(
                "sys.argv",
                [
                    "workflow_inputs",
                    "choose",
                    "--directory",
                    str(self.root),
                    "--filename",
                    selected.name,
                ],
            ),
            redirect_stdout(output),
        ):
            main()
        self.assertEqual(output.getvalue(), str(selected) + "\n")

    def test_settings_cli_appends_github_outputs(self):
        """Append validated settings without replacing existing step outputs."""
        config_path = self.root / "public-config.toml"
        config = _config()
        lines = []
        for section, entries in config.items():
            lines.append(f"[{section}]")
            for key, value in entries.items():
                lines.append(f"{key} = {json.dumps(value)}")
        config_path.write_text("\n".join(lines), encoding="utf-8")
        output_path = self.root / "step-outputs.txt"
        output_path.write_text("earlier=value\n", encoding="utf-8")
        with (
            patch(
                "sys.argv",
                ["workflow_inputs", "settings", "--config", str(config_path)],
            ),
            patch.dict("os.environ", {"GITHUB_OUTPUT": str(output_path)}),
        ):
            main()
        expected = "earlier=value\n" + "".join(
            f"{name}={value}\n"
            for name, value in settings(copy.deepcopy(config)).items()
        )
        self.assertEqual(output_path.read_text(), expected)
