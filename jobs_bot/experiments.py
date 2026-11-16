"""Compare vacancy ranking methods without delivery history writes."""

import argparse
import json
import logging
import os
import re
import sys
import tomllib
from email.message import EmailMessage
from pathlib import Path
from uuid import uuid4

from jobs_bot.experiment_reports import _plain_text as _plain_text
from jobs_bot.experiment_reports import _summary
from jobs_bot.jsearch import fetch_jsearch
from jobs_bot.model_ranking import (
    prepare_candidates,
    rank_jobs,
    ranking_request,
    validate_assessments,
)
from jobs_bot.services import fetch_jobs, send_message
from jobs_bot.shortlist import select_jobs
from jobs_bot.snapshots import create_snapshot, load_snapshot, save_snapshot


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def _read(path):
    return json.loads(Path(path).read_text())


def _replay_config(snapshot, config):
    # Freeze search policy with the fetched pool; runtime settings supply inference.
    return {**config, **snapshot["config"]}


def _report(snapshot, method, status="success", **details):
    return {
        "schema_version": 1,
        "snapshot_hash": snapshot["content_hash"],
        "snapshot_id": snapshot["snapshot_id"],
        "method": method,
        "status": status,
        **details,
    }


def _rules(snapshot, config):
    search = {**config["search"], "provider": snapshot["provider"]}
    return select_jobs(snapshot["jobs"], set(snapshot["seen"]), search)


def _prepare(args, config):
    if args.snapshot:
        if args.fresh or args.provider:
            raise ValueError("Replay cannot also request a fresh provider")
        snapshot = load_snapshot(args.snapshot)
    else:
        if not args.fresh:
            raise ValueError("Supply --snapshot or explicitly request --fresh")
        provider = args.provider or config["search"].get("provider", "adzuna")
        if provider == "adzuna":
            jobs = fetch_jobs(
                config["search"],
                os.environ["ADZUNA_APP_ID"],
                os.environ["ADZUNA_API_KEY"],
            )
        elif provider == "jsearch":
            jobs = fetch_jsearch(config["jsearch"], os.environ["JSEARCH_API_KEY"])
        else:
            raise ValueError("Unknown configured provider")
        history = Path(config["history"]["path"])
        seen = _read(history) if history.exists() else []
        if not isinstance(seen, list) or any(not isinstance(key, str) for key in seen):
            raise ValueError("History must contain string keys")
        snapshot = create_snapshot(jobs, provider, config, set(seen))
    output = Path(args.output)
    save_snapshot(snapshot, output.parent, filename=output.name)


def _rank(args, snapshot, config):
    if args.method == "rules":
        report = _report(snapshot, "rules", selected=_rules(snapshot, config))
    else:
        try:
            selected, receipt = rank_jobs(
                snapshot["jobs"], set(snapshot["seen"]), config
            )
            report = _report(snapshot, "nebius_llm", selected=selected, receipt=receipt)
        except Exception as error:
            # Raw provider exceptions can contain credential-bearing response bodies.
            _write(
                args.output,
                _report(
                    snapshot,
                    "nebius_llm",
                    "failed",
                    error_type=type(error).__name__,
                ),
            )
            raise RuntimeError(
                "Model ranking failed; safe failure report saved"
            ) from None
    _write(args.output, report)


def _agent_input(args, snapshot, config):
    candidates = prepare_candidates(snapshot["jobs"], set(snapshot["seen"]), config)
    request = ranking_request(candidates, config)
    _write(
        args.output,
        {
            "snapshot_hash": snapshot["content_hash"],
            "snapshot_id": snapshot["snapshot_id"],
            "request": request,
            "output_contract": {
                "snapshot_hash": snapshot["content_hash"],
                "input_hash": request["input_hash"],
                "assessments": "Use the request response_format JSON schema",
            },
        },
    )


def _validated_report(path, snapshot, method):
    report = _read(path)
    if (
        report.get("snapshot_hash") != snapshot["content_hash"]
        or report.get("method") != method
        or report.get("status") not in {"success", "failed", "not_run"}
    ):
        raise ValueError("Ranking report is not bound to this snapshot and method")
    return report


