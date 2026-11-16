"""Prefer junior finance vacancies and suppress senior or repeated adverts."""

import logging
import re


_NUMBER_WORDS = dict(
    zip("zero one two three four five six seven eight nine ten".split(), range(11))
)
_YEARS_EXPERIENCE = re.compile(
    r"\b(?P<low>\d+)\s*(?:(?:-|–|—|to)\s*\d+|or more)?\s*\+?\s*years?"
    r"[’']?\s+(?:of\s+)?(?:[a-z]+\s+){0,3}experience\b"
)


def _experience_fit(job):
    """Return (incompatible, supported) from explicit experience wording.

    Use the lower end of ranges. Optional experience and upper bounds do not
    establish a minimum. Missing or unrecognized wording remains uncertain.
    This is a bounded English-language heuristic, not an eligibility decision.
    """
    supported = False
    title = re.sub(r"\s[-–—|]\s", "\n", job["title"])
    text = title + "\n" + (job.get("description") or "")
    for clause in re.split(r"[.!?;,\n]|\bbut\b", text.casefold()):
        clause = re.sub(
            r"\b(" + "|".join(_NUMBER_WORDS) + r")\b",
            lambda match: str(_NUMBER_WORDS[match[0]]),
            clause,
        )
        if re.search(r"\b(preferred|desirable|ideally|advantage|bonus)\b", clause):
            continue
        if re.search(
            r"\bno\s+(?:prior\s+|professional\s+)?experience\s+"
            r"(?:is\s+)?(?:required|necessary)\b", clause
        ):
            supported = True
        for match in _YEARS_EXPERIENCE.finditer(clause):
            prefix = clause[:match.start()].strip(" *•:-")
            suffix = clause[match.end():]
            # Only accept a direct requirement on the applicant. A manager's
            # or employer's experience, and bare numbers, remain uncertain.
            candidate = (
                r"(?:you (?:need|must have)|(?:candidates|applicants) must have|"
                r"requires?|must have)"
            )
            minimum = r"(?:at least|(?:a )?minimum(?: of)?|no less than)"
            mandatory_prefix = re.fullmatch(
                rf"(?:{candidate}\s+)?{minimum}|{candidate}", prefix
            )
            mandatory_suffix = not prefix and re.match(
                r"\s+(?:is\s+)?(?:required|essential|mandatory)\b", suffix
            )
            if not (mandatory_prefix or mandatory_suffix):
                continue
            if int(match["low"]) > 2:
                return True, False
            supported = True
    return False, supported


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
        Normalized vacancy with an ID, employer, title and location.

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
    """Require finance evidence and rank roles for a 0–2-year candidate.

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
    experience_supported = {}
    jsearch = config.get("provider", "adzuna") == "jsearch"
    finance_reason = "no_finance_evidence" if jsearch else "no_finance_title_match"
    irrelevant = {
        "wrong_or_missing_category": 0,
        finance_reason: 0,
        "experience_above_two_years": 0,
    }
    for job in jobs:
        category = job.get("category")
        if not jsearch and (
            not isinstance(category, dict) or category.get("tag") != config["category"]
        ):
            irrelevant["wrong_or_missing_category"] += 1
            continue
        # Junior wording alone must never qualify a non-finance vacancy.
        evidence = job["title"] + (" " + (job.get("description") or "") if jsearch else "")
        if not _matching_terms(evidence, config["title_keywords"]):
            irrelevant[finance_reason] += 1
            continue
        matches = _matching_terms(
            job["title"], config.get("exclude_title_keywords", [])
        )
        if matches:
            excluded[matches[0]] = excluded.get(matches[0], 0) + 1
            continue
        incompatible, supported = _experience_fit(job)
        if incompatible:
            irrelevant["experience_above_two_years"] += 1
            continue
        experience_supported[id(job)] = supported
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
            experience_supported[id(job)],
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
