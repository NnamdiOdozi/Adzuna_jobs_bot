# Design choices

## 2026-11-10 — Require finance relevance before ranking

The supplied bulletin contained 18 titles with zero configured finance-word
matches, including Entry-Level Executive Search Consultant, baristas and chefs.
The combined keyword search could return incidental description matches, while
the local code only ranked finance evidence and never required it. Junior
wording could therefore promote a zero-finance role. The earlier seniority tests
did not cover this failure, so their passing results did not establish relevance.

The request now includes Adzuna's documented `accounting-finance-jobs` category.
Local selection independently requires that returned category tag and a whole
finance word/phrase in the title before senior exclusions, junior preferences,
deduplication or the shortlist limit. Accounts, payroll, bookkeeping, auditor
and actuarial title terms extend the explicit finance vocabulary. Missing,
malformed or different categories are excluded. A bare Junior Analyst is now
excluded; Junior Finance Analyst remains eligible. Rejection counts are logged.

Tests include all 18 unrelated titles even with synthetic finance categories,
incorrect/missing categories, valid finance roles, request parameters in both
attempts and the command's actual email/history selection. These establish exact
criteria, not semantic truth or graduate eligibility: provider misclassification
and an unrelated role mentioning a finance word can still pass, while valid roles
without those words or in another category can be missed. The accepted trade-off
favours a shorter, explicitly relevant shortlist. The request budget and 400→100
fallback are unchanged. No history records are reset.

With explicit user permission, one live request was made after the offline
checks. A wrapper prevented any second HTTP request during this verification;
the production fallback itself was unchanged. The category-filtered request
specified 400 and returned 50, all tagged accounting-finance-jobs. The local
rules excluded 26 for missing finance-title evidence and 10 for senior titles;
history filtering left 13 unseen selections. No mail was sent or history changed.
Accounts Assistant and Finance Assistant were present, but Financial Controller
and Finance Business Partner also survived. This confirms improved finance
relevance, not graduate suitability; that remaining gap is in DEFERRED_WORK.md.
The user then explicitly requested excluding controller titles. A whole-word
controller exclusion now also rejects Assistant Financial Controller and Credit
Controller, even though some credit-control roles can be junior. Rechecking the
cached selection removes Financial Controller without another API request.

The user's live log for 2026-11-10 shows one request specifying 400 succeeded
with 50 returned jobs. No fallback occurred. This establishes that response's
size and acceptance, not a universal maximum of 50. Earlier success requesting
100 likewise did not establish the number actually returned.

## 2026-11-09 — One combined search with a bounded size fallback

The user clarified that the intended budget was one Adzuna request per search,
not one per role query, then requested 400 results with a fallback to 100.
The four-query loop and pagination setting are removed. `query_terms` supplies
finance alternatives through the documented `what_or` parameter on page 1.
Junior/senior title rules and all delivery/history safeguards still apply.

One request is made normally. A first HTTP 400 causes exactly one smaller-page
retry; the second failure propagates. Other HTTP errors and network failures
are not retried. Equal configured primary/fallback sizes are deduplicated, and
a fallback larger than the primary is rejected. Successful short or empty
responses are used as returned, never expanded through more requests. Logs
show attempt, requested/returned count and HTTP status without URLs, response
bodies or credentials. Existing full-response validation remains in force.

Adzuna's public OpenAPI schema documents `what_or` and a positive page size but
no maximum. No live Adzuna request was authorized for verification. Offline
tests prove one/two request bounds and error behaviour, not support for 400 or
100 results, provider credit accounting or actual vacancy coverage. HTTP 400
means invalid parameters generally, so the single size retry is a heuristic;
an unrelated invalid parameter could also consume the second request. If 100
is rejected too, the workflow reports failure. One broad result pool may miss
roles that separate targeted searches would retrieve.

## 2026-11-09 — Weekday-only normal delivery

The user requested Monday–Friday email without editing Cloudflare. The bot now
checks editable `[email].send_weekdays` (Monday=0, Sunday=6) against the London
date before history, credentials or network access. Cloudflare's existing
Saturday dispatch remains valid but logs `reason=non_send_day` and exits zero.
Normal manual sends follow the same rule; force_send overrides only the daily
limit, not permitted weekdays. Preview and sender-only test remain available.
Offline tests cover both weekend days, a forced weekend send, Friday/Monday
normal sends and weekend testing. The clock check cannot fix missing dispatches.

Adzuna HTTP failures already propagate to the command's redacted exception log
and nonzero exit, making the Actions run fail. Current logs show HTTPError but
do not identify quota exhaustion or log the HTTP response body/URL, which may
contain credentials. No proactive alert email is implemented by the bot.

## 2026-11-04 — Graduate-focused searches and title rules

The user supplied a 20-job email with seven clearly senior titles and requested
ordinary code filters for a recent graduate. The previous finance-keyword count
rewarded broad banking/investment wording without checking seniority. Four more
targeted queries now retain the same one-page/100-results request limits.

Configured senior/recruiter phrases are excluded before ranking and choosing
the shortlist. Punctuation-normalized, whole-token matching catches Sr. and VP
without matching words such as overhead. Junior/graduate/trainee/assistant/entry
level titles sort first; within each group, associate titles sort lower. The
existing finance-word count and recency break ties. Senior exclusion overrides
junior wording, so Assistant Manager never receives the assistant preference.
Generic analysts and ambiguous associates remain eligible, and fewer than 20
results are sent when fewer survive. No salary or description filters are added.

