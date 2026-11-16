"""Archive provider candidates before filtering, without delivery configuration."""

import hashlib
import json
import logging
import math
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

_SEARCH_FIELDS = frozenset(
    "provider fallback_provider location category distance_miles query_terms days_old "
    "results_per_page fallback_results_per_page shortlist_size max_experience_years "
    "timeout_seconds jsearch_top_up_threshold title_keywords exclude_title_keywords "
    "preferred_title_keywords "
    "deprioritise_title_keywords".split()
)
_JSEARCH_FIELDS = frozenset(
    "query country language num_pages date_posted radius timeout_seconds".split()
)
_JOB_TEXT = frozenset(
    "id title description created redirect_url source "
    "salary_currency salary_period".split()
)
_JOB_SALARY = frozenset("salary_min salary_max salary_is_predicted".split())
_JOB_NESTED = {
    "company": frozenset({"display_name"}),
    "location": frozenset({"display_name", "area"}),
    "category": frozenset({"tag", "label"}),
}
_KEYS = {
    "schema_version",
    "snapshot_id",
    "captured_at",
    "provider",
    "jobs",
    "seen",
    "config",
    "metadata",
    "content_hash",
}


def _plain(value):
    return (
        value is None
        or type(value) in (str, bool, int)
        or (type(value) is float and math.isfinite(value))
    )


def _config(config):
    result = {}
    for section, fields in (("search", _SEARCH_FIELDS), ("jsearch", _JSEARCH_FIELDS)):
        settings = config.get(section, {})
        if not isinstance(settings, dict):
            raise ValueError("Invalid snapshot search settings")
        result[section] = {}
        for key in fields & settings.keys():
            value = settings[key]
            if not _plain(value) and not (
                isinstance(value, list) and all(_plain(item) for item in value)
            ):
                raise ValueError("Invalid snapshot search value")
            result[section][key] = value
    return result


def _job(job):
    if not isinstance(job, dict):
        raise ValueError("Snapshot vacancy must be an object")
    result = {}
    for key in (_JOB_TEXT | _JOB_SALARY) & job.keys():
        value = job[key]
        valid = value is None or isinstance(value, str)
        if key in _JOB_SALARY:
            valid = _plain(value)
        if not valid:
            raise ValueError("Invalid snapshot vacancy value")
        result[key] = value
    for key, fields in _JOB_NESTED.items():
        if key not in job:
            continue
        value = job[key]
        if not isinstance(value, dict):
            raise ValueError("Invalid snapshot vacancy detail")
        detail = {}
        for name in fields & value.keys():
            item = value[name]
            if not isinstance(item, str) and not (
                key == "location"
                and name == "area"
                and isinstance(item, list)
                and all(isinstance(part, str) for part in item)
            ):
                raise ValueError("Invalid snapshot vacancy detail value")
            detail[name] = item
        result[key] = detail
    return result


