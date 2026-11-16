"""Validate ranking configuration and evidence without trusting model claims."""

import math

_LABELS = {"strong_fit", "possible_fit", "unlikely_fit", "insufficient_information"}
_FIELDS = ["title", "description", "location"]


def _settings(config):
    settings = config["ranking"]
    for name in (
        "batch_size",
        "max_candidates",
        "max_calls",
        "max_output_tokens",
        "timeout_seconds",
        "max_elapsed_seconds",
        "max_description_chars",
        "max_reason_chars",
        "max_evidence_chars",
    ):
        value = settings[name]
        if type(value) is not int or value <= 0:
            raise ValueError(f"ranking.{name} must be a positive integer")
    labels = settings["allowed_labels"]
    selected = settings["selected_labels"]
    if (
        not isinstance(labels, list)
        or not labels
        or any(not isinstance(item, str) for item in labels)
        or set(labels) != _LABELS
        or len(labels) != len(_LABELS)
        or not isinstance(selected, list)
        or not selected
        or any(not isinstance(item, str) or item not in labels for item in selected)
        or len(set(selected)) != len(selected)
    ):
        raise ValueError("Invalid ranking label configuration")
    if (
        not isinstance(settings["base_url"], str)
        or settings["base_url"].rstrip("/") != "https://api.tokenfactory.nebius.com/v1"
    ):
        raise ValueError(
            "Only the configured Token Factory HTTPS endpoint is permitted"
        )
    for name in ("model", "prompt_path"):
        if not isinstance(settings[name], str) or not settings[name].strip():
            raise ValueError(f"ranking.{name} must be nonempty text")
    temperature = settings["temperature"]
    if (
        type(temperature) not in (float, int)
        or not math.isfinite(temperature)
        or not 0 <= temperature <= 2
    ):
        raise ValueError("Invalid ranking temperature")
    if (
        not isinstance(config["candidate"]["profile"], str)
        or not config["candidate"]["profile"].strip()
    ):
        raise ValueError("Candidate profile must be nonempty text")
    return settings


def validate_assessments(payload, candidates, config):
    """Require complete decisions and verbatim evidence for supplied adverts.

    Parameters
    ----------
    payload : dict
        Model result containing only an assessments array.
    candidates : list of dict
        Exact prepared adverts supplied to inference.
    config : dict
        Allowed labels and reason/evidence length limits.

    Returns
    -------
    list of dict
        Validated assessments preserving model array order. Quotation checks
        establish textual presence, not semantic support or actual eligibility.
    """
    settings = _settings(config)
    by_id = {job["id"]: job for job in candidates}
    if len(by_id) != len(candidates):
        raise ValueError("Duplicate candidate IDs")
    if not isinstance(payload, dict) or set(payload) != {"assessments"}:
        raise ValueError("Invalid assessment envelope")
    rows = payload["assessments"]
    if not isinstance(rows, list) or len(rows) != len(candidates):
        raise ValueError("Assessment coverage differs from candidate pool")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "id",
            "suitability",
            "reason",
            "evidence",
        }:
            raise ValueError("Invalid assessment fields")
        identifier = row["id"]
        if (
            not isinstance(identifier, str)
            or identifier not in by_id
            or identifier in seen
        ):
            raise ValueError("Unknown or repeated assessment ID")
        seen.add(identifier)
        if row["suitability"] not in settings["allowed_labels"]:
            raise ValueError("Unknown suitability label")
        reason = row["reason"]
        if (
            not isinstance(reason, str)
            or not reason.strip()
            or len(reason) > settings["max_reason_chars"]
        ):
            raise ValueError("Invalid assessment reason")
        evidence = row["evidence"]
        if not isinstance(evidence, list) or (
            not evidence and row["suitability"] != "insufficient_information"
        ):
            raise ValueError("Assessment requires evidence")
        for item in evidence:
            if not isinstance(item, dict) or set(item) != {"field", "quote"}:
                raise ValueError("Invalid evidence fields")
            field, quote = item["field"], item["quote"]
            if (
                field not in _FIELDS
                or not isinstance(quote, str)
                or not quote.strip()
                or len(quote) > settings["max_evidence_chars"]
            ):
                raise ValueError("Invalid evidence quotation")
            value = by_id[identifier].get(field, "")
            if field == "location":
                value = value.get("display_name", "")
            if quote not in value:
                raise ValueError("Evidence quotation absent from supplied field")
    return rows