Offline tests cover the supplied seven senior titles, ordering, punctuation,
word boundaries, duplicates and shorter results. These prove configured text
matching, not candidate eligibility. Titles may still conceal required experience,
and relevant jobs can be missed by narrower queries or broad senior exclusions
(for example, a junior role whose title mentions a manager). Summer/placement
programme eligibility remains a manual check. No LLM, Jev, Adzuna call or email
is needed to validate these rules. Existing delivery and vacancy history are
preserved from GitHub's latest daily-run commit before publishing.

## 2026-10-26 — Sender-only test delivery

The user requested testing Cloudflare through GitHub without contacting the
friend. Workflow mode `test` runs `--test-send`, a mutually exclusive alternative
to normal `--send`. It uses only `GMAIL_SENDER` as recipient, never the normal
recipient settings, labels the subject `[TEST]`, and returns before either history
write. It bypasses the daily date guard so today's normal send does not prevent
testing, while still filtering previously emailed vacancies.

The Worker accepts a validated `RUN_MODE` of preview, test or send. Omission
preserves the deployed Worker's original send behaviour. The dashboard-managed
Worker must be updated manually before that variable can change its behaviour.
Offline tests check mode forwarding, rejection of invalid modes, sender-only
message headers and preservation of existing/absent history. No live email or
Cloudflare dispatch was performed; tests do not establish inbox delivery.

## 2026-10-26 — Cloudflare timer and deliberate repeat sends

The user requested a minimal version of the fixed-income project's GitHub
dispatch pattern. The new Worker uses workflow dispatch, targeting only the
existing jobs workflow with mode=send. No database, health probes, proxying,
notification service or automatic retry is needed for this version. Dashboard
variables supply the repository, workflow, branch, timezone and send time; a
Worker Secret supplies the GitHub token. No public HTTP trigger is implemented.

Cloudflare Cron Triggers use UTC, so `30 5,6 * * *` checks both possible UTC
hours. The Worker uses the scheduled timestamp to select 06:30 Europe/London
and exclude Sundays. Only one daily invocation dispatches; the other skips.
The GitHub native schedule is removed to avoid an early or competing email.
Deployment and dashboard configuration remain user-managed; until completed,
there is no automatic timer. GitHub acceptance is not execution or delivery.
Offline Node tests cover both seasons, clock-change weekends and request failure.
No live Cloudflare invocation or GitHub dispatch has been tested by the agent.

The config switch `[email].force_send`, false by default, bypasses the daily
limit only. A warning logs its use; the vacancy filter and history still apply.
The override also affects automated send runs if committed as true, so it must
be reset after deliberate extra-send testing. Offline Python tests exercise this.

## 2026-10-26 — One accepted email per London date

The send command checks `state/delivery.json` before loading credentials or
contacting Adzuna. An already-recorded London date produces a successful skip
with `reason=already_sent`. Preview is unaffected. The first delivery record is
seeded from the confirmed Gmail acceptance in manual run 40286374198 at
2026-10-26 07:32:22 UTC. Existing vacancy keys remain unchanged.

After Gmail accepts an email, the date record is saved using a temporary file
and replacement, then vacancy history is saved. GitHub commits both files even
if a later step fails, unless the run is cancelled. Existing workflow concurrency
serializes manual and scheduled runs; each checks out the current default branch.
The same-date check also covers empty shortlists. Failed Gmail submissions do
not consume the date, allowing retries.

Offline tests prove the date check, skipping before API calls, next-day delivery,
preview behaviour and failure handling. They do not prove inbox receipt or
exactly-once delivery: a crash after Gmail acceptance but before saving the date,
a failed GitHub push, partial recipient acceptance, or independent stale/local
checkouts can still permit another email. Simultaneous local sends are unsupported.
The new record does not fix GitHub's delayed or missing scheduled triggers.

## 2026-10-25 — Earlier scheduled start

The user moved the scheduled start from 06:30 to 02:30 Europe/London after
observing roughly four-to-five-hour delays in the separate fixed-income standby
workflow. Monday-to-Saturday operation is preserved. Europe/London means GMT in
winter and BST in summer; this is not a fixed UTC hour throughout the year.
The buffer is a temporary timing choice, not a delivery guarantee: a punctual
run can send around 02:30 and a sufficiently delayed run can still arrive late.

## 2026-10-24 — Email address privacy

The user initially preferred editable recipient configuration, then requested
removing addresses to reduce exposure to public-repository scraping. Sender and
recipients now come only from runtime settings. In GitHub Actions these settings
are repository Secrets: GMAIL_SENDER, EMAIL_USER and EMAIL_FRIEND. The user chose
Secrets after discussing that ordinary Variables are not automatically masked
in public logs. No fallback to public config or repository Variables is used.

Locally, the approved credential launcher supplies GMAIL_SENDER, email_user and
optional email_friend. GMAIL_SENDER must contain the actual Gmail login, separate
from a recipient alias with a plus tag. Recipient spelling is preserved. The
Gmail app-password label remains an informational comment, not a login setting.

The user authorized history rewriting on 2026-10-24. The 12 existing commits were
rewritten in an isolated repository to replace Gmail/Googlemail addresses with
non-personal placeholders. All historical file contents and commit metadata on
that branch were checked for remaining matches. The current tracked file tree,
including sent-job history, was preserved exactly by the rewrite. A separate
sender-name fix uses uppercase GMAIL_SENDER locally and in GitHub Actions.

Publication uses an update guarded against unexpected remote changes. Other old
clones must not merge their original history back. Old GitHub cached views, forks,
run logs and downloaded copies are outside the verified main-branch cleanup;
secret masking and history rewriting do not undo that past exposure. Repository
visibility is unchanged. GitHub Support may be needed for eligible cached data
removal; no support contact or deletion of run logs is authorized by this change.

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