def _assessed_selection(assessments, candidates, config):
    jobs = {str(job["id"]): job for job in candidates}
    settings = config["ranking"]
    selected = []
    for label in settings["selected_labels"]:
        selected.extend(
            jobs[row["id"]] for row in assessments if row["suitability"] == label
        )
    return selected[: config["search"]["shortlist_size"]]


def _compare(args, snapshot, config):
    rules = _validated_report(args.rules, snapshot, "rules")
    direct = _validated_report(args.direct, snapshot, "nebius_llm")
    candidates = prepare_candidates(snapshot["jobs"], set(snapshot["seen"]), config)
    request = ranking_request(candidates, config)
    reports = {"rules": rules, "nebius_llm": direct}
    if args.agent_status == "success" and not args.agent:
        raise ValueError("Successful agent execution requires --agent output")
    if args.agent_status == "failed":
        reports["agent"] = _report(snapshot, "gh_aw", "failed", selected=[])
    elif args.agent:
        payload = _read(args.agent)
        if (
            payload.get("snapshot_hash") != snapshot["content_hash"]
            or payload.get("input_hash") != request["input_hash"]
        ):
            raise ValueError("Agent output is not bound to the shared ranking request")
        assessments = validate_assessments(
            {"assessments": payload.get("assessments")}, candidates, config
        )
        reports["agent"] = _report(
            snapshot,
            "gh_aw",
            "validated_output",
            selected=_assessed_selection(assessments, candidates, config),
            receipt={
                "assessments": assessments,
                "input_hash": request["input_hash"],
                "execution": "not_independently_verified",
            },
        )
    else:
        reports["agent"] = _report(snapshot, "gh_aw", "not_run", selected=[])
    rules_ids = {str(job["id"]) for job in rules["selected"]}
    overlaps = {
        method: len(rules_ids & {str(job["id"]) for job in result.get("selected", [])})
        for method, result in reports.items()
    }
    report = _report(
        snapshot, "comparison", reports=reports, overlap_with_rules=overlaps
    )
    _validate_comparison(report, snapshot, config)
    directory = Path(args.output_dir)
    _write(directory / "comparison.json", report)
    (directory / "comparison.md").write_text(_summary(report))


def _validate_comparison(report, snapshot, config):
    if (
        report.get("method") != "comparison"
        or report.get("status") != "success"
        or report.get("snapshot_hash") != snapshot["content_hash"]
        or report.get("snapshot_id") != snapshot["snapshot_id"]
    ):
        raise ValueError("Comparison does not match this snapshot")
    reports = report.get("reports")
    if not isinstance(reports, dict) or set(reports) != {
        "rules",
        "nebius_llm",
        "agent",
    }:
        raise ValueError("Comparison must contain all ranking methods")
    candidates = prepare_candidates(snapshot["jobs"], set(snapshot["seen"]), config)
    request = ranking_request(candidates, config)
    for name, method in (
        ("rules", "rules"),
        ("nebius_llm", "nebius_llm"),
        ("agent", "gh_aw"),
    ):
        result = reports[name]
        if (
            result.get("method") != method
            or result.get("snapshot_hash") != snapshot["content_hash"]
            or result.get("snapshot_id") != snapshot["snapshot_id"]
        ):
            raise ValueError("Ranking method is not bound to this snapshot")
        status = result.get("status")
        if name == "rules":
            if status != "success" or result.get("selected") != _rules(
                snapshot, config
            ):
                raise ValueError("Rules report differs from replayed rules selection")
        elif status in {"failed", "not_run"}:
            if result.get("selected", []) != []:
                raise ValueError(
                    "Failed or absent ranking cannot contain selected jobs"
                )
            result["selected"] = []
        elif status == ("validated_output" if name == "agent" else "success"):
            receipt = result.get("receipt", {})
            keys = (
                ("input_hash",)
                if name == "agent"
                else ("input_hash", "prompt_hash", "config_hash", "model")
            )
            if any(receipt.get(key) != request[key] for key in keys):
                raise ValueError("Ranking receipt differs from shared request")
            assessments = validate_assessments(
                {"assessments": receipt.get("assessments")}, candidates, config
            )
            if result.get("selected") != _assessed_selection(
                assessments, candidates, config
            ):
                raise ValueError("Selection differs from validated assessments")
        else:
            raise ValueError("Unsupported ranking status")
    rules_ids = {str(job["id"]) for job in reports["rules"]["selected"]}
    expected = {
        name: len(rules_ids & {str(job["id"]) for job in result["selected"]})
        for name, result in reports.items()
    }
    if report.get("overlap_with_rules") != expected:
        raise ValueError("Comparison overlap counts differ from selected jobs")


