"""Controlled title-only replay; never calls providers or writes history."""

import csv
import json
import subprocess
import tomllib
from pathlib import Path

from jobs_bot.shortlist import select_jobs

baseline = {}
exec(
    subprocess.check_output(
        ["git", "show", "3af73ec:jobs_bot/shortlist.py"], text=True
    ),
    baseline,
)
config = tomllib.loads(Path("config.toml").read_text())["search"]
rows = list(csv.DictReader(Path("reports/filter_backtest_2026-11-12.csv").open()))
jobs = [
    dict(
        id=str(i),
        title=row["title"],
        company={"display_name": row["company"]},
        location={"display_name": row["location"]},
        category={"tag": config["category"]},
        created="",
    )
    for i, row in enumerate(rows)
]
config["shortlist_size"] = len(jobs)
old = baseline["select_jobs"](jobs, set(), config)
new = select_jobs(jobs, set(), config)
old_ranks = {job["id"]: rank for rank, job in enumerate(old, 1)}
new_ranks = {job["id"]: rank for rank, job in enumerate(new, 1)}
with Path("reports/junior_ranking_title_replay.csv").open("w") as stream:
    writer = csv.DictWriter(
        stream,
        lineterminator="\n",
        fieldnames=["title", "company", "location", "baseline_rank", "proposed_rank"],
    )
    writer.writeheader()
    for job in new:
        writer.writerow(
            dict(
                title=job["title"],
                company=job["company"]["display_name"],
                location=job["location"]["display_name"],
                baseline_rank=old_ranks[job["id"]],
                proposed_rank=new_ranks[job["id"]],
            )
        )
print(
    json.dumps(
        dict(
            records=len(jobs),
            baseline_selected=len(old),
            proposed_selected=len(new),
            eligibility_changes=len(set(old_ranks) ^ set(new_ranks)),
            moved=sum(old_ranks[key] != new_ranks[key] for key in new_ranks),
            top20_overlap=len(
                {j["id"] for j in old[:20]} & {j["id"] for j in new[:20]}
            ),
        )
    )
)
