# Design choices

## 2026-10-24 — Editable recipient configuration

Sender and recipient addresses live in the email section of config.toml. The user
prefers a versioned file that any repository writer can edit over Actions settings.
The same list is used locally and in GitHub Actions, with no environment override
or fallback to old recipient variables. Passwords and Adzuna credentials remain
outside the file. Recipient addresses become public in this public repository.
Only the known address is included initially; the friend must be added explicitly.

## 2026-10-24 — Credential naming and the failed local run

The original application used the initially supplied spellings
`adzuna_APR_key` and `adzuna_app_ID`. The actual local setup supplies
`ADZUNA_API_KEY` and `ADZUNA_APP_ID`. The application failed before making any
Adzuna request, and its deliberately redacted error concealed which stage failed.
Both the application and GitHub workflow now use the actual uppercase names.
Tests exercise the command with synthetic uppercase credentials so the same
mismatch is caught without reading or displaying real credentials.

Adzuna request exceptions can include a URL containing authentication parameters.
The command therefore reports exception types without dumping exception messages
or tracebacks. This protects credentials at the cost of less detailed diagnosis.
Never enable HTTP debugging or log full request URLs to investigate failures.

## 2026-10-24 — Search and relevance

The proof of concept uses explicit title keywords and listing dates. No LLM or
Jev is called: the current ranking rule is a deterministic word match, rather
than a repeated semantic judgment. If candidate-specific suitability assessment
is added, that is a separate design decision requiring labelled examples.

A live search returned an investment-banking recruiter role among finance jobs.
Configurable title exclusions now remove recruiter and recruitment-consultant
titles. These checks prove only that the configured words match. They do not
prove that every retained vacancy is suitable, or that every excluded vacancy
is irrelevant. For example, a software role at a financial employer can still
appear. Recipients review the full advert; candidate-specific screening remains
outside the current scope.

## 2026-10-24 — History and delivery

Only emailed shortlist entries are added to history. Keys use Adzuna IDs and,
when employer/title/location are available, a normalized combination of those
fields. This catches some reposts but can hide distinct vacancies with identical
details. The current user preference is to suppress previously emailed jobs.

History stays local until migrated, then the GitHub workflow commits it to the
default branch. Public repository history is public. No credentials or recipient
addresses belong in the history file. Scheduled runs are serialized within that
workflow; independent local runs are not coordinated with GitHub or each other.

Gmail accepting a message is not proof of inbox delivery. There is no transaction
covering both Gmail and history storage, so failure after acceptance can cause a
repeat on retry. Partial recipient acceptance can do the same. The current
history file write is not crash-safe; interruption while writing can damage the
file, and invalid history causes the next run to fail rather than silently reset.
Do not run simultaneous local send commands. These are accepted proof-of-concept
limitations, not guarantees of exactly-once email delivery.

Automated tests establish preview/send/history behaviour with simulated services.
They cannot establish live Gmail delivery, Adzuna coverage, GitHub write permissions
or a particular recipient's job suitability. Each deployment still needs a live
preview, a deliberate send and confirmation that history persists successfully.
