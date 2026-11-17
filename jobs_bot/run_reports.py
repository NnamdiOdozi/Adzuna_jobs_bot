"""Save numbered vacancies and the email trail, then publish a readable run report.

The daily coordinator records its selection before attempting email and updates
the submission state afterwards. This module owns those report files. A later
Actions step publishes their Markdown on the run page; the archive workflow can
then preserve the same files without rerunning a search or a model.
"""

import argparse
import html
import json
import logging
import os
import tomllib
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlsplit
from zoneinfo import ZoneInfo

from jobs_bot.snapshots import create_snapshot, load_snapshot


def _text(value):
    text = html.escape(str(value)).replace("\n", " ").replace("\r", " ")
    for character in "\\`*_[]|":
        text = text.replace(character, "\\" + character)
    return text


def _vacancy(job):
    title, url = _text(job.get("title", "Untitled")), job.get("redirect_url", "")
    parsed = urlsplit(url)
    if parsed.scheme in {"https", "http"} and parsed.hostname:
        url = quote(url, safe=":/?&=%#@+-._~")
        return f"[{title}](<{url}>)"
    return title


def _candidates(jobs, config):
    run_id = os.environ.get("GITHUB_RUN_ID")
    if run_id:
        snapshots = [
            load_snapshot(path)
            for path in Path(config["archive"]["directory"]).glob("*.json")
        ]
        snapshots = sorted(
            (s for s in snapshots if s["metadata"]["run_id"] == run_id),
            key=lambda s: s["captured_at"],
        )
        # The combined snapshot repeats its component batches, so count those
        # components once rather than doubling the fetched total.
        parts = [s for s in snapshots if s["provider"] != "combined"]
        if parts:
            jobs = [job for snapshot in parts for job in snapshot["jobs"]]
    cleaned = create_snapshot(jobs, "combined", config, ())["jobs"]
    return [{**job, "fetched_index": i} for i, job in enumerate(cleaned, 1)]


def _assessments(records, indices):
    return [
        {**row, "fetched_index": indices.get(str(row["id"]))}
        for record in records
        for row in (record.get("receipt") or {}).get("assessments", [])
    ]


