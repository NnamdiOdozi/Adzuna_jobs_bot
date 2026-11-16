# Junior finance ranking review — issue #1

Target: a finance master's graduate with 0–2 years of professional experience.
Baseline: `3af73ec77fa67d75700bf970e0da1ffa4477cb70`.

## Three weaknesses and decisions

1. **Experience is ignored.** A junior title can pass with a mandatory five-year
   requirement. Check direct applicant requirements in titles and available
   descriptions before ranking. Reject only recognized mandatory minima above
   two years. Optional requirements, third-party experience and missing evidence
   remain unknown. Overlapping ranges use the lower endpoint. This deliberately
   favors retaining uncertain adverts over making speculative exclusions.
2. **Junior and associate signals are ambiguous.** Graduate Finance Associate
   outranks Finance Analyst today. That is defensible: associate seniority varies
   across employers. Keep the existing junior-first preference and use explicit
   mandatory experience to reject demonstrably unsuitable jobs. Do not move the
   associate penalty ahead of graduate/junior evidence.
3. **Finance keyword count rewards crowded titles.** Distinct finance words do
   not demonstrate early-career suitability. Keep finance relevance as the
   existing eligibility gate, then rank by compatible explicit experience,
   junior wording, the existing associate penalty and recency. Equal scores
   retain input order.

The wording parser accepts bounded English forms such as `requires 3+ years
experience`, `minimum three years experience`, `you need five years experience`
and `3 years experience required`. It intentionally leaves other formulations
unknown. It is not a semantic eligibility classifier. It does not verify degree,
qualification, student or work authorization requirements, or missing details
in provider snippets.

## Historical replay

The only saved advert evidence found is the existing
`filter_backtest_2026-11-12.csv` and title/employer/location history keys. There
are no saved full descriptions or publication timestamps. We cannot replay the
experience filter on historical descriptions or reconstruct actual shortlists.

`replay_junior_ranking.py` compares the baseline and proposed functions against
all 273 records in that CSV. Run from the repository root:

```sh
PYTHONPATH=. python3 reports/replay_junior_ranking.py
```

For this controlled title-only experiment, all records receive the same empty
publication date and a synthetic matching finance category. History is empty,
the limit includes the whole pool, and input order is the CSV order. Neither the
dates nor categories are historical facts. Duplicate suppression is identical
in both versions. The experiment isolates title ranking with recency neutralized.

| Measure | Result |
|---|---:|
| Historical title records | 273 |
| Baseline retained | 160 |
| Proposed retained | 160 |
| Eligibility changes | 0 |
| Retained records changing rank | 141 |
| Shared records in each experimental top 20 | 16 |

`junior_ranking_title_replay.csv` records both ranks for every retained record.
These are experimental positions, not historical delivery order or verified
suitability labels. The changes demonstrate sensitivity to keyword-count
removal; they do not prove better precision or recall. No saved description
evidence exists to validate mandatory-experience decisions against real adverts.

## Offline validation

Synthetic tests cover mandatory requirements above two years for both providers,
preferred experience, lower-bound overlap (`0–3`, `1–3`, `2+`, `two or more`),
missing descriptions, manager/company experience, and graduate associates.
Existing senior exclusions, relevance gates, deduplication and shortlist limits
remain tested. All 64 Python tests and 36 Cloudflare tests pass.

No live searches, API credits, email submission, history writes or workflow
configuration changes were used. Better real-world validation needs a reviewed,
sanitized sample of complete adverts and rejected candidates; collecting that
data is outside this change.
