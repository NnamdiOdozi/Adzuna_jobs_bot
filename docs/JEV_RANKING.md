# Jev in the normal jobs workflow

Jev replaces the suitability/ranking step while Python retains responsibility
for vacancy fetching, history, selecting up to twenty jobs and email formatting.
It does not need Copilot, an agentic workflow or another Cloudflare Worker.
The user has selected `[ranking] method = "jev"` for normal delivery. Setting
it to `"rules"` disables model assessment; `"qwen"` uses the compact Qwen client.

## Enable or disable

1. In GitHub, open **Adzuna_jobs_bot → Settings → Secrets and variables → Actions
   → Secrets → New repository secret**. Name it **TYPESAFE_API_KEY**, paste your
   TypeSafe credential and select **Add secret**. The existing local secret
   launcher already supplied this name successfully in the trials. Local secret
   configuration is user-managed and has not been inspected or modified.
2. In `config.toml`, choose `[ranking] method = "jev"`, `"qwen"` or `"rules"`.
   Qwen requires repository Secret **NEBIUS_KEY** and uses the settings under
   `[qwen]`; its fixed answer slots bound output and its scores are suitability,
   not confidence. `[jev]` supplies the pinned model, endpoint, batch size,
   timeout and criteria-file path. Shared ranking settings bound candidates,
   calls, elapsed time and description length. There is no automatic model retry
   or silent fallback to rules on inference failure.
3. The anonymous candidate profile is under `[candidate]`. It now describes a
   Finance and Accounting master's graduate with 0–2 years, includes relevant
   complaints operations and graduate investment programmes with training, and
   excludes actual legal occupations and mid-level/senior work. The four outcome
   descriptions are editable in `prompts/jev_suitability.json`.
4. Commit and push reviewed changes for GitHub to use them. A local edit alone
   does not alter the published workflow, and publication does not require
   changing the Cloudflare timer. After Code checks passes, open **Actions →
   Daily London job shortlist → Run workflow**, choose **test**, and run it on
   **main**. This makes a real vacancy search and model calls but emails only
   the sender and leaves normal sent-job history unchanged. Preview omits the
   email but still incurs search and model usage. Send uses normal recipients.
5. Inspect **job-ranking-receipts** under the run's artifacts. Receipts record
   categories, probabilities, model version, usage and input hash. Failed model
   requests remain failures and do not mark jobs as sent; partial receipts retain
   completed batches. The existing Cloudflare completion watchdog remains the
   recovery/notification mechanism for an absent normal delivery.

## Reuse saved candidates without another vacancy search

The manual ranking command also accepts Jev:

```sh
/home/nodozi/.local/bin/run-with-secrets python3 -m jobs_bot.experiments rank \
  --snapshot artifacts/evaluation/jsearch-2026-11-16-eight-pages.json \
  --method jev --output artifacts/evaluation/jev-replay.json
```

This spends Jev credits only. It sends no email and does not alter normal history.
The snapshot is local and ignored by Git; a fresh clone does not contain it.
The existing **Compare finance job rankings** agentic experiment remains the
separate Nebius path and is not repurposed as the Jev daily workflow. Its agent
driver is configured by `[agentic].model`, independently of the daily method.
It now names Qwen, but the earlier Copilot-runtime provider-discovery failure
has not been fixed or live-retested. Do not rely on that experiment for morning mail.
The legacy `nebius_llm` selector is retained for older experiments; use `qwen`
for the bounded standard-workflow client. The replay command also accepts `qwen`.

## What selection and validation mean

One question assesses each unseen, deduplicated advert. Up to twenty questions
share one request; model outputs are categories and probabilities, not long
generated explanations. Python retains strong/possible matches, sorts by their
combined probability with strong-match probability as a tie-breaker, and takes
up to the configured shortlist limit. It never fills spare places with rejected
or insufficient-information jobs. The numbers are not interview probabilities.

Coverage, category and numeric checks establish a complete, structurally valid
result. They do not establish applicant eligibility or probability calibration.
A confidently selected graduate programme may still have an incompatible cohort
or student requirement. The candidate profile's exact graduation month and other
unknowns must not be invented. Human review of borderline programmes remains
necessary. Historical sent-job titles alone are insufficient to measure recall.

The live [Jev/Qwen comparison](../reports/finance_model_faceoff_2026-11-16.md)
records measured token usage, estimated costs, failures and disagreements.
