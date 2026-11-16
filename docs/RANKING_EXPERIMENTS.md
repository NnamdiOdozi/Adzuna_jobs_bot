# Comparing job rankings on GitHub

The daily bot still uses its existing rules. It now saves each successfully
fetched provider batch before filtering, including available descriptions and
the seen-job keys and search settings used at that time. A separate manual
experiment compares those rules with Nemotron on Nebius Token Factory. You can
also include a genuine GitHub Agentic Workflow using the same provider/model.
Your laptop does not need to remain on.

The model is `nvidia/nemotron-3-super-120b-a12b`, matching the experiments lab's
active local development branch. Endpoint availability, structured output and
the Copilot engine's tool calling remain unverified until an explicitly chosen
live run. Successful offline tests or workflow compilation do not establish them.

## One-time GitHub setup

1. Open this repository on GitHub. Select **Settings → Secrets and variables →
   Actions → Secrets**. If your screen combines these tabs, choose repository
   secrets rather than an environment.
2. Choose **New repository secret**. Set **Name** to `NEBIUS_KEY`, paste your
   Token Factory inference key into **Secret**, then choose **Add secret**. Do
   not put the key in `config.toml`, an issue, workflow input or prompt.
3. The existing `GMAIL_SENDER` and `GMAIL_APP_PASSWORD` repository secrets are
   used only if you select test email. No friend/user recipient secret is passed
   to experiment delivery. The experiments do not require a paid Copilot model
   subscription: the engine is configured to route inference to Nebius. Actual
   engine/model compatibility still needs the first live test.

The job API secrets are used only for an explicitly selected fresh search. The
agent receives neither those credentials nor Gmail credentials. No Cloudflare
console changes are needed.

## First test without spending job-search credits

1. Select **Actions** at the top of the repository.
2. Select **Compare finance job rankings** in the left sidebar.
3. Choose **Run workflow** and use the default branch.
4. Leave **source_run_id** and **snapshot_filename** blank. Leave **fresh_search**
   unchecked. Check **example_data**. These choices use the clearly labelled
   synthetic `examples/candidates.json`, not Adzuna or JSearch.
5. Leave **include_agent** unchecked for the first direct-model compatibility
   check. Select **preview** to generate reports without email, or **test** to
   receive one comparison email only at the configured sender address.
6. Choose the final **Run workflow** button. Open the new run. The preparation
   stage makes no paid calls for example/replay input. Its direct-ranking stage
   calls Nebius: the example contains four unseen candidates, fitting one
   configured inference batch. There are no automatic charged inference retries.

This is a live model test, not a free unit test. It consumes Nebius credits even
in preview mode. No live model calls were made during implementation. A failed
model request is shown as failed, never replaced by a falsely successful rules
result. If available, the comparison still preserves baseline and failure details.

For the second experiment, repeat with **include_agent** checked. This runs the
direct route and an agentic route on the same input. The agent can use multiple
Nebius calls while reading and writing results; its execution is bounded by the
workflow time/tool limits. GitHub runner/storage charges are separate from model
credits. It uses the existing compiled workflow; you do not install a CLI locally.

## Reuse actual daily candidates

After the revised daily workflow has run, leave both **fresh_search** and
**example_data** unchecked. A blank **source_run_id** selects the latest available
candidate artifact from the default branch. To replay a particular day, open
**Actions → Daily London job shortlist → the desired run** and use the run ID
shown at the end of its browser URL.

At the bottom of the run's summary, **Artifacts → job-candidates** contains one
JSON file per successfully fetched provider batch. If fallback occurred, both
successful responses are retained; failed requests are not fabricated as empty
successful searches. Blank **snapshot_filename** chooses the newest batch in
that artifact. To assess the earlier primary response, supply its exact JSON
basename. Each run compares one selected batch, not a silently combined pool.

Selecting **fresh_search** makes a new request to the selected provider. Adzuna
may make its existing one-time smaller-page retry on HTTP 400. JSearch's current
eight pages can consume eight credits even though transported in one request.
The experiment does not trigger another provider merely because a ranker finds
no matches. The existing daily fallback policy is unchanged.

