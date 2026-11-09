"""Read Adzuna vacancies and deliver plain-text Gmail shortlists."""

import json
import logging
import smtplib
import ssl
from email.message import EmailMessage
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


def fetch_jobs(config, app_id, app_key):
    """Fetch one combined finance search, reducing a rejected page size once.

    Parameters
    ----------
    config : dict
        Search endpoint, query terms and request limits.
    app_id, app_key : str
        Adzuna credentials, used only for the Adzuna request.

    Returns
    -------
    list of dict
        First-page results; duplicates are retained for later filtering.
    """
    endpoint = urlsplit(config["base_url"])
    if endpoint.scheme != "https" or endpoint.hostname != "api.adzuna.com":
        raise ValueError("Search endpoint must be the HTTPS Adzuna API")
    requested = config["results_per_page"]
    fallback = config["fallback_results_per_page"]
    if fallback > requested:
        raise ValueError("Fallback page size must not exceed the requested size")
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what_or": " ".join(config["query_terms"]),
        "where": config["location"],
        "distance": config["distance_miles"],
        "max_days_old": config["days_old"],
        "sort_by": "date",
    }
    for attempt, limit in enumerate(dict.fromkeys((requested, fallback)), 1):
        params["results_per_page"] = limit
        request = Request(
            f"{config['base_url']}/1?{urlencode(params)}",
            headers={"Accept": "application/json"},
        )
        logging.info(
            "event=adzuna_request state=ready->requested attempt=%d "
            "results_requested=%d",
            attempt,
            limit,
        )
        try:
            # Never log URLs or response bodies: they may contain credentials.
            with urlopen(request, timeout=config["timeout_seconds"]) as response:
                rows = json.load(response)["results"]
        except HTTPError as error:
            retry = error.code == 400 and limit > fallback
            logging.warning(
                "event=adzuna_request state=requested->%s attempt=%d "
                "http_status=%d results_requested=%d",
                "fallback" if retry else "failed",
                attempt,
                error.code,
                limit,
            )
            if not retry:
                raise
            error.close()
            continue
        break
    if not isinstance(rows, list):
        raise ValueError("Adzuna results must be a list")
    for job in rows:
        for field in ("id", "title", "created", "company", "location", "redirect_url"):
            if field not in job:
                raise ValueError("Adzuna returned an incomplete vacancy")
        link = urlsplit(job["redirect_url"])
        if link.scheme not in {"http", "https"} or not link.hostname:
            raise ValueError("Adzuna returned an invalid vacancy link")
    logging.info(
        "event=adzuna_request state=requested->received attempt=%d "
        "results_requested=%d results_returned=%d",
        attempt,
        limit,
        len(rows),
    )
    return rows


def build_message(jobs, config, recipients, date):
    """Build a readable shortlist with both recipients visible.

    Parameters
    ----------
    jobs : list of dict
        Previously unseen, ranked vacancies.
    config : dict
        Sender and subject settings.
    recipients : list of str
        Email addresses included in the To field.
    date : str
        London calendar date shown in the subject.

    Returns
    -------
    email.message.EmailMessage
        Plain-text message, without remote images or HTML.
    """
    message = EmailMessage()
    message["From"] = config["sender"]
    message["To"] = ", ".join(recipients)
    message["Subject"] = f"{config['subject']} — {date} ({len(jobs)} new)"
    lines = ["Previously unseen London finance jobs, sourced from Adzuna.", ""]
    if not jobs:
        lines.append("No new matching jobs were found in the searched results today.")
    for index, job in enumerate(jobs, 1):
        lines.extend(
            [
                f"{index}. {job['title']}",
                f"{job['company'].get('display_name', 'Employer unspecified')} | "
                f"{job['location'].get('display_name', 'Location unspecified')}",
                f"Listed: {job['created']}",
                f"Salary: {job.get('salary_min', 'not supplied')} to "
                f"{job.get('salary_max', 'not supplied')} GBP"
                + (
                    " (Adzuna estimate)"
                    if str(job.get("salary_is_predicted")) == "1"
                    else ""
                ),
                job["redirect_url"],
                "",
            ]
        )
    lines.append(
        "Title rules exclude senior roles and favour junior roles, then finance "
        "keywords and listing date. Check experience and eligibility "
        "in each full advert."
    )
    message.set_content("\n".join(lines))
    return message


def send_message(message, config, password):
    """Submit the email using Gmail's encrypted SMTP connection.

    Parameters
    ----------
    message : email.message.EmailMessage
        Prepared shortlist.
    config : dict
        Gmail sender, host, port and timeout.
    password : str
        Gmail app password, never written to logs.

    Raises
    ------
    RuntimeError
        Gmail refuses any recipient; history must remain unchanged.
    """
    with smtplib.SMTP_SSL(
        config["smtp_host"],
        config["smtp_port"],
        timeout=config["timeout_seconds"],
        context=ssl.create_default_context(),
    ) as server:
        server.login(config["sender"], password)
        if server.send_message(message):
            raise RuntimeError("Gmail refused at least one recipient")
