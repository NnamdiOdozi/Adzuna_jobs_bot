"""Apply exact salary limits before the daily coordinator chooses a ranker.

The coordinator passes fetched records and search settings to ``screen_jobs``.
It returns the retained original records, so rules, Jev and Qwen share the same
salary cap. Raw snapshots are saved before this step. Unknown pay information
remains eligible; model suitability must not depend on invented annual salaries.
"""

import logging
import math
import re


def screen_jobs(jobs, settings, provider):
    """Exclude known annual GBP pay above the configured upper limit."""
    limit = settings.get("max_salary_gbp")
    if limit is None:
        return jobs
    if type(limit) not in (int, float) or not math.isfinite(limit) or limit <= 0:
        raise ValueError("max_salary_gbp must be a positive finite number")
    retained = []
    for job in jobs:
        # Adzuna's GBP search salaries are annual even without explicit units.
        adzuna = job.get("source", provider).lower() == "adzuna"
        currency = job.get("salary_currency") or ("GBP" if adzuna else "")
        period = job.get("salary_period") or ("YEAR" if adzuna else "")
        values = [
            value
            for name in ("salary_min", "salary_max")
            if type(value := job.get(name)) in (int, float)
            and math.isfinite(value)
            and value > 0
        ]
        comparable = currency.upper() == "GBP" and period.upper() in {
            "YEAR",
            "ANNUAL",
            "YEARLY",
            "ANNUALLY",
        }
        excluded = comparable and values and max(values) > limit
        logging.info(
            "event=salary_screen state=fetched->%s job_id=%s limit_gbp=%s "
            "currency=%s period=%s reason=%s",
            "excluded" if excluded else "retained",
            job.get("id", "unknown"),
            limit,
            currency,
            period,
            "above_cap"
            if excluded
            else "within_cap"
            if comparable and values
            else "pay_not_comparable",
        )
        if not excluded:
            retained.append(job)
    return retained


def salary_details(job, assessment):
    """Attach copied advert pay and Jev's category without estimating a salary.

    Only interpret explicit salary phrases when Jev found current base pay.
    Unknown or commission-only pay stays null. Numeric provider fields remain
    untouched; these separate fields show exactly what the extra check added.
    """
    category = assessment["salary_category"]
    result = {
        "category": category,
        "probabilities": assessment["salary_probabilities"],
        "min": None,
        "max": None,
        "currency": None,
        "period": None,
        "source": "not_established",
        "evidence": None,
    }
    if category == "unknown":
        return result
    number = r"\d[\d,]*(?:\.\d+)?[kK]?"
    match = re.search(
        rf"salary(?:\s+(?:ranging from|of|is))?\s*:?\s*"
        rf"(?P<upper>up to\s+)?(?:£|GBP\s*)\s*(?P<first>{number})"
        rf"(?:\s*(?:to|[-–—])\s*(?:£|GBP\s*)?\s*(?P<last>{number}))?",
        job.get("description", ""),
        re.IGNORECASE,
    )
    if not match:
        return result

    def amount(value):
        multiplier = 1000 if value.lower().endswith("k") else 1
        return float(value.lower().removesuffix("k").replace(",", "")) * multiplier

    first = amount(match["first"])
    last = amount(match["last"]) if match["last"] else first
    context = job["description"][max(0, match.start() - 30) : match.end() + 30]
    result.update(
        min=None if match["upper"] else first,
        max=last,
        currency="GBP",
        period="YEAR"
        if re.search(r"annual|per annum|per year|p\.a\.", context, re.I)
        else None,
        source="advert_description",
        evidence=match.group(0),
    )
    return result
