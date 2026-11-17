"""Require successful GitHub code checks before searching or sending email."""

import argparse
import json
import os
import re
import subprocess
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from jobs_bot.archive_runs import archive_data_path


def _documentation_path(path):
    # Prompts and agent definitions also use Markdown but affect live behaviour;
    # only these documentation locations are exempt from the code-test gate.
    return path in {
        "README.md",
        "DESIGN_CHOICES.md",
        "DEFERRED_WORK.md",
        "HANDOVER.md",
        "DOUBTS.md",
        "archive/README.md",
    } or (path.startswith(("docs/", "reports/")) and path.endswith(".md"))


def verify(repository, workflow, branch, token, timeout):
    """Accept passed code with subsequent delivery records and known evidence."""
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
        raise ValueError("Invalid repository")
    if not re.fullmatch(r"[\w.-]+\.ya?ml", workflow):
        raise ValueError("Invalid checks workflow")
    query = urlencode({"branch": branch, "event": "push", "per_page": 1})
    request = Request(
        f"https://api.github.com/repos/{repository}/actions/workflows/{workflow}/runs?{query}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        runs = json.load(response)["workflow_runs"]
    if not runs or runs[0]["conclusion"] != "success":
        raise RuntimeError("Latest pushed code checks are missing, pending or failed")
    run = runs[0]
    sha = run["head_sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Invalid tested commit")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, "HEAD"], check=False
    )
    if ancestor.returncode:
        raise RuntimeError("Tested commit is not an ancestor of checked-out code")
    # Evidence and delivery records grow independently of application code.
    # Check filenames explicitly so an executable under archive/ still blocks.
    difference = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            sha,
            "HEAD",
            "--",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if difference.returncode or any(
        path not in {"state/seen.json", "state/delivery.json"}
        and not archive_data_path(path)
        and not _documentation_path(path)
        for path in difference.stdout.split("\0")
        if path
    ):
        raise RuntimeError("Checked-out code differs from successfully tested code")
    print(
        f"event=code_check state=unverified->verified "
        f"tested_commit={sha} run_id={run['id']}"
    )


def main():
    """Read workflow inputs and fail visibly without printing authentication data."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--timeout", required=True, type=int)
    args = parser.parse_args()
    try:
        verify(
            os.environ["GITHUB_REPOSITORY"],
            args.workflow,
            args.branch,
            os.environ["GITHUB_TOKEN"],
            args.timeout,
        )
    except Exception as error:
        print(f"event=code_check state=unverified->blocked type={type(error).__name__}")
        print(
            "No search or email: code checks must pass for this version. "
            "See Code checks in Actions."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
