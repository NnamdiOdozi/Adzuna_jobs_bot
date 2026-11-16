# Finance vacancy comparison: Jev and Qwen — 2026-11-16

## Conclusion

Jev is the better candidate from this trial: its decisions agree with more of
the provisional reference labels, it is faster and cheaper, and it avoids
generating an open-ended answer. Both models retained the graduate investment
banking advert and the financial-services complaints role under the user's
latest clarification. Neither model establishes applicant eligibility.

The standard Python workflow now supports `ranking.method = "jev"`, with
`"rules"` disabling model assessment. The default remains rules until explicit
activation. Jev does not use a GitHub agentic workflow. The Qwen face-off used a
compact experimental response format; it is not a claim that the legacy Nebius
ranker, with its different explanation/quotation format, has been live-verified
with Qwen. No emails, live delivery-history writes or new vacancy searches were
made for this comparison.

## Comparable inputs and reference labels

Both models assessed the same forty previously saved JSearch candidates, with
their available descriptions. The shared profile is a Finance and Accounting
master's graduate, completed in 2025, with 0–2 years' experience. Junior accounting,
general finance, relevant complaints operations and graduate investment schemes
offering training are eligible. Actual legal occupations and mid-level/senior
roles are excluded. Missing prior derivatives expertise does not disqualify a
graduate scheme that teaches it. Unknown qualifications must not be invented.

Reference labels were assigned by Codex before the original trials: nineteen
plausible, seventeen unsuitable and four uncertain. The latest user clarification
restores complaints operations to plausible; investment banking remains plausible.
The reference labels are provisional and not independently reviewed by the
candidate. Matching them is agreement, not validated real-world accuracy.

## Forty adverts with descriptions: results and costs

| Trial | Calls | Input tokens | Output tokens | API seconds | Estimated USD | Reference agreement |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Jev 1.14 | 2 | 35,777 | 2,129 | 0.72 | $0.00150 | 35/40, 87.5% |
| Qwen successful fixed-slot trial | 1 | 21,687 | 801 | 7.28 | $0.00482 | 33/40, 82.5% |
| Qwen earlier incomplete attempt | 1 | 21,678 | 8,192 | 62.65 | $0.00925 | No valid complete result |
| Qwen including that failed attempt | 2 | 43,365 | 8,993 | 69.93 | $0.01407 | Only the completed trial is scored |

These are measured API token counts and elapsed times. Costs are calculated at
published direct-service rates, not reconciled account invoices: Jev $0.042 per
million input tokens with free output, and Qwen $0.20 input/$0.60 output per
million tokens. The successful Qwen pass costs about 3.2 times the Jev pass, but
both cost less than one cent at this scale. The difference alone should not drive
the choice: suitability and reliable operation matter more.