def _test_email(args, config):
    report = _read(args.report)
    snapshot = load_snapshot(args.snapshot)
    _validate_comparison(report, snapshot, _replay_config(snapshot, config))
    sender = os.environ["GMAIL_SENDER"].strip()
    if not re.fullmatch(r"[^\s@,;<>]+@[^\s@,;<>]+\.[^\s@,;<>]+", sender):
        raise ValueError("GMAIL_SENDER must contain one plain email address")
    message = EmailMessage()
    message["From"] = sender
    message["To"] = sender
    subject = config.get("experiment", {}).get(
        "test_subject", "[TEST] Job ranking comparison"
    )
    if not isinstance(subject, str) or "\r" in subject or "\n" in subject:
        raise ValueError("Test subject must be a single line")
    message["Subject"] = (
        subject if subject.startswith("[TEST]") else f"[TEST] {subject}"
    )
    message.set_content(_summary(report))
    send_message(
        message, {**config["email"], "sender": sender}, os.environ["gmail_app_password"]
    )
    logging.info(
        "event=experiment_email state=pending->accepted recipients=1 history=unchanged"
    )


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--snapshot")
    prepare.add_argument("--fresh", action="store_true")
    prepare.add_argument("--provider", choices=("adzuna", "jsearch"))
    prepare.add_argument("--output", required=True)
    rank = commands.add_parser("rank")
    rank.add_argument("--snapshot", required=True)
    rank.add_argument("--method", choices=("rules", "nebius_llm"), required=True)
    rank.add_argument("--output", required=True)
    agent = commands.add_parser("agent-input")
    agent.add_argument("--snapshot", required=True)
    agent.add_argument("--output", required=True)
    compare = commands.add_parser("compare")
    compare.add_argument("--snapshot", required=True)
    compare.add_argument("--rules", required=True)
    compare.add_argument("--direct", required=True)
    compare.add_argument("--agent")
    compare.add_argument(
        "--agent-status", choices=("success", "failed", "not_run"), default="not_run"
    )
    compare.add_argument("--output-dir", required=True)
    email = commands.add_parser("test-email")
    email.add_argument("--report", required=True)
    email.add_argument("--snapshot", required=True)
    for command in (prepare, rank, agent, compare, email):
        command.add_argument("--config", default="config.toml")
    return parser


def main(argv=None):
    """Run one manual experiment command without changing delivery history.

    Parameters
    ----------
    argv : list of str, optional
        Command-line arguments, defaulting to the current process arguments.

    Returns
    -------
    None
        Outputs are written to the explicitly requested artifact paths.
    """
    args = _parser().parse_args(argv)
    with Path(args.config).open("rb") as stream:
        config = tomllib.load(stream)
    if args.command == "prepare":
        _prepare(args, config)
    elif args.command == "test-email":
        _test_email(args, config)
    else:
        snapshot = load_snapshot(args.snapshot)
        config = _replay_config(snapshot, config)
        {"rank": _rank, "agent-input": _agent_input, "compare": _compare}[args.command](
            args,
            snapshot,
            config,
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format=f"%(asctime)s run={uuid4().hex} %(message)s"
    )
    try:
        main()
    except Exception as error:
        logging.error(
            "event=experiment state=running->failed type=%s details=redacted",
            type(error).__name__,
        )
        sys.exit(1)
