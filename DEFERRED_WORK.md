# Open work

- 2026-11-16 — Source: user chose Jev for semantic job suitability. Live local
  trial of the forty saved JSearch candidates completed in two twenty-question
  requests, without retries: 32,257 input tokens, 2,126 output tokens, about
  $0.00135 estimated API cost. Against provisional Codex labels, its shortlist
  contained eighteen plausible, zero clearly unsuitable and two uncertain roles.
  Evidence and limits: `reports/jev_evaluation_2026-11-16.md`. A second authorized
  trial used the corrected Finance and Accounting profile with explicit legal,
  mid-level and senior exclusions: thirteen strong, four possible, twenty
  unlikely and three insufficient-information results. Seventeen shortlisted;
  investment-banking advert dropped. Local canonical candidate profile corrected.
  See `reports/jev_accounting_evaluation_2026-11-16.md`. The user's latest
  clarification permits complaints operations and graduate investment programmes
  offering training. A fresh Jev/Qwen face-off and 252-record historical title
  pass are complete: `reports/finance_model_faceoff_2026-11-16.md`.
  Standard-workflow Jev adapter, editable policy, configuration method switch,
  repository Secret mapping, assessment artifacts and offline tests are implemented.
  The user selected method=jev for normal delivery. The Qwen config option and
  <=25-job Adzuna top-up are implemented with offline tests. Pending: user ensures
  TYPESAFE_API_KEY is configured as a repository Secret, and verifies the first
  normal Jev delivery or a sender-only end-to-end run.
  Local evaluation artifacts are not available in a fresh GitHub checkout.
  Graduation-date and finance-sales preferences remain open. The legacy agentic
  comparison is separate; Jev does not depend on it.

- 2026-11-16 — Source: approved manual Nebius ranking experiments. Snapshot,
  direct ranker, comparison/test-email CLI and compiled Agentic Workflow are
  implemented with offline tests. Live run 43874086629 on 2026-11-16 verified
  direct Nemotron structured output: four synthetic unseen jobs assessed in one
  call, with the expected decisions. Sender-only test email submission succeeded.
  GitHub agent execution aborted during provider discovery with no supported
  SDK wire API; investigate runtime compatibility before another paid trial.
  Evaluation: `reports/ranking_experiment_43874086629_2026-11-16.md`.
  A 40-candidate JSearch evaluation now has provisional Codex labels and a rules
  baseline: `reports/jsearch_ranking_evaluation_2026-11-16.md`. Direct local
  ranking initially failed with only a generic RuntimeError recorded. Safe
  diagnostics and preservation of validated batches are now implemented locally
  and covered by 139 passing offline tests. One authorized ten-job diagnostic
  trial returned HTTP 200, finish_reason=length, 8192 completion tokens and zero
  final-answer characters after about 34 seconds. The local direct failure is
  now confirmed as output-budget exhaustion, not connection failure. No retry.
  The user has since chosen Jev, so no further paid Nemotron budget trial is
  planned. Diagnostic changes are now published with the Jev integration. Retain
  the agent-runtime experiment as an optional route with its limitation disclosed.
  Normal delivery now has a separate compact fixed-slot Qwen adapter. The legacy
  Nebius quotation-based experiment remains separate and retains its older format.
  Human-reviewed labels, daily artifact capture on a scheduled run and sender
  inbox confirmation for the original experiment also remain unverified.
  Daily ranking is now separately selected as Jev. Qwen SDK, CLI and native
  Copilot connection experiments are tracked in
  `reports/agent_connection_experiments_2026-11-16.md`; the CLI variant remains
  isolated on `experiment/qwen-cli`, not selected for normal delivery.
  Qwen SDK reproduced the metadata failure. CLI trials stopped before inference
  on missing-model and unresolved-auto configuration errors; its model selection
  still needs investigation. The separate 33-line native Copilot probe passed
  exit/nonempty-response checks, without establishing full ranking suitability.

