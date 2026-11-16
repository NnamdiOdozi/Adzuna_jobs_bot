"""Select downloaded candidate archives and expose safe workflow settings."""

import argparse
import os
import re
import tomllib
from pathlib import Path

from jobs_bot.snapshots import load_snapshot


def choose_snapshot(directory, filename=""):
    """Select an explicit archive basename or the latest validated provider batch."""
    root = Path(directory)
    if filename:
        if Path(filename).name != filename or not filename.endswith(".json"):
            raise ValueError("Choose one JSON snapshot filename, not a path")
        paths = [root / filename]
    else:
        paths = list(root.glob("*.json"))
    if not paths or any(path.is_symlink() for path in paths):
        raise ValueError("No safe candidate snapshot found")
    snapshots = [(load_snapshot(path), path) for path in paths]
    return max(snapshots, key=lambda item: item[0]["captured_at"])[1]


def settings(config):
    """Return the small set of non-secret settings required by Actions."""
    archive, experiment = config["archive"], config["experiment"]
    values = {
        "archive_directory": archive["directory"],
        "archive_name": archive["artifact_name"],
        "archive_retention": archive["retention_days"],
        "result_name": experiment["result_artifact_name"],
        "result_retention": experiment["retention_days"],
        "model": config["agentic"].get("model", config["ranking"]["model"]),
        "base_url": config["ranking"]["base_url"],
        "prompt_tokens": config["agentic"]["max_prompt_tokens"],
        "output_tokens": config["ranking"]["max_output_tokens"],
    }
    for name, value in values.items():
        if name.endswith(("retention", "tokens")):
            if type(value) is not int or value <= 0:
                raise ValueError("Invalid workflow numeric setting")
        elif not isinstance(value, str) or not value or re.search(r"[\r\n]", value):
            raise ValueError("Invalid workflow text setting")
    if values["archive_retention"] > 90 or values["result_retention"] > 90:
        raise ValueError("Public repository artifact retention cannot exceed 90 days")
    if values["base_url"].rstrip("/") != "https://api.tokenfactory.nebius.com/v1":
        raise ValueError("Agent inference must use the intended Nebius HTTPS endpoint")
    return values


def main():
    """Print a snapshot path or write settings to GitHub's step-output file."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    choose = commands.add_parser("choose")
    choose.add_argument("--directory", required=True)
    choose.add_argument("--filename", default="")
    output = commands.add_parser("settings")
    output.add_argument("--config", default="config.toml")
    args = parser.parse_args()
    if args.command == "choose":
        print(choose_snapshot(args.directory, args.filename))
    else:
        with Path(args.config).open("rb") as stream:
            values = settings(tomllib.load(stream))
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as stream:
            for name, value in values.items():
                print(f"{name}={value}", file=stream)


if __name__ == "__main__":
    main()
