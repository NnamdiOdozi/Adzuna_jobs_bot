# Ranking experiment implementation blueprint — 2026-11-16

Approved scope: archive daily fetched candidates, compare deterministic rules,
direct Nebius ranking and a GitHub Agentic Workflow; manual preview or one test
email to the sender only. Daily delivery remains rules-based by default.
Model: `nvidia/nemotron-3-super-120b-a12b`.

## Components and contracts

1. `jobs_bot/snapshots.py` (approximately 180 lines) owns candidate snapshot writes.
   `create_snapshot(jobs, provider, config, seen, *, run_id="local", commit="local",
   captured_at=None) -> dict` builds a versioned, credential-free JSON document.
   `save_snapshot(snapshot, directory) -> Path` writes it atomically.
   `load_snapshot(path) -> dict` checks schema, content hash and necessary types.
   `record_snapshot(jobs, provider, config, seen) -> Path | None` reads the
   non-secret archive configuration and logs a safe warning if saving fails;
   diagnostic failure must not stop normal email delivery.
   Snapshot keys: `schema_version=1`, `snapshot_id`, `captured_at`, `provider`,
   `jobs`, `seen`, `config`, `metadata`, `content_hash`. `config` contains only
   allowlisted search and JSearch settings. `metadata` contains GitHub run/commit
   identity. Jobs preserve available description, title, ID, employer, location,
   category, date, application link, source and salary fields, not arbitrary
   response properties. Never store credentials, request URLs/headers, email
   settings or error bodies. Hash canonical content excluding `content_hash`.
   Snapshot IDs must distinguish both provider attempts in the same run.
   Integrate recording immediately after each successful provider fetch in
   `__main__.py`, before suitability filtering, including empty primary results.
   Failed fetches have no fabricated successful snapshot. Existing fallback
   behavior, accepted-notice behavior and history writers remain unchanged.

2. `jobs_bot/model_ranking.py` (approximately 250–300 lines) owns direct inference
   and shared model-output validation; use stdlib HTTPS without a new runtime SDK.
   `prepare_candidates(jobs, seen, config) -> list[dict]` removes seen/duplicate
   jobs and validates necessary fields without title/experience exclusions.
   `ranking_request(candidates, config) -> dict` returns the shared profile,
   prompt and JSON response schema. IDs and all bounded fields use enums.
   `validate_assessments(payload, candidates, config) -> list[dict]` requires
   exactly one result per supplied ID, no invented IDs, known suitability labels,
   bounded reason strings, and evidence quotations found verbatim in supplied
   title/description/location. Unknown evidence is represented explicitly.
   `rank_jobs(jobs, seen, config, *, api_key=None) -> tuple[list[dict], dict]`
   calls configured Nebius Chat Completions in bounded batches. Return selected
   jobs plus a receipt containing all validated assessments, model/prompt identity,
   input hash, token usage, call count and elapsed time. Labels are
   `strong_fit`, `possible_fit`, `unlikely_fit`, `insufficient_information`.
   Model array order ranks within each configured label tier. Keep all decisions
   for review even when only strong/possible jobs are selected. Reject missing
   assessment rows rather than quietly dropping candidates. No numeric confidence.
   Only the intended HTTPS Token Factory endpoint receives its credential; reject
   redirects, log no raw errors/bodies, and do not automatically retry charged
   inference or repair malformed output. Description truncation must be explicit
   in inputs and receipts. Budgets, batch size, profile, prompt file and limits
   live in `config.toml`, not dispersed literals.

3. `jobs_bot/experiments.py` (approximately 250 lines) owns the manual CLI and
   report generation, using snapshots and ranking without normal history writes.
   Commands: `prepare` takes one fresh configured-provider fetch or reuses a
   downloaded snapshot; `rank` produces rules/direct-model reports;
   `agent-input` writes the same candidate/profile/prompt/schema for the agent;
   `compare` validates optional agent results and writes JSON/Markdown summaries;
   `test-email` sends a single comparison message only to `GMAIL_SENDER` using
   the existing Gmail service. No normal recipient variables are read for test
   delivery. Subjects begin `[TEST]`. Required inputs include the candidate
   snapshot hash; receipts bind exact model/prompt/config inputs. Model failure
   remains failed, never mislabeled as a successful rules result. Rules/direct
   ranking must consume the same snapshot and seen set. The experiment's fresh
   provider selection is explicit; do not silently fetch again because an
   experimental ranking is empty. Existing daily semantic fallback is unchanged.

4. `prompts/job_suitability.md` describes the shared decision policy and defines
   fit labels against a nameless finance master's / 0–2-year profile. Advert text
   is untrusted data, never instructions. Missing/truncated information is not a
   confirmed negative. No CV, private email address or application submission.

5. GitHub workflows: daily workflow uploads `artifacts/candidates` as an artifact
   with configurable retention (30 days initially), even if later delivery fails.
   Upload failure warns without blocking the morning email. Existing test-result
   gate remains. New manual comparison workflow can replay a supplied archive
   run ID or deliberately request a fresh search; default is replay. It runs
   rules/direct ranking and prepares a reusable agent input. A genuine `gh-aw`
   Markdown workflow, compiled to its lock YAML, uses Copilot BYOK routed to Nebius
   and the same exact model and assessment format. Auxiliary inference routes
   must not silently require paid Copilot inference. Agent gets no Gmail or job
   API credentials and no repository write permissions. Deterministic validation
   occurs after its result, before optional test email. GitHub-hosted execution
   is the intended user path; local compilation is a development tool only.

## Verification and limits

Offline tests exercise capture-before-filtering, sanitization, failed diagnostic
save, two-provider capture, hash tampering, replay without fetching, duplicate
and seen checks, output completeness/evidence, budget limits, invalid/model HTTP
responses, and sender-only test delivery without history changes. Add both suites
and workflow compiler checks to Code checks. No paid requests during implementation.
Mocked or schema checks cannot establish semantic suitability, provider/model
availability or actual inbox receipt. Report those as unverified until an
explicitly authorized bounded live test. Prompt, model and input versions belong
in artifacts so a model's self-report cannot substitute for observed execution.

Implementation order: snapshots and tests; ranker and tests; experiment commands
and tests; GitHub workflow compilation and integration; offline review; publication
and mocked Code checks. Document GitHub Secret setup and the exact manual test
navigation. Production activation of model ranking is a separate explicit choice.