Snapshots are downloadable Actions artifacts, not daily Git commits. Retention
defaults to 90 days in `[archive]` and `[experiment]` in `config.toml`; expired or
deleted archives cannot be replayed. Archive upload/save failures warn without
blocking the normal morning email. GitHub artifacts are not private-secret
storage: people with repository read access and GitHub access can download them.
Only allowlisted public advert data and non-secret run/search metadata are saved.
Compiled agent artifacts also use 90 days, configured in `.github/workflows/aw.json`.
This is GitHub's maximum for public repositories. Omitting retention selects a
repository default rather than permanent storage. Changes apply to new artifacts;
existing uploads keep their original expiry. Planned long-term JSON preservation
will use a separate private archive; it must not rely on artifact retention.

## Read and compare results

Open the experiment run's **Summary**. The comparison shows which jobs each
method selected, model explanations and supporting quotations, and overlap with
the rules. Download **ranking-comparison** for the full JSON and Markdown.
Intermediate artifacts preserve the snapshot, direct receipt and agent output.

The direct route and agent route both see candidates before title/experience
exclusions. Code still validates records, removes repeats and suppresses jobs
already seen in that snapshot. Missing descriptions remain explicitly uncertain.
The direct model assesses configurable batches; within each suitability tier,
batch order is preserved. It does not perform an additional global pairwise
ranking pass. Agent order can differ. Overlap or changed order alone does not
establish that either method is better; inspect the actual reasons and review
both retained and rejected jobs.

Output checks require complete known IDs, allowed fit labels, bound input/prompt
hashes and quotations present in the supplied fields. Those checks establish
structure and textual presence, not that a quote supports an interpretation or
that a candidate is eligible. Agent output remains untrusted data and is checked
on a fresh checkout before comparison or test delivery. Advert/model text is
escaped so reports cannot introduce remote-loading images or HTML.

**Test** sends a single plain-text `[TEST]` comparison only to `GMAIL_SENDER`.
It does not read normal recipient secrets, change `seen.json` or consume the day's
normal delivery allowance. Repeating a test can therefore send another test to
you. It does not change the friend's normal email schedule.

## Configuration and development

`[candidate]` contains the nameless professional profile. `[ranking]` controls the
model, prompt, batch/token/time limits and selected suitability labels. The
initial cap is 100 unseen candidates; exceeding it fails visibly rather than
silently throwing away the rest. `[agentic]` sets the selected prompt-token budget,
not a claim about the provider's maximum context window. Engine tool/time limits
are versioned in the Markdown workflow frontmatter.

Keep `[ranking].method = "rules"` while experimenting. Changing it to
`"nebius_llm"` intentionally activates direct inference in the ordinary bot,
including its normal sends and fallback policy. Model errors then fail visibly
and the existing completion watchdog can alert about a missing normal delivery.
The experiment workflows themselves only offer preview/test.

The agent definition is `.github/workflows/agentic-ranking.md`. The official
`gh-aw` compiler, pinned at v1.2.2, generates `agentic-ranking.lock.yml`; do not
edit the generated file. Code checks recompile it without inference and reject
stale generated output. Developers use `gh aw compile agentic-ranking --strict`
after edits. Review changed secret/action/network references before approving a
safe-update warning. The compiled lock and `.github/aw/actions-lock.json` are
versioned together. No application package installation is required.

The handwritten YAML passes actionlint. The generated workflow uses newer
GitHub.com contexts and queue syntax that actionlint v1.7.12 does not recognize;
it is checked by the official compiler and by GitHub's workflow loader instead.
The new contexts are not supported on GitHub Enterprise Server.

The reusable caller permits issue-write for the compiler's conclusion job; the
inference job itself has only read permissions. Automatic issue publishing is
disabled. Code checks includes a deliberately skipped reusable call so GitHub
validates the nested permissions before running tests, without inference.

Direct model failures now save a safe `diagnostics` object identifying the batch,
error category and available HTTP status, completion reason and token usage.
A `partial_receipt` retains earlier validated assessments and progress counters.
The result remains failed: partial output is not a complete comparison and is
not automatically retried. Missing usage is unknown, not proof of zero charges.
No provider response body, authentication header or raw exception is saved.