def _markdown(report, candidates, assessments, shortlist):
    by_id = {str(row["id"]): row for row in assessments}
    positions = {job["fetched_index"]: job["email_index"] for job in shortlist}
    states = {
        "preview": "Preview only; no email submitted",
        "prepared": "Email prepared; acceptance has not been recorded",
        "accepted": "Gmail accepted the message; history completion not recorded",
        "accepted_history_saved": "Gmail accepted the message; delivery history saved",
        "submission_failed_or_unknown": "Submission failed or acceptance is unknown",
        "failed": "Run failed before a complete email report was recorded",
        "no_new_report": "No new email report; the run may have stopped at a guard",
    }
    lines = [
        "# Daily job bulletin",
        "",
        f"Date: {_text(report['date'])} · Mode: {_text(report['mode'])}",
        f"Run: {_text(report['run_id'])} · Code: {_text(report['commit'])}",
        "",
        f"**Delivery:** {states[report['state']]}",
        f"**Fetched:** {len(candidates)} · **Assessed:** {len(assessments)} · "
        f"**Selected:** {len(shortlist)} · **Ranking:** {_text(report['method'])}",
        f"**Source:** {_text(report['provider'])} · "
        f"**Model:** {_text(report['model'])} · "
        f"**Model requests:** {report['model_calls']}",
        "",
        "Gmail acceptance is not proof of inbox delivery. Test mode preserves history.",
        "",
        "## Selected jobs",
        "",
        "| Email # | Fetched # | Vacancy | Employer / location | "
        "Assessment | Fit probability / score |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for job in shortlist:
        row = by_id.get(str(job["id"]), {})
        probabilities = row.get("probabilities", {})
        combined = probabilities.get("strong_fit", 0)
        combined += probabilities.get("possible_fit", 0)
        fit = f"{combined:.1%}" if probabilities else str(row.get("score", "—"))
        details = f"{job.get('company', {}).get('display_name', '')} / "
        details += job.get("location", {}).get("display_name", "")
        category = row.get(
            "suitability", "rules" if report["method"] == "rules" else "Not recorded"
        )
        lines.append(
            f"| {job['email_index']} | {job['fetched_index']} | {_vacancy(job)} | "
            f"{_text(details)} | {_text(category)} | {fit} |"
        )
    if not shortlist:
        lines.extend(["", "No jobs selected. See the saved email body for any notice."])
    lines.extend(
        [
            "",
            "## All fetched vacancies",
            "",
            "| Fetched # | Vacancy | Assessment | Strong | Possible | "
            "Unlikely | Unknown | Email # |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for job in candidates:
        row = by_id.get(str(job["id"]), {})
        probabilities = row.get("probabilities", {})
        cells = " | ".join(
            f"{probabilities[key]:.1%}" if key in probabilities else "—"
            for key in (
                "strong_fit",
                "possible_fit",
                "unlikely_fit",
                "insufficient_information",
            )
        )
        lines.append(
            f"| {job['fetched_index']} | {_vacancy(job)} | "
            f"{_text(row.get('suitability', 'Not assessed by a model'))} | "
            f"{cells} | {positions.get(job['fetched_index'], '—')} |"
        )
    lines.extend(
        [
            "",
            "Fetched numbers refer to this run, not permanent job identifiers.",
            "Not assessed can mean rules mode, a seen/duplicate job "
            "or a candidate limit.",
            "For Jev, strong/possible categories pass; "
            "their summed probabilities order accepted jobs.",
            "There is no additional probability threshold. These estimates",
            "and valid output do not prove job suitability.",
            "",
            "Download **job-run-report** for numbered JSON and **email.txt** "
            "(the exact prepared body, without recipient headers).",
            "",
        ]
    )
    return "\n".join(lines)


def record_run(jobs, selected, config, records, *, date, mode, state, message=None):
    """Save public report data without letting reporting prevent email delivery.

    Parameters
    ----------
    jobs, selected : list of dict
        Fetched vacancies and the final shortlist in email order.
    config : dict
        Report paths, search settings and ranking method; never copied wholesale.
    records : list of dict
        Model assessment records already validated by the ranking adapter.
    date, mode, state : str
        London date, preview/test/send mode and observed delivery stage.
    message : email.message.EmailMessage, optional
        Prepared email; only its subject and body are retained, never headers.

    Returns
    -------
    bool
        Whether the report was saved; failure is logged without sending again.
    """
    settings = config.get("report", {})
    if not settings.get("enabled", False):
        return False
    try:
        candidates = _candidates(jobs, config)
        indices = {}
        for job in candidates:
            indices.setdefault(str(job["id"]), job["fetched_index"])
        clean_selected = create_snapshot(selected, "combined", config, ())["jobs"]
        shortlist = [
            {**job, "email_index": i, "fetched_index": indices.get(str(job["id"]))}
            for i, job in enumerate(clean_selected, 1)
        ]
        assessments = _assessments(records, indices)
        report = {
            "date": date,
            "mode": mode,
            "state": state,
            "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
            "commit": os.environ.get("GITHUB_SHA", "local"),
            "method": config["ranking"]["method"],
            "provider": config.get("email", {}).get("source", "See candidate records"),
            "model": next(
                (
                    r["receipt"]["model"]
                    for r in records
                    if (r.get("receipt") or {}).get("model")
                ),
                "None / unavailable",
            ),
            "model_calls": sum(
                (r.get("receipt") or {}).get("calls", 0) for r in records
            ),
            "fetched": len(candidates),
            "assessed": len(assessments),
            "selected": len(shortlist),
            "subject": str(message["Subject"]) if message else None,
            "ranking_records": records,
        }
        directory = Path(settings["directory"])
        directory.mkdir(parents=True, exist_ok=True)
        for name, value in {
            "report": report,
            "candidates": candidates,
            "assessments": assessments,
            "shortlist": shortlist,
        }.items():
            (directory / f"{name}.json").write_text(
                json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                encoding="utf-8",
            )
        if message is not None:
            (directory / "email.txt").write_text(
                message.get_content(), encoding="utf-8"
            )
        (directory / "summary.md").write_text(
            _markdown(report, candidates, assessments, shortlist), encoding="utf-8"
        )
        logging.info("event=run_report state=updated status=%s", state)
        return True
    except Exception as error:
        logging.warning("event=run_report state=failed type=%s", type(error).__name__)
        return False


def main():
    """Publish the saved report, or explain an incomplete run, in Actions."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.toml")
    args = parser.parse_args()
    with Path(args.config).open("rb") as stream:
        config = tomllib.load(stream)
    if not config.get("report", {}).get("enabled", False):
        return
    directory = Path(config["report"]["directory"])
    if not (directory / "summary.md").exists():
        records = [
            json.loads(path.read_text())
            for path in Path(config["ranking"]["receipt_directory"]).glob(
                "ranking-*.json"
            )
        ]
        state = (
            "failed" if os.environ.get("RUN_OUTCOME") == "failure" else "no_new_report"
        )
        if not record_run(
            [],
            [],
            config,
            records,
            date=datetime.now(ZoneInfo(config["email"]["timezone"])).date().isoformat(),
            mode=os.environ.get("RUN_MODE", "unknown"),
            state=state,
        ):
            raise RuntimeError("Readable run report could not be saved")
    with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as stream:
        stream.write((directory / "summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
