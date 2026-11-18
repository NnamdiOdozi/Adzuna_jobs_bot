# Saved job-run evidence

The **Preserve run evidence** workflow stores approved JSON and readable reports
here after default-branch daily and comparison runs. New directories use the
source run's creation time in London: `2026-11-18_06-30-45_GMT`, for example.
The year-first order sorts chronologically; `GMT`/`BST` identifies winter/summer
time. Its `manifest.json` retains the GitHub run ID, original UTC time, source
commit, artifact identities and file fingerprints. Older numeric folders remain
supported. A run ID suffix is added only if two timestamps collide.

For new daily bulletins, open `<date-time>/job-run-report/summary.md`. The same folder
contains numbered candidates, assessments, the shortlist and the prepared email
body. Older runs may contain only their originally captured data.

These committed files have no automatic expiry. Everything in this folder is
public. Do not add credentials, email headers or raw runner logs. See
[the run-trail guide](../docs/RUN_TRAIL.md) for navigation and backfilling old runs.

The 17 and 18 November assessments were later enriched with titles and vacancy
text from their saved candidates, without changing decisions or probabilities.
Their manifests record the additions and retain the original file fingerprints
alongside the current ones. Repeating an original download will fail rather than
overwrite these enriched historical versions and silently remove that context.