Pricing sources: [TypeSafe models](https://docs.typesafe.ai/models) and
[Nebius's model comparison table](https://dev.nebius.com/cookbook/openhands-agent-canvas).
The console model page could not be retrieved and the inference model-list API
does not expose pricing, so the Nebius cookbook rate is an estimate rather than
a confirmed account-specific tariff.

## Where the decisions differed

Jev's twenty-job shortlist contained eighteen provisional plausible matches and
two uncertain cases. Qwen's twenty contained sixteen plausible, two unsuitable
and two uncertain cases. Both rejected all twelve applicant-paid training-course
adverts. Jev also rejected the misleading location advert whose description
places work in Eccles/Wellingborough; Qwen selected it as a strong fit despite
the contradictory location field. Qwen selected the LSEG graduate programme
despite its graduation-year restriction, while Jev set it aside for review.

Qwen rejected commercial-finance broking where the reference considered it a
plausible finance role; whether the candidate wants sales-oriented work needs
her preference, so this disagreement is not automatically a model defect.
Both selected the Colgate programme welcoming 2026/2027 graduates and Checkout's
last-12-month graduation window. Exact dates or employer clarification remain
necessary. A high category probability is not verified eligibility.

Jev returned probabilities for strong, possible, unlikely and insufficient-
information outcomes. Python ranked strong/possible choices by their combined
probability, breaking ties with strong-fit probability. Qwen returned those same
four categories plus a discrete 0–5 suitability score, not a confidence claim;
Python ranked its acceptable choices by that score. Identical information and
categories support a classification comparison, but these ranking mechanisms
are not mathematically identical. No probability calibration was measured.

## Why Qwen's first attempt was incomplete

The linked model is **Qwen3-235B-A22B-Instruct-2507**, with 235 billion total and
22 billion active parameters. It is the non-thinking variant, not a 2.5B model.
[Qwen's model card](https://huggingface.co/Qwen/Qwen3-235B-A22B-Instruct-2507)
confirms the variant and recommends temperature 0.7.

The first request asked only for ID/category/score, not explanations, but its
schema permitted an unbounded array. It generated about 40,910 characters and
finished with `length` at 8,192 output tokens. The failure diagnostic retained
length and usage, not the full answer, so repetition cannot be proven afterwards.
A second, explicitly bounded trial gave each of the forty jobs a named answer
slot and used temperature 0.7 rather than zero. It completed with 801 output
tokens. Both schema and temperature changed, so the result does not isolate which
change caused the improvement. This was not evidence of excessive hidden reasoning.

## Historical backtest: 252 earlier sent-role records

Git history reconstructs 252 role records first recorded from 26 October to
16 November, across sixteen dates. Records contain normalized title, employer
and location. Descriptions, application requirements and rejected candidates
were not saved, and GitHub currently exposes no daily candidate archives.
Both models were explicitly told that those fields were unavailable.

| Historical title outcome | Jev | Qwen |
| --- | ---: | ---: |
| Strong or possible match | 1 | 128 |
| Insufficient information | 200 | 2 |
| Unlikely match | 51 | 122 |
| Total assessed | 252 | 252 |
| Requests | 6 | 3 |
| Measured API seconds | 2.12 | 89.15 |
| Estimated USD | $0.00448 | $0.00953 |

Jev's historical requests used 106,705 input/14,226 output tokens; Qwen used
32,245 input/5,135 output tokens. All requested historical assessments completed;
there were no automatic request retries. Output format was a category only for
Qwen; Jev also returned its category probabilities. Historical costs include
that separate workload and are not hidden inside the forty-advert trial.

The stark outcome difference is a limitation of title-only reconstruction, not
evidence that Jev found 251 bad jobs or that Qwen has better recall. Jev declined
to infer eligibility from missing descriptions; Qwen was much more willing to
classify. Neither model's historical decisions establish what the full adverts
required. There is no defensible historical accuracy percentage or recall figure.

Both rejected the two explicit lawyer titles. Among fifty-five titles containing
explicit senior/legal markers, Jev rejected thirty-nine and deferred sixteen;
none became eligible. Qwen rejected fifty-one but accepted four, including
Commercial Risk Financial Crime AVP. The other three were two credit-controller
titles and a semi-senior accountant title, where title-only interpretation can
be ambiguous. These markers are an audit screen, not independent ground truth.

## Evidence, integration and remaining limits

Detailed CSVs and requests/responses are saved locally under
`artifacts/evaluation/finance-faceoff-2026-11-16/`. They include
`full-description-comparison.csv`, `historical-title-comparison.csv`,
`comparison-summary.json`, pinned model names, usage and timings. Historical
records retain the first observed date and source commit. Local artifacts are
ignored by Git; they are not promised to be present in a fresh clone.

The Jev integration uses the existing provider fetching, duplicate history,
once-per-day delivery guard, sender-only test mode and email rendering. Its
category criteria are in `prompts/jev_suitability.json`; the candidate profile
and on/off method selection are in `config.toml`. API errors fail visibly and
save completed batches; no model failure silently switches back to rules.
Assessment receipts are downloadable as `job-ranking-receipts` on normal runs.

These controls establish complete question coverage, numeric validity, bounded
calls and history isolation. They do not prove semantic suitability, calibrated
probabilities, employer eligibility, inbox delivery or that future advert text
cannot mislead the classifier. Review borderline graduate cohorts, agree the
role of finance sales, and use future full-description archives for a stronger
held-out evaluation. See [setup and activation](../docs/JEV_RANKING.md).
