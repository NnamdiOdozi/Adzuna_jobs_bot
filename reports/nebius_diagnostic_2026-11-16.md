# Nebius ten-job diagnostic — 2026-11-16

One explicitly authorized generation request reused the first ten candidates
from the saved JSearch evaluation batch. No job searches, emails, automatic
retries or delivery-history writes occurred. Settings stayed on the global
Token Factory endpoint, Nemotron 3 Super and an 8,192-token generation allowance.

The response arrived after approximately 33.9 seconds:

- HTTP status: 200.
- Completion reason: `length`.
- Reported prompt tokens: see the saved diagnostic JSON.
- Reported completion tokens: 8,192, exactly the requested allowance.
- Final answer content: zero characters.
- Attempted calls: one; validated batches: zero.

This establishes generation-budget exhaustion for this trial, not a failed
connection or an oversized input. The response is consistent with reasoning
consuming the allowance before a final answer; no separate reasoning-token
count was retained, so that allocation is an inference rather than a measurement.
The previous uninstrumented failure cannot retrospectively be proven identical.

Both global and US-central model-list endpoints also returned HTTP 200 and listed
the configured model, using non-generating requests. The environment-variable
name remained NEBIUS_KEY; no credentials were inspected or renamed.

Local evidence: `artifacts/evaluation/jsearch-2026-11-16-ten-job-result.json`
and `/tmp/adzuna-nebius-ten-job-diagnostic.log`. A sensible next trial should
increase the generation allowance or constrain reasoning using provider-supported
options, then record the same diagnostics. It has not been run automatically.
The separate GitHub agent provider-discovery failure remains unresolved.
