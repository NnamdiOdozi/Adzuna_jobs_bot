"""Preserve selected Actions evidence as inert files in this repository.

The independent archive workflow calls this module after a daily or comparison
run. GitHub's CLI supplies authenticated downloads; ZIP members are validated
in memory and never executed or extracted. Only known producer filenames enter
the permanent archive. Original bytes and their hashes remain together so a
later review can identify exactly which evidence came from each source run.
"""

import argparse
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import time
import tomllib
from datetime import datetime
from pathlib import Path, PurePosixPath
from zipfile import ZipFile
from zoneinfo import ZoneInfo

ARTIFACT_FILES = {
    "job-candidates": r"(?:[0-9a-f]{32}|snapshot)\.json",
    "job-ranking-receipts": r"ranking-[0-9a-f]{32}\.json",
    "job-run-report": (
        r"(?:(?:report|candidates|assessments|shortlist)\.json|summary\.md|email\.txt)"
    ),
    "ranking-input": r"(?:snapshot|rules|agent-input)\.json",
    "ranking-direct": r"direct\.json",
    "ranking-agent": r"agent-assessments\.json",
    "ranking-comparison": r"comparison\.(?:json|md)",
}
SOURCE_WORKFLOWS = {
    ".github/workflows/daily-jobs.yml",
    ".github/workflows/ranking-experiment.yml",
}
_FOLDER = (
    r"(?:[1-9][0-9]*|[0-9]{4}-[0-9]{2}-[0-9]{2}_"
    r"[0-9]{2}-[0-9]{2}-[0-9]{2}_[A-Z0-9+-]{2,8}(?:--[1-9][0-9]*)?)"
)
_SAFE_VALIDATION_REASONS = frozenset(
    {
        "Invalid repository",
        "Invalid source run ID",
        "Source creation time must include a timezone",
        "Multiple archive folders match the source run",
        "Invalid permanent archive request settings",
        "Source run is not on the default branch; branch experiments are not archived",
        "Source must be a completed trusted default-branch run",
        "Approved artifact expired or duplicated",
        "Invalid artifact ID",
        "No approved artifacts remain for this run",
        "Artifact exceeds archive safety limits",
        "Unsafe artifact member",
        "Unexpected artifact evidence filename",
        "Duplicate artifact member",
        "Artifact contains no evidence",
        "Non-finite JSON value",
        "Archive destination contains a symlink",
        "Archive evidence conflicts with existing data",
    }
)


def archive_data_path(path):
    """Recognize only the archive's known evidence paths for the code-test gate.

    Parameters
    ----------
    path : str
        Repository-relative path changed since the last tested commit.

    Returns
    -------
    bool
        Whether this is a data filename owned by the archive writer.
    """
    parts = path.split("/")
    if len(parts) not in (3, 4) or parts[0] != "archive":
        return False
    if not re.fullmatch(_FOLDER, parts[1]):
        return False
    if len(parts) == 3:
        return parts[2] == "manifest.json"
    return bool(re.fullmatch(ARTIFACT_FILES.get(parts[2], r"(?!)"), parts[3]))


def _request_settings(path=Path("config.toml")):
    settings = tomllib.loads(path.read_text())["permanent_archive"]
    timeout = settings.get("request_timeout_seconds")
    attempts = settings.get("request_attempts")
    delays = settings.get("retry_delays_seconds")
    if (
        type(timeout) is not int
        or timeout <= 0
        or type(attempts) is not int
        or attempts <= 0
        or not isinstance(delays, list)
        or len(delays) != attempts - 1
        or any(type(delay) is not int or delay <= 0 for delay in delays)
    ):
        raise ValueError("Invalid permanent archive request settings")
    return timeout, attempts, delays


def _api(repository, endpoint, *, binary=False):
    # Only repeat safe reads after timeouts or explicit HTTP server failures.
    # Authentication, expiry and malformed content need an operator's attention.
    timeout, attempts, delays = _request_settings()
    for attempt in range(attempts):
        try:
            result = subprocess.run(
                ["gh", "api", f"repos/{repository}/{endpoint}"],
                check=True,
                capture_output=True,
                timeout=timeout,
            )
            break
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as error:
            transient = isinstance(error, subprocess.TimeoutExpired) or bool(
                re.search(rb"\(HTTP 5[0-9]{2}\)", error.stderr or b"")
            )
            if not transient or attempt == attempts - 1:
                raise
            print(f"event=archive_read state=failed->retry attempt={attempt + 1}")
            time.sleep(delays[attempt])
    return result.stdout if binary else json.loads(result.stdout)


def _members(name, content):
    files = {}
    with ZipFile(io.BytesIO(content)) as archive:
        # Bound both expanded bytes and entry count before reading any member.
        entries = archive.infolist()
        if len(entries) > 1000 or sum(e.file_size for e in entries) > 100_000_000:
            raise ValueError("Artifact exceeds archive safety limits")
        for entry in entries:
            path = PurePosixPath(entry.filename)
            mode = entry.external_attr >> 16
            if (
                len(path.parts) != 1
                or entry.filename != path.name
                or "\\" in entry.filename
                or stat.S_ISLNK(mode)
                or entry.is_dir()
            ):
                raise ValueError("Unsafe artifact member")
            if not re.fullmatch(ARTIFACT_FILES[name], entry.filename):
                raise ValueError("Unexpected artifact evidence filename")
            if entry.filename in files:
                raise ValueError("Duplicate artifact member")
            data = archive.read(entry)
            text = data.decode("utf-8")
            if path.suffix == ".json":
                json.loads(text, parse_constant=lambda _: _invalid_json())
            files[entry.filename] = data
    if not files:
        raise ValueError("Artifact contains no evidence")
    return files


