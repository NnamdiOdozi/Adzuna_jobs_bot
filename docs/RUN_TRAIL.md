# Follow a bulletin from fetched jobs to email

Every new daily run writes a readable report on its GitHub Actions page. Open
**Actions → Daily London job shortlist → the run → Summary**. Beneath the workflow
details, **Daily job bulletin** shows counts, ranking method, observed email
status, selected jobs and all fetched jobs. Existing completed runs cannot have
new summary text inserted retrospectively.

## Two numbers, with different purposes

**Fetched #** follows arrival order across the provider batches in that run.
**Email #** follows the selected shortlist's order, matching the email's existing
numbering. For example, email position 1 can refer to fetched vacancy 37. Both
numbers appear together; the provider's job ID remains the durable identifier.
Numbers start again in each run and do not replace duplicate history.

The downloaded **job-run-report** artifact contains:

| File | Purpose |
| --- | --- |
| `summary.md` | The readable run report |
| `candidates.json` | Original normalized vacancies with fetched numbers |
| `assessments.json` | Model decisions and probabilities linked to fetched numbers |
| `shortlist.json` | Selected records with both fetched and email numbers |
| `report.json` | Counts, method, model, assessment records and delivery stage |
| `email.txt` | Exact prepared email body, without sender/recipient headers |

The original **job-candidates** and **job-ranking-receipts** artifacts remain
available for replay. Their schemas are unchanged. Normalized vacancy snapshots
preserve the fields the bot uses, rather than the untouched provider response.
Comparison reports also show fetched counts and link each selected position to
its original fetched number.

## What delivery status establishes

The report is first saved before email submission. It is updated after Gmail
accepts the message and again after normal delivery history is saved. A failed
submission is labelled **failed or unknown**, because a network error does not
prove that nobody received a message. Gmail acceptance is not inbox confirmation.
Preview sends nothing; sender-only tests preserve normal delivery history.
Reporting failures are logged without retrying email. The Actions report step
tries to explain incomplete runs from available snapshots and assessment records.

## Permanent copies in this repository

**Preserve run evidence** runs separately after a completed default-branch daily
or comparison run. It commits approved files under `archive/<London-date-time>/`,
with a manifest containing source identity and file fingerprints. It never
executes downloaded files or changes agent permissions. Archive data is public.
There is no automatic deletion; artifacts still expire after 90 days.

Names such as `2026-11-18_06-30-45_GMT` use the source run's creation time,
converted to the configured `permanent_archive.timezone` (`Europe/London`). The
manifest retains the original UTC time and GitHub run ID. Existing numeric
folders remain readable; a second run in the same second gets an ID suffix.

Open **Code → archive → the dated folder** to browse permanent files. For new
daily runs, open **job-run-report → summary.md** to read the bulletin directly.
To preserve an older run before its artifacts expire, open **Actions → Preserve
run evidence → Run workflow**, enter its numeric **source_run_id**, and run it.
That downloads existing evidence only: no job search, model call or email.
It cannot recover an expired artifact or an email body never captured.

To compare an archived batch later, use its source ID in **Compare finance job
rankings**, leaving **fresh_search** off. Explicit IDs use committed snapshots
before attempting artifact downloads. Ranking comparisons still consume model
credits when their model jobs are enabled.
Open `manifest.json` and copy its `source_run_id` for that input; the date-time
folder name is for browsing, while the ID identifies the original GitHub run.

Archive publication has bounded retries and its own visible failure status, so
it cannot block the email that already ran. It accepts only default-branch
sources. Up to 100 archive runs can queue; additional runs need manual recovery.
The archive is not currently monitored by the Cloudflare delivery watchdog.
Hashes establish unchanged file contents, not model correctness or job truth.
Filename restrictions do not guarantee absence of contact information in public
advert text; raw runner logs and email headers are deliberately excluded.