- 2026-11-13 — Source: approved JSearch build. Provider switch, eight-page/50 km
  settings, Secret mapping and offline tests are complete. User reports adding
  GitHub JSEARCH_API_KEY. Authorized live eight-page acquisition on 2026-11-16
  returned 42 jobs with descriptions; 40 remain after history/duplicate checks.
  Local reusable dataset and limitations are documented in
  `reports/jsearch_evaluation_batch_2026-11-16.md`. Provisional agent labels and
  rules evaluation are now saved; a larger Nebius attempt failed. Pending: human
  label review, successful model evaluation and GitHub replay access for that dataset.
  Adzuna remains primary with
  automatic JSearch backup after HTTP errors or no unseen matching jobs. If
  both have no matches, send the user-requested informative notice. A JSearch
  failure sends a distinct failure email; accepted notices use the daily limit
  while Actions still reports search failure. Eight-page retrieval is now live
  verified; strict radius behaviour and account billing/quota remain unverified.
  Shared history preserves
  cross-source duplicate checks; exact county boundaries/identity remain limits.

- 2026-11-13 — Source: missed morning email and requested Cloudflare instructions.
  Replacement Worker with bounded dispatch retries and offline tests is ready.
  User reports adding both Text variables and pasting the new script into
  Cloudflare. Confirm the Production deployment and next scheduled dispatch
  using `cloudflare/README.md`; live retry recovery has not been verified.
  User subsequently chose a same-Worker watchdog and Ntfy only. That code and
  offline tests are now prepared locally: recovery checks at 06:45, alerts at
  07:00 London time. User reports updating the script, settings, Secret and cron,
  and successfully publishing a direct curl test to the new topic: the phone
  received it. Status: topic/subscription verified by user; confirm Production
  deployment and scheduled delivery checks. The direct test does not establish
  that Cloudflare's saved topic or watchdog works. No agent notification was sent.

- 2026-11-12 — Source: requested historical filter backtest. Offline title replay
  of 273 history records is in `reports/filter_backtest_2026-11-12.md` and its CSV.
  Status: analysis complete, live rules unchanged. User agreed AVP/lawyer
  exclusions; implement these and agree the wider legal/occupation phrases,
  narrow finance-title exceptions and changed-location duplicate policy from
  the report. Preserve ordinary analyst/accountant matches. Future evaluation
  needs saved pre-filter candidates and suitability labels; old sent history
  alone cannot establish recall. No new Adzuna or model calls were made.

- 2026-11-10 — Source: authorized one-request relevance check. Tighten graduate
  suitability separately from finance relevance: Finance Business Partner survived
  the title exclusions; controller roles have since been excluded at the user's
  request. Status: observed and
  disclosed; no experience parsing or blanket rejection of generic accountant/
  analyst roles implemented. Agree additional senior role phrases or stronger
  junior evidence before changing that policy. The finance gate also excludes
  valid roles whose titles lack the configured words (e.g. Purchase Ledger Clerk).

- 2026-10-26 — Source: approved minimal Cloudflare timer. Deploy the prepared
  `cloudflare/worker.mjs` in the dashboard, add its variables, token Secret and
  Cron Trigger, then verify a dispatch and email receipt. Status: code and
  offline checks complete; user reports Worker, Cron Trigger and token deployed.
  Verify a dispatch and receipt, then update the dashboard Worker to the new
  RUN_MODE-capable script if testing preview/sender-only modes. Native GitHub cron
  removed; the dashboard deployment controls the automatic timer.

- 2026-10-24 — Source: approved history cleanup. Decide whether any old public
  run logs or GitHub cached commit views need further removal or a Support request.
  Status: main-branch history scrubbed and checked; cached copies, forks and other
  clones remain outside that verification. No log deletion or Support contact
  authorized; any other old checkout must be cleaned before pushing again.
- 2026-10-24 — Source: user request. Explore applying for jobs on the friend's
  behalf rather than only emailing vacancies. Status: deferred; no implementation
  or application submission authorized today. Agree which sites and job criteria
  to support, and whether each application needs her approval before submission
  or can be submitted automatically within explicitly agreed limits. Determine
  the minimum applicant information required: CV, contact email, phone number,
  work history and any site-specific questions. Obtain her consent and choose
  private storage and access controls; never commit her CV, phone number, account
  credentials or other private applicant information to this public repository.
  Do not invent missing qualifications or answers. Plan application history to
  prevent duplicate submissions and distinguish a submitted application from
  confirmed receipt. No personal documents need to be collected today.
- 2026-10-24 — Source: deployment discussion. Decide whether to change the
  currently public repository to private. Status: public visibility retained;
  user authorized publishing the source on this date.
- 2026-10-24 — Source: local test. Verify Gmail submission and receipt with a
  deliberate send; preserve resulting local history during migration.
  Status: corrected normal preview verified live; Gmail not tested by the agent.
  Existing local sent-job history was found and preserved.
