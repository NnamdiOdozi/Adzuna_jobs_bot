"""Fetch one budgeted JSearch batch and translate vacancies for the shortlist."""

import json
import logging
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the API-key header to a redirected destination.
        return None


def fetch_jsearch(config, key):
    """Fetch configured pages once, without retries or following the cursor.

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
    logging.info(
        "event=jsearch_request state=ready->requested pages=%d", config["num_pages"]
    )
    try:
        with build_opener(_NoRedirect()).open(
            request, timeout=config["timeout_seconds"]
        ) as response:
            payload = json.load(response)
    except HTTPError as error:
        logging.error(
            "event=jsearch_request state=requested->failed http_status=%d", error.code
        )
        error.close()
        raise
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise ValueError("JSearch returned an invalid response")
    rows = payload["data"].get("jobs")
    if not isinstance(rows, list):
        raise ValueError("JSearch jobs must be a list")
    jobs = []
    for row in rows:
        required = (
            "job_id",
            "job_title",
            "employer_name",
            "job_location",
            "job_apply_link",
        )
        if not isinstance(row, dict) or any(
            not isinstance(row.get(name), str) or not row[name].strip()
            for name in required
        ):
            raise ValueError("JSearch returned an incomplete vacancy")
        link = urlsplit(row["job_apply_link"])
        if link.scheme not in {"http", "https"} or not link.hostname:
            raise ValueError("JSearch returned an invalid vacancy link")
        if any(
            row.get(name) is not None and not isinstance(row[name], str)
            for name in ("job_posted_at_datetime_utc", "job_description")
        ):
            raise ValueError("JSearch returned invalid vacancy text")
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
        "event=jsearch_request state=requested->received jobs=%d pages=%d",
        len(jobs),
        config["num_pages"],
    )
    return jobs
