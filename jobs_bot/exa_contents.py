"""Enrich unseen vacancies with Exa text before the daily coordinator ranks them.

Provider snapshots retain the original extracts. Returned records keep those
extracts alongside the longer text used by Jev and saved in the run report.
One bounded contents request is made per selection batch; failures leave the
original descriptions usable so extraction cannot prevent the morning email.
"""

import json
import logging
import os
import time
from datetime import UTC, datetime
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from jobs_bot.screening import screen_jobs
from jobs_bot.shortlist import job_keys


def enrich_jobs(jobs, seen, config):
    """Return enriched copies, skipping delivered roles and duplicate URLs."""
    settings = config.get("exa", {})
    if not settings.get("enabled", False):
        return jobs
    output = [dict(job) for job in jobs]
    eligible = {
        str(j["id"]) for j in screen_jobs(jobs, config.get("search", {}), "combined")
    }
    used, targets = set(seen), {}
    for job in output:
        if str(job["id"]) not in eligible:
            continue
        keys = job_keys(job)
        if keys & used:
            continue
        used.update(keys)
        url = job.get("redirect_url", "")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username:
            continue
        if url not in targets and len(targets) >= min(
            100, max(0, settings["max_pages"])
        ):
            continue
        targets.setdefault(url, []).append(job)
    if not targets:
        return output
    started = time.monotonic()
    for group in targets.values():
        for job in group:
            job["original_description"] = job.get("description", "")
            job["exa_status"] = "unavailable"
    try:
        # Authentication is sent only to Exa's fixed endpoint, never advert URLs.
        request = Request(
            "https://api.exa.ai/contents",
            data=json.dumps({"urls": list(targets), "text": True}).encode(),
            headers={
                "x-api-key": os.environ["EXA_API_KEY"],
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=settings["timeout_seconds"]) as response:
            payload = json.load(response)
        fetched_at = datetime.now(UTC).isoformat()
        for result in payload.get("results", []):
            url, text = result.get("url"), result.get("text")
            if url not in targets or not isinstance(text, str) or not text.strip():
                continue
            for job in targets[url]:
                # More text is useful evidence, not proof of advert completeness.
                if len(text) > len(job["original_description"]):
                    job.update(
                        description=text,
                        exa_status="enriched",
                        exa_url=url,
                        exa_fetched_at=fetched_at,
                    )
                else:
                    job["exa_status"] = "original_longer"
    except Exception as error:
        # Never log HTTP bodies or headers: they can contain sensitive diagnostics.
        logging.warning(
            "event=exa state=requested->fallback error_type=%s", type(error).__name__
        )
    enriched = sum(job.get("exa_status") == "enriched" for job in output)
    logging.info(
        "event=exa state=requested->completed pages=%d enriched=%d "
        "elapsed_seconds=%.2f",
        len(targets),
        enriched,
        time.monotonic() - started,
    )
    return output