def _invalid_json():
    raise ValueError("Non-finite JSON value")


def _destination(root, run, timezone):
    """Use the source creation time, retaining existing run folders on retries."""
    created = datetime.fromisoformat(run["created_at"])
    if created.tzinfo is None:
        raise ValueError("Source creation time must include a timezone")
    local = created.astimezone(ZoneInfo(timezone))
    if root.is_symlink():
        raise ValueError("Archive destination contains a symlink")
    matches = []
    for folder in root.iterdir() if root.exists() else ():
        if not re.fullmatch(_FOLDER, folder.name):
            continue
        manifest = folder / "manifest.json"
        if folder.is_symlink() or manifest.is_symlink():
            raise ValueError("Archive destination contains a symlink")
        if manifest.is_file():
            if str(json.loads(manifest.read_text())["source_run_id"]) == str(run["id"]):
                matches.append(folder)
    if len(matches) > 1:
        raise ValueError("Multiple archive folders match the source run")
    if matches:
        return matches[0], {}
    destination = root / local.strftime("%Y-%m-%d_%H-%M-%S_%Z")
    if destination.exists():
        # Distinct runs can start within the same second. Never merge their data.
        destination = root / f"{destination.name}--{run['id']}"
    timing = {
        "source_created_at": run["created_at"],
        "source_local_time": local.isoformat(),
        "archive_timezone": timezone,
    }
    return destination, timing


def preserve_run(repository, run_id, branch, root=Path("archive")):
    """Download approved evidence and write an immutable per-run manifest.

    Parameters
    ----------
    repository, run_id, branch : str
        Same-repository run identity and trusted default branch.
    root : pathlib.Path, default=Path('archive')
        Destination root; tests supply a temporary directory.

    Returns
    -------
    pathlib.Path
        Per-run directory, unchanged when the identical evidence already exists.
    """
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
        raise ValueError("Invalid repository")
    if not re.fullmatch(r"[1-9][0-9]*", run_id):
        raise ValueError("Invalid source run ID")
    run = _api(repository, f"actions/runs/{run_id}")
    if run["head_branch"] != branch:
        raise ValueError(
            "Source run is not on the default branch; "
            "branch experiments are not archived"
        )
    if (
        str(run["id"]) != run_id
        or run["head_repository"]["full_name"] != repository
        or run["path"] not in SOURCE_WORKFLOWS
        or run["event"] != "workflow_dispatch"
        or run["status"] != "completed"
        or not re.fullmatch(r"[0-9a-f]{40}", run["head_sha"])
    ):
        raise ValueError("Source must be a completed trusted default-branch run")
    settings = tomllib.loads(Path("config.toml").read_text())["permanent_archive"]
    destination, timing = _destination(Path(root), run, settings["timezone"])
    files, artifacts = {}, []
    page = 1
    while True:
        batch = _api(
            repository, f"actions/runs/{run_id}/artifacts?per_page=100&page={page}"
        )["artifacts"]
        for artifact in batch:
            name = artifact["name"]
            if name not in ARTIFACT_FILES:
                continue
            if artifact["expired"] or name in {a["name"] for a in artifacts}:
                raise ValueError("Approved artifact expired or duplicated")
            artifact_id = artifact["id"]
            if type(artifact_id) is not int or artifact_id <= 0:
                raise ValueError("Invalid artifact ID")
            payload = _api(
                repository, f"actions/artifacts/{artifact_id}/zip", binary=True
            )
            for filename, data in _members(name, payload).items():
                files[f"{name}/{filename}"] = data
            artifacts.append({"name": name, "id": artifact_id})
        if len(batch) < 100:
            break
        page += 1
    if not files:
        raise ValueError("No approved artifacts remain for this run")
    manifest = {
        "schema_version": 1,
        "repository": repository,
        "source_run_id": run_id,
        "source_commit": run["head_sha"],
        "workflow": run["path"],
        "branch": branch,
        "conclusion": run["conclusion"],
        "run_attempt": run["run_attempt"],
        "artifacts": sorted(artifacts, key=lambda item: item["name"]),
        "sha256": {p: hashlib.sha256(b).hexdigest() for p, b in sorted(files.items())},
    }
    previous = destination / "manifest.json"
    if previous.exists():
        existing = json.loads(previous.read_text())
        # Preserve old manifest bytes and newly recorded time fields alike.
        timing = {
            key: existing[key]
            for key in ("source_created_at", "source_local_time", "archive_timezone")
            if key in existing
        }
    manifest.update(timing)
    files["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    # Validate every target before writing anything. A retry may complete partial
    # identical data, but can never replace conflicting evidence or follow links.
    for relative, data in files.items():
        target = destination / relative
        if any(p.is_symlink() for p in (target, *target.parents)):
            raise ValueError("Archive destination contains a symlink")
        if target.exists() and (not target.is_file() or target.read_bytes() != data):
            raise ValueError("Archive evidence conflicts with existing data")
    for relative, data in files.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with target.open("xb") as stream:
                stream.write(data)
    return destination


def main():
    """Run the archive command without exposing downloaded text or API errors."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--branch", required=True)
    args = parser.parse_args()
    try:
        destination = preserve_run(args.repository, args.run_id, args.branch)
        if "GITHUB_OUTPUT" in os.environ:
            with Path(os.environ["GITHUB_OUTPUT"]).open("a") as stream:
                print(f"directory={destination.as_posix()}", file=stream)
        print(f"event=archive state=downloaded->preserved path={destination}")
    except Exception as error:
        print(f"event=archive state=pending->failed type={type(error).__name__}")
        if type(error) is ValueError and str(error) in _SAFE_VALIDATION_REASONS:
            print(f"Archive validation failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
