"""Prefer junior finance vacancies and suppress senior or repeated adverts."""

import logging
import math
import re

_NUMBER_WORDS = dict(
    zip(
        "zero one two three four five six seven eight nine ten".split(),
        range(11),
        strict=True,
    )
)
_NUMBER = r"(?:\d+(?:\.\d+)?|\.\d+)"
_YEARS_EXPERIENCE = re.compile(
    rf"(?<![\w.,])(?P<low>{_NUMBER})\s*"
    rf"(?:(?:-|–|—|to)\s*{_NUMBER}|or more)?\s*\+?\s*years?"
    r"[’']?\s+(?:of\s+)?(?:[a-z]+\s+){0,3}experience\b"
)
_SENTENCE_BREAK = r"[!?\n]|\.(?!\d)"
_CLAUSE_BREAK = r";|(?<!\d),|,(?!\d)|\b(?:and|but)\b"
_CONDITIONAL = re.compile(
    r"\b(?:or(?!\s+more\b)|if|unless|except|alternatively|equivalent|"
    r"depending on|in lieu)\b|"
    r"\bfor\s+(?:(?:non[- ]?)?graduates?|candidates|applicants|those)\b"
)
_OPTIONAL = re.compile(r"\b(preferred|desirable|ideally|advantage|bonus)\b")
_CANDIDATE = (
    r"(?:you (?:(?:will )?need|must have)|"
    r"(?:the successful candidate|candidates|applicants) must have|"
    r"requires?|must have)"
)
_MINIMUM = r"(?:at least|(?:a )?minimum(?: of)?|no less than)"
_MANDATORY_PREFIX = re.compile(rf"(?:{_CANDIDATE}\s+)?{_MINIMUM}|{_CANDIDATE}")
_MANDATORY_SUFFIX = re.compile(r"\s+(?:is\s+)?(?:required|essential|mandatory)\b")
_NEGATED_SUFFIX = re.compile(
    r"\s+(?:is\s+)?not\s+(?:required|necessary|essential|mandatory)\b"
)
_NO_EXPERIENCE = re.compile(
    r"^no\s+(?:prior\s+|professional\s+)?experience\s+"
    r"(?:is\s+)?(?:required|necessary)\b"
)


def _experience_fit(job, max_years):
    """Return (incompatible, supported) from direct applicant requirements.

    Keep decimals intact and use the lower end of ranges. Alternative and
    conditional sentences remain unknown. Split independent requirements before
    interpreting optional wording. Unrecognized language also remains unknown.
    """
    supported = False
    for field in ("title", "description"):
        text = (job.get(field) or "").casefold()
        text = re.sub(
            r"\b(" + "|".join(_NUMBER_WORDS) + r")\b",
            lambda match: str(_NUMBER_WORDS[match[0]]),
            text,
        )
        for sentence in re.split(_SENTENCE_BREAK, text):
            # Check alternatives before splitting clauses. Otherwise an exception
            # after a semicolon or comma could be detached from its requirement.
            if _CONDITIONAL.search(sentence):
                continue
            breaks = _CLAUSE_BREAK
            if field == "title":
                breaks += r"|\s[-–—|]\s|[():]"
            for clause in re.split(breaks, sentence):
                clause = clause.strip(" *•:-")
                if _NO_EXPERIENCE.match(clause):
                    supported = True
                for match in _YEARS_EXPERIENCE.finditer(clause):
                    prefix = clause[: match.start()].strip()
                    suffix = clause[match.end() :]
                    mandatory_suffix = _MANDATORY_SUFFIX.match(suffix)
                    # A later optional skill cannot undo an immediate "required"
                    # modifier. Without that boundary, keep optional text unknown.
                    if (
                        _OPTIONAL.search(prefix)
                        or (_OPTIONAL.search(suffix) and not mandatory_suffix)
                        or _NEGATED_SUFFIX.match(suffix)
                    ):
                        continue
                    # A direct applicant subject is required. We do not borrow
                    # experience from a manager, colleague or company.
                    mandatory = _MANDATORY_PREFIX.fullmatch(prefix) or (
                        not prefix and mandatory_suffix
                    )
                    if not mandatory:
                        continue
                    if float(match["low"]) > max_years:
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
    """Require finance evidence and rank roles within the candidate experience limit.

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
    max_years = config.get("max_experience_years", 2)
    if (
        isinstance(max_years, bool)
        or not isinstance(max_years, (int, float))
        or not math.isfinite(max_years)
        or max_years < 0
    ):
        raise ValueError("max_experience_years must be a finite non-negative number")
    eligible, excluded = [], {}
    experience_supported = {}
    jsearch = config.get("provider", "adzuna") == "jsearch"
    finance_reason = "no_finance_evidence" if jsearch else "no_finance_title_match"
    irrelevant = {
        "wrong_or_missing_category": 0,
        finance_reason: 0,
        "experience_above_limit": 0,
    }
    for job in jobs:
        category = job.get("category")
        if not jsearch and (
            not isinstance(category, dict) or category.get("tag") != config["category"]
        ):
            irrelevant["wrong_or_missing_category"] += 1
            continue
        # Junior wording alone must never qualify a non-finance vacancy.
        evidence = job["title"] + (
            " " + (job.get("description") or "") if jsearch else ""
        )
        if not _matching_terms(evidence, config["title_keywords"]):
            irrelevant[finance_reason] += 1
            continue
        matches = _matching_terms(
            job["title"], config.get("exclude_title_keywords", [])
        )
        if matches:
            excluded[matches[0]] = excluded.get(matches[0], 0) + 1
            continue
        incompatible, supported = _experience_fit(job, max_years)
        if incompatible:
            irrelevant["experience_above_limit"] += 1
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
