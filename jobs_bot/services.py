"""Read Adzuna vacancies and deliver plain-text Gmail shortlists."""

import json
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


def fetch_jobs(config, app_id, app_key):
    """Fetch bounded pages of recent London vacancies over HTTPS.

    Parameters
    ----------
    config : dict
        Search endpoint, query terms and request limits.
    app_id, app_key : str
        Adzuna credentials, used only for the Adzuna request.

    Returns
    -------
    list of dict
        Combined results; duplicates are retained for later filtering.
    """
    endpoint = urlsplit(config["base_url"])
    if endpoint.scheme != "https" or endpoint.hostname != "api.adzuna.com":
        raise ValueError("Search endpoint must be the HTTPS Adzuna API")
    jobs = []
    for query in config["queries"]:
        for page in range(1, config["pages_per_query"] + 1):
            params = {
                "app_id": app_id,
                "app_key": app_key,
                "what": query,
                "where": config["location"],
                "distance": config["distance_miles"],
                "max_days_old": config["days_old"],
                "sort_by": "date",
                "results_per_page": config["results_per_page"],
            }
            request = Request(
                f"{config['base_url']}/{page}?{urlencode(params)}",
                headers={"Accept": "application/json"},
            )
            # Never log the request URL: Adzuna authenticates in its query string.
            with urlopen(request, timeout=config["timeout_seconds"]) as response:
                rows = json.load(response)["results"]
            if not isinstance(rows, list):
                raise ValueError("Adzuna results must be a list")
            for job in rows:
                for field in (
                    "id",
                    "title",
                    "created",
                    "company",
                    "location",
                    "redirect_url",
                ):
                    if field not in job:
                        raise ValueError("Adzuna returned an incomplete vacancy")
                link = urlsplit(job["redirect_url"])
                if link.scheme not in {"http", "https"} or not link.hostname:
                    raise ValueError("Adzuna returned an invalid vacancy link")
            jobs.extend(rows)
            if len(rows) < config["results_per_page"]:
                break
    return jobs


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
        "Ranking uses job-title keywords, then listing date. Check each full advert."
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
