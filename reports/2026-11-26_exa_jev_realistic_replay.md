# Realistic Exa → Jev replay — 2026-11-26

Used the 26 saved JSearch vacancies from run 45774259929. Made a live Exa
contents request, followed by the production Jev ranker with ten-vacancy
batches and the original snapshot's sent-job history. No JSearch request,
email submission or delivery-history update occurred.

Exa enriched 22 vacancies in 7.775 seconds. After shared duplicate/history
filtering, 24 candidates reached Jev in batches of 10, 10 and 4 vacancies.
All three calls succeeded, and ten vacancies were selected.

| Call | Vacancies | Questions | Input tokens | Output tokens |
|---|---:|---:|---:|---:|
| 1 | 10 | 20 | 30,619 | 1,020 |
| 2 | 10 | 20 | 36,565 | 1,024 |
| 3 | 4 | 8 | 15,651 | 412 |
| Total | 24 | 48 | 82,835 | 2,456 |

The first two calls together consumed 67,184 input tokens. Combining their
vacancies into one twenty-vacancy call would remove one copy of the shared
candidate context, so that sum is not an exact merged-request token count.
It nevertheless strongly supports input size as the earlier HTTP 400 cause.
The exact previously rejected enriched payload was not retained, so the cause
cannot be proved retrospectively. All current calls stayed below the 64k
per-request limit. Token usage includes the shared state and questions, not
just vacancy descriptions. Successful API calls and schema checks establish
execution, not that every suitability decision was correct.

The complete enriched vacancy text was saved before ranking. Local evidence:
`artifacts/evaluation/exa-jev-realistic-2026-11-26/` contains
`enriched-candidates.json`, `receipt.json`, `shortlist.json` and `summary.json`.
At the documented $0.042 per million input tokens, Jev cost approximately
$0.00348. Exa's configured 24 unique target pages imply approximately $0.024
at $0.001 per text page; this is an estimate, not an invoice measurement.
