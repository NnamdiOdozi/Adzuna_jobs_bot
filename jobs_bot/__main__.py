"""Run a preview or send a shortlist and retain the sent-job history."""

import argparse
import json
import logging
import os
import sys
import tomllib
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from jobs_bot.services import build_message, fetch_jobs, send_message
from jobs_bot.shortlist import job_keys, select_jobs


def _run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--send", action="store_true", help="Send email and update history"
    )
    parser.add_argument("--config", default="config.toml")
    args = parser.parse_args()
    with Path(args.config).open("rb") as stream:
        config = tomllib.load(stream)
    search = config["search"]
    for name in ("pages_per_query", "results_per_page", "shortlist_size", "days_old"):
        if not isinstance(search[name], int) or search[name] <= 0:
            raise ValueError("Search limits must be positive integers")
    history_path = Path(config["history"]["path"])
    history = json.loads(history_path.read_text()) if history_path.exists() else []
    if not isinstance(history, list) or not all(
        isinstance(key, str) for key in history
    ):
        raise ValueError("Sent-job history must be a list of keys")
    seen = set(history)
    password = os.environ["gmail_app_password"] if args.send else None
    # Addresses come from runtime settings, never the public configuration file.
    config["email"]["sender"] = os.environ["gmail_sender"].strip()
    if not os.environ["email_user"].strip():
        raise ValueError("The main recipient address is required")
    addresses = (os.environ["email_user"], os.environ.get("email_friend", ""))
    recipients = list(
        dict.fromkeys(address.strip() for address in addresses if address.strip())
    )
    if not recipients or any(
        "@" not in address or "\n" in address or "\r" in address or "," in address
        for address in [config["email"]["sender"], *recipients]
    ):
        raise ValueError("Each recipient setting must contain one email address")
    # Keep these names identical to the local setup and GitHub Actions mapping.
    jobs = fetch_jobs(search, os.environ["ADZUNA_APP_ID"], os.environ["ADZUNA_API_KEY"])
    selected = select_jobs(jobs, seen, search)
    logging.info(
        "event=shortlist fetched=%d selected=%d history_keys=%d mode=%s",
        len(jobs),
        len(selected),
        len(seen),
        "send" if args.send else "preview",
    )
    date = datetime.now(ZoneInfo(config["email"]["timezone"])).date().isoformat()
    message = build_message(selected, config["email"], recipients, date)
    if not args.send:
        # Preview only the body so recipient addresses stay out of Actions logs.
        print(message.get_content())
        return
    send_message(message, config["email"], password)
    logging.info("event=email state=pending->accepted recipients=%d", len(recipients))
    for job in selected:
        seen.update(job_keys(job))
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(sorted(seen), indent=2) + "\n")
    logging.info("event=history state=loaded->saved keys=%d", len(seen))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format=f"%(asctime)s run={uuid4().hex} %(message)s"
    )
    try:
        _run()
    except Exception as error:
        # HTTP and SMTP exceptions can embed credentials, URLs or recipient addresses.
        logging.error(
            "event=failed type=%s details=redacted check=configuration_or_service",
            type(error).__name__,
        )
        sys.exit(1)
