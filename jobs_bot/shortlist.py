"""Rank finance vacancies and identify repeated advertisements."""

import re


def _normalise(value):
    return " ".join(re.findall(r"\w+", value.casefold()))


def job_keys(job):
    """Identify a listing by source ID and employer/title/location.

    Parameters
    ----------
    job : dict
        Adzuna vacancy with an ID, employer, title and location.

    Returns
    -------
    set of str
        Keys used to suppress repeated listings and probable reposts.
    """
    keys = {"id:" + str(job["id"])}
    parts = [
        job["title"],
        job["company"].get("display_name", ""),
        job["location"].get("display_name", ""),
    ]
    if all(parts):
        keys.add("role:" + "|".join(_normalise(part) for part in parts))
    return keys


def select_jobs(jobs, seen, config):
    """Rank matching titles, preferring recent ads, and remove duplicates.

    Parameters
    ----------
    jobs : list of dict
        Candidate vacancies from all search queries.
    seen : set of str
        Keys of advertisements already sent.
    config : dict
        Search keywords and maximum shortlist size.

    Returns
    -------
    list of dict
        Previously unseen vacancies in rank order.
    """
    ranked = sorted(
        jobs,
        key=lambda job: (
            sum(
                word.casefold() in job["title"].casefold()
                for word in config["title_keywords"]
            ),
            job["created"],
        ),
        reverse=True,
    )
    selected, used = [], set(seen)
    for job in ranked:
        if any(
            word.casefold() in job["title"].casefold()
            for word in config.get("exclude_title_keywords", [])
        ):
            continue
        keys = job_keys(job)
        if keys & used:
            continue
        selected.append(job)
        used.update(keys)
        if len(selected) >= config["shortlist_size"]:
            break
    return selected
