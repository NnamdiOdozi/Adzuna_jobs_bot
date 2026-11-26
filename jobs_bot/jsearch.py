"""Fetch JSearch vacancies and translate them into the shared job record format.

The daily coordinator calls this provider when JSearch is selected directly,
when Adzuna needs backup, or when a small Adzuna batch needs supplementation.
One successful request asks for the configured pages. Temporary failures can
retry after configured delays; every attempt may affect provider credits.

Provider fields are normalized here so snapshots, ranking methods and the email
builder can reuse the same records. This module does not select suitable jobs,
save snapshots, send email or change duplicate-suppression history. Malformed
individual vacancies are logged and excluded; an entirely unusable batch fails.
"""

import json
import logging
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the API-key header to a redirected destination.
        return None


def fetch_jsearch(config, key):
    """Fetch pages with bounded retries for temporary transport/server failures.

    Parameters
    ----------
    config : dict
        Endpoint, query parameters, page budget and timeout.
    key : str
        Private OpenWeb Ninja key, supplied through runtime configuration.

    Returns
    -------
    list of dict
        Vacancies with provider-prefixed IDs and common shortlist fields.
    """
    if config["base_url"] != "https://api.openwebninja.com/jsearch/search-v2":
        raise ValueError("JSearch must use its HTTPS OpenWeb Ninja search endpoint")
    if type(config["num_pages"]) is not int or not 1 <= config["num_pages"] <= 20:
        raise ValueError("JSearch num_pages must be an integer from 1 to 20")
    params = {
        name: config[name]
        for name in (
            "query",
            "country",
            "language",
            "num_pages",
            "date_posted",
            "radius",
        )
    }
    request = Request(
        f"{config['base_url']}?{urlencode(params)}",
        headers={"x-api-key": key, "Accept": "application/json"},
    )
    delays = config.get("retry_delays_seconds", [])
    if (
        not isinstance(delays, list)
        or any(type(delay) is not int or delay < 60 for delay in delays)
        or len(delays) > 2
    ):
        raise ValueError("JSearch allows at most two retry delays, each >=60 seconds")
    for attempt in range(len(delays) + 1):
        logging.info(
            "event=jsearch_request state=ready->requested attempt=%d pages=%d",
            attempt + 1,
            config["num_pages"],
        )
        try:
            with build_opener(_NoRedirect()).open(
                request, timeout=config["timeout_seconds"]
            ) as response:
                payload = json.load(response)
            break
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            status = error.code if isinstance(error, HTTPError) else None
            retryable = status is None or 500 <= status <= 599
            if isinstance(error, HTTPError):
                error.close()
            logging.warning(
                "event=jsearch_request state=requested->failed attempt=%d "
                "http_status=%s error_type=%s retryable=%s",
                attempt + 1,
                status,
                type(error).__name__,
                retryable,
            )
            if not retryable or attempt == len(delays):
                raise
            logging.info(
                "event=jsearch_request state=failed->waiting delay_seconds=%d",
                delays[attempt],
            )
            time.sleep(delays[attempt])
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise ValueError("JSearch returned an invalid response")
    rows = payload["data"].get("jobs")
    if not isinstance(rows, list):
        raise ValueError("JSearch jobs must be a list")
    jobs = []
    rejected = 0
    for index, row in enumerate(rows, 1):
        required = (
            "job_id",
            "job_title",
            "employer_name",
            "job_location",
            "job_apply_link",
        )
        missing = [
            name
            for name in required
            if not isinstance(row, dict)
            or not isinstance(row.get(name), str)
            or not row[name].strip()
        ]
        reason = "incomplete_vacancy" if missing else None
        invalid_text = []
        if not missing:
            try:
                link = urlsplit(row["job_apply_link"])
                if link.scheme not in {"http", "https"} or not link.hostname:
                    reason = "invalid_vacancy_link"
            except ValueError:
                reason = "invalid_vacancy_link"
            invalid_text = [
                name
                for name in ("job_posted_at_datetime_utc", "job_description")
                if row.get(name) is not None and not isinstance(row[name], str)
            ]
            if invalid_text:
                reason = "invalid_vacancy_text"
        if reason:
            rejected += 1
            # A bad row must not discard the remaining complete vacancies.
            # Only fixed field names and the row number reach public logs.
            logging.warning(
                "event=jsearch_vacancy state=received->excluded row=%d "
                "reason=%s invalid_fields=%s",
                index,
                reason,
                ",".join(missing or invalid_text) or "job_apply_link",
            )
            continue
        # Optional salary fields must not crash later filtering or archiving.
        for field in ("job_salary_currency", "job_salary_period"):
            if row.get(field) is not None and not isinstance(row[field], str):
                logging.warning(
                    "event=jsearch_salary state=received->unknown row=%d field=%s",
                    index,
                    field,
                )
                row = {**row, field: None}
        jobs.append(
            {
                "id": f"jsearch:{row['job_id']}",
                "title": row["job_title"],
                "company": {"display_name": row["employer_name"]},
                "location": {"display_name": row["job_location"]},
                "created": row.get("job_posted_at_datetime_utc") or "",
                "redirect_url": row["job_apply_link"],
                "description": row.get("job_description") or "",
                "source": "JSearch",
                "salary_min": row.get("job_min_salary") or "not supplied",
                "salary_max": row.get("job_max_salary") or "not supplied",
                "salary_currency": row.get("job_salary_currency")
                or "currency not supplied",
                "salary_period": row.get("job_salary_period") or "",
            }
        )
    logging.info(
        "event=jsearch_request state=requested->received jobs=%d pages=%d "
        "returned=%d rejected=%d",
        len(jobs),
        config["num_pages"],
        len(rows),
        rejected,
    )
    if rows and not jobs:
        raise ValueError("JSearch returned no usable vacancies")
    return jobs
