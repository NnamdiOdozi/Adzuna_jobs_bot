"""Prefer junior finance vacancies and suppress senior or repeated adverts."""

import logging
import re


def _normalise(value):
    return " ".join(re.findall(r"\w+", value.casefold()))


def _matching_terms(title, terms):
    # Padded tokens match "Sr." and "entry-level" without matching "overhead".
    normalised = f" {_normalise(title)} "
    return [term for term in terms if f" {_normalise(term)} " in normalised]


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
    """Require finance evidence, exclude senior titles and rank junior matches.

    Parameters
    ----------
    jobs : list of dict
        Candidate vacancies from the combined Adzuna search.
    seen : set of str
        Keys of advertisements already sent.
    config : dict
        Title exclusions, preferences, finance keywords and shortlist limit.

    Returns
    -------
    list of dict
        Previously unseen vacancies in rank order.
    """
    eligible, excluded = [], {}
    irrelevant = {"wrong_or_missing_category": 0, "no_finance_title_match": 0}
    for job in jobs:
        category = job.get("category")
        if not isinstance(category, dict) or category.get("tag") != config["category"]:
            irrelevant["wrong_or_missing_category"] += 1
            continue
        # Junior wording alone must never qualify a non-finance vacancy.
        if not _matching_terms(job["title"], config["title_keywords"]):
            irrelevant["no_finance_title_match"] += 1
            continue
        matches = _matching_terms(
            job["title"], config.get("exclude_title_keywords", [])
        )
        if matches:
            excluded[matches[0]] = excluded.get(matches[0], 0) + 1
        else:
            eligible.append(job)
    for reason, count in irrelevant.items():
        if count:
            logging.info(
                "event=relevance_filter state=fetched->excluded reason=%s count=%d",
                reason,
                count,
            )
    for term, count in sorted(excluded.items()):
        logging.info(
            "event=title_filter state=fetched->excluded reason=title_term "
            "term=%r count=%d",
            term,
            count,
        )
    ranked = sorted(
        eligible,
        key=lambda job: (
            bool(
                _matching_terms(
                    job["title"], config.get("preferred_title_keywords", [])
                )
            ),
            not bool(
                _matching_terms(
                    job["title"], config.get("deprioritise_title_keywords", [])
                )
            ),
            len(_matching_terms(job["title"], config["title_keywords"])),
            job["created"],
        ),
        reverse=True,
    )
    selected, used = [], set(seen)
    for job in ranked:
        keys = job_keys(job)
        if keys & used:
            continue
        selected.append(job)
        used.update(keys)
        if len(selected) >= config["shortlist_size"]:
            break
    return selected
