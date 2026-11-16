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

The wording checks recognize a small set of direct applicant requirements.
Examples include `requires 3+ years experience`, `minimum three years experience`
and `3 years experience required`. They also recognize `The successful candidate
must have 5 years experience` and `You will need at least 3 years experience`.

The experience limit is set by `[search].max_experience_years` in `config.toml`.
It defaults to two years. Zero and fractional limits are supported. Invalid
values cause an explicit error.

These checks do not establish overall eligibility. They cannot verify degree,
qualification, student or work authorization requirements. They also cannot
recover details that are absent from a provider's description.

## Corrections following review

The review reproduced three interpretation errors in the first version. The
following cases now have regression tests.

| Wording | Revised treatment |
|---|---|
| `1.5 years experience required` | Keep the decimal intact and retain the role. |
| `2.5 years experience required` | Compare the actual value and exclude it at the default limit. |
| `Requires 3 years experience or a relevant masters degree` | Keep the alternative uncertain and retain the role. |
| `No experience required for graduates; 3 years experience required for non-graduates` | Leave the conditional sentence uncertain. Do not exclude or promote the role on that sentence. |
| `3 years experience required and Python preferred` | Apply the mandatory experience requirement. The Python preference does not cancel it. |
| `3 years experience preferred and Python required` | Keep the experience uncertain. The Python requirement does not make it mandatory. |
| `Support a manager with ten years' experience` | Leave the manager's experience uncertain. Do not attribute it to the applicant. |

Sentence splitting preserves decimal points. Recognized alternatives are checked
before splitting clauses, so a semicolon cannot detach the graduate exception
from its requirement. Independent requirements joined by `and` or `but` are
then separated before preference wording is interpreted.

The experience checks also recognize title requirements after a colon or inside
parentheses. They previously handled only the spaced dash form consistently.

These are still limited English wording rules. An unrelated alternative in the
same sentence may leave a mandatory requirement unknown. An exception in a
different sentence or field may not be connected to its requirement. The checks
can also miss HTML markup, abbreviated units and other unrecognized language.
The regression examples provide evidence about those examples. They do not
establish correct interpretation of arbitrary adverts.

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
The review regressions add fractional years, alternative qualifications,
conditional graduate exceptions and unrelated preference wording. They also
cover title punctuation, direct applicant subjects and configurable limits.
Existing senior exclusions, relevance gates, deduplication and shortlist limits
remain tested. All 72 Python tests and 36 Cloudflare tests pass. Ruff checks and
formatting checks pass for the changed Python files.

Repeating the same 273-record replay after these corrections produces the same
counts and exactly the same CSV as before. That is expected: these saved titles
do not supply the description evidence needed to evaluate the new regressions.

No live searches, API credits, email submission, history writes or workflow
configuration changes were used. Better real-world validation needs a reviewed,
sanitized sample of complete adverts and rejected candidates; collecting that
data is outside this change.