def _hash(snapshot):
    content = {key: value for key, value in snapshot.items() if key != "content_hash"}
    encoded = json.dumps(
        content,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate(snapshot):
    if not isinstance(snapshot, dict) or set(snapshot) != _KEYS:
        raise ValueError("Invalid snapshot keys")
    if type(snapshot["schema_version"]) is not int or snapshot["schema_version"] != 1:
        raise ValueError("Unsupported snapshot schema")
    if snapshot["provider"] not in ("adzuna", "jsearch", "combined"):
        raise ValueError("Invalid snapshot provider")
    if not isinstance(snapshot["snapshot_id"], str) or not re.fullmatch(
        r"[0-9a-f]{32}", snapshot["snapshot_id"]
    ):
        raise ValueError("Invalid snapshot identity")
    if not isinstance(snapshot["captured_at"], str):
        raise ValueError("Invalid snapshot capture time")
    timestamp = datetime.fromisoformat(snapshot["captured_at"])
    if timestamp.tzinfo is None:
        raise ValueError("Snapshot capture time must include a timezone")
    if not isinstance(snapshot["jobs"], list) or any(
        _job(job) != job for job in snapshot["jobs"]
    ):
        raise ValueError("Invalid snapshot vacancies")
    if not isinstance(snapshot["seen"], list) or not all(
        isinstance(key, str) for key in snapshot["seen"]
    ):
        raise ValueError("Invalid snapshot seen keys")
    if (
        not isinstance(snapshot["config"], dict)
        or _config(snapshot["config"]) != snapshot["config"]
    ):
        raise ValueError("Invalid snapshot configuration")
    metadata = snapshot["metadata"]
    if (
        not isinstance(metadata, dict)
        or set(metadata) != {"run_id", "commit"}
        or not all(isinstance(value, str) for value in metadata.values())
    ):
        raise ValueError("Invalid snapshot metadata")
    if not isinstance(snapshot["content_hash"], str) or snapshot[
        "content_hash"
    ] != _hash(snapshot):
        raise ValueError("Snapshot content hash mismatch")


def create_snapshot(
    jobs, provider, config, seen, *, run_id="local", commit="local", captured_at=None
):
    """Build a sanitized candidate archive and bind its contents to a hash.

    Parameters
    ----------
    jobs : list of dict
        Validated provider vacancies, before suitability filtering.
    provider : str
        Actual provider: adzuna, jsearch or their combined candidate pool.
    config : dict
        Application settings; only allowlisted search settings are retained.
    seen : iterable of str
        Previously delivered job keys.
    run_id, commit : str
        Public execution identity.
    captured_at : datetime or str, optional
        Time with timezone, defaulting to current UTC time.

    Returns
    -------
    dict
        Versioned archive with a unique identity and SHA-256 content hash.
    """
    if captured_at is None:
        captured_at = datetime.now(UTC)
    if isinstance(captured_at, datetime):
        captured_at = captured_at.isoformat()
    snapshot = {
        "schema_version": 1,
        "snapshot_id": uuid4().hex,
        "captured_at": captured_at,
        "provider": provider,
        "jobs": [_job(job) for job in jobs],
        "seen": sorted(set(seen)),
        "config": _config(config),
        "metadata": {"run_id": run_id, "commit": commit},
    }
    snapshot["content_hash"] = _hash(snapshot)
    _validate(snapshot)
    return snapshot


def save_snapshot(snapshot, directory, *, filename=None):
    """Write a validated archive with an atomic rename.

    Parameters
    ----------
    snapshot : dict
        Candidate archive from create_snapshot.
    directory : str or pathlib.Path
        Destination directory, created if absent.
    filename : str, optional
        Explicit JSON basename for a requested export; defaults to the identity.

    Returns
    -------
    pathlib.Path
        Completed archive filename.
    """
    _validate(snapshot)
    if filename is None:
        filename = f"{snapshot['snapshot_id']}.json"
    if not isinstance(filename, str) or not re.fullmatch(r"[\w.-]+\.json", filename):
        raise ValueError("Snapshot export must use a JSON basename")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / filename
    pending = directory / f"{snapshot['snapshot_id']}.{uuid4().hex}.tmp"
    with pending.open("x", encoding="utf-8") as stream:
        stream.write(
            json.dumps(snapshot, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        )
    pending.replace(target)
    return target


def load_snapshot(path):
    """Read an archive, rejecting unsupported shapes or changed contents.

    Parameters
    ----------
    path : str or pathlib.Path
        Archive filename.

    Returns
    -------
    dict
        Validated candidate archive.
    """
    snapshot = json.loads(Path(path).read_text(encoding="utf-8"))
    _validate(snapshot)
    return snapshot


def record_snapshot(jobs, provider, config, seen):
    """Record diagnostics without preventing normal shortlist delivery.

    Parameters
    ----------
    jobs : list of dict
        Successful provider response before filtering.
    provider : str
        Actual provider identity.
    config : dict
        Application settings, including the optional archive section.
    seen : iterable of str
        Previously delivered job keys.

    Returns
    -------
    pathlib.Path or None
        Written archive, or None when disabled or unsuccessful.
    """
    try:
        archive = config.get("archive", {})
        if not archive.get("enabled", False):
            return None
        snapshot = create_snapshot(
            jobs,
            provider,
            config,
            seen,
            run_id=os.environ.get("GITHUB_RUN_ID", "local"),
            commit=os.environ.get("GITHUB_SHA", "local"),
        )
        path = save_snapshot(snapshot, archive["directory"])
        logging.info(
            "event=snapshot state=fetched->saved provider=%s snapshot=%s jobs=%d",
            provider,
            snapshot["snapshot_id"],
            len(jobs),
        )
        return path
    except Exception as error:
        # Error text may contain provider data or filesystem details.
        logging.warning(
            "event=snapshot state=fetched->archive_failed type=%s details=redacted",
            type(error).__name__,
        )
        return None