- 2026-10-24 — Source: GitHub Actions plan. User adds credentials as secrets, then
  verify manual preview, manual send, history commit and the daily schedule.
  Status: workflow configured for publication; secrets and live checks remain.
- 2026-10-24 — Source: terminal output. User-managed startup configuration tries
  to activate a missing virtual environment. Status: unchanged; no virtual
  environment is required by the current application. Secret startup files are
  outside the agent's editing scope.

## Shortlist improvements — deferred 2026-10-24

Source: candidate-preference, ranking and run-log discussions. Status: open
extensions beyond the title rules implemented on 2026-11-04; no paid model calls
or application submissions authorized.

## 1. Candidate preferences — deferred 2026-10-24

Extend the editable title criteria with candidate preferences. Agree additional
values with the friend. Separate hard requirements, which reject a job, from
preferences, which change its rank.

- More specific role specialisms and unwanted responsibilities; summer/placement
  eligibility and whether those programmes should be included.
- Candidate experience and acceptable job requirements. Distinguish essential
  experience from desirable experience, ranges, and equivalent experience.
- Minimum salary and treatment of missing salary, estimated salary, and ranges
  that overlap the threshold. Compare compatible currencies and pay periods.
- Remote, hybrid or office attendance requirements and acceptable commute.
- Permanent, temporary or contract roles; full-time or part-time work.
- Required qualifications, relevant skills and transferable experience.
- Work authorization and sponsorship needs, where the advert supplies evidence.

Do not invent defaults for these choices. Changing the target candidate should
not require editing source code. Personal candidate information must stay out
of this public repository.

## 2. Evidence and filtering — deferred 2026-10-24

Use structured Adzuna fields and Python comparisons first, including salary and
contract information. Simple, explicit phrases may be parsed without a model.
Adzuna search results contain description snippets, so missing experience,
sponsorship or working-arrangement details mean unknown, not no requirement.

If full adverts are needed, first establish a permitted, practical retrieval
method and handle inaccessible pages explicitly. Preserve the evidence used for
each extracted requirement. Never infer a qualification or experience threshold
merely from a senior-sounding title.

For genuinely ambiguous text, compare a generative extraction model with a
bounded classifier. The extractor can discover requirements; Jev can judge a
specified requirement against supplied evidence using outcomes such as meets,
does_not_meet and insufficient_information. Exact arithmetic remains in Python.
Free-text instructions need an implemented interpretation step: adding a prompt
field alone does not change behaviour.

Initially retain uncertain matches for review. Define missing-evidence handling
explicitly so truncated adverts do not silently exclude suitable jobs. No model
or Jev calls have been authorized or performed for these proposals.

## 3. Ranking and cost controls — deferred 2026-10-24

Extend the current junior-title preference and finance-word score with agreed
candidate-fit weights and findings. Explain why each job
ranked highly and identify unmet or unknown requirements separately. Apply the
new criteria before choosing the final shortlist; scoring only the first 20
would miss potentially better candidates elsewhere in the fetched results.

Remove known and duplicate adverts and apply cheap exact filters before paid
analysis. Consider caching analysis for unchanged adverts. Estimate request
volume and spending, agree a limit before any paid trial, and decide whether
batch processing fits the morning delivery deadline. Preserve the single-search
request budget, including its explicitly bounded page-size fallback.

## 4. Review and validation — deferred 2026-10-24

Create a small hand-checked set of adverts before trusting automatic rejection.
Include missing salaries, estimated salaries, experience that is preferred rather
than required, alternative qualifications and incomplete descriptions. Compare
the new approach with the existing title rules. Measure suitable jobs wrongly
excluded, unsuitable jobs retained, unknown outcomes and cost per advert.

Valid structured output proves format, not correct interpretation. Display the
supporting wording so a person can check important judgments. If model confidence
labels are used, define their meanings and check their usefulness against the
reviewed examples rather than treating them as calibrated probabilities.

## 5. Inspectable shortlists and send records — deferred 2026-10-24

Log selected job IDs, titles and employers in send mode as well as summary counts.
Distinguish selection, Gmail acceptance and successful history persistence.
Consider a saved shortlist or downloadable GitHub artifact so the exact selection
can be inspected later without rerunning the search. Decide retention and access
before adding artifacts. Do not log credentials or private applicant information.

Consider a separate email-submission record with run time and selected job IDs.
The current seen.json is duplicate-suppression history, not an email audit trail
or proof of inbox delivery. Saving a shortlist must not mark its jobs as sent.
