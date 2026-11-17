# Saved job-run evidence

The **Preserve run evidence** workflow stores approved JSON and readable reports
here after default-branch daily and comparison runs. Each numbered directory is
the original GitHub run ID, not the archive job's ID. Its `manifest.json` records
the source commit, original artifact identities and file fingerprints.

For new daily bulletins, open `<run-id>/job-run-report/summary.md`. The same folder
contains numbered candidates, assessments, the shortlist and the prepared email
body. Older runs may contain only their originally captured data.

These committed files have no automatic expiry. Everything in this folder is
public. Do not add credentials, email headers or raw runner logs. See
[the run-trail guide](../docs/RUN_TRAIL.md) for navigation and backfilling old runs.
