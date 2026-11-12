# Historical title-filter backtest — 2026-11-12

The current filters remove much of the old senior and unrelated material, but
they are not sufficient to establish graduate suitability. Narrow exclusions
for legal careers and AVP improve the observed selection. Requiring every title
to say graduate, junior, trainee, entry level or assistant would discard many
plausible finance roles and is not recommended.

This was read-only research against GitHub and an offline title replay. No
Adzuna or model requests, emails, live configuration changes or history writes
were made. One parallel audit independently checked location-only repeats.

## Evidence and scope

The source is 16 versions of `state/seen.json`, from 24 October to 12 November
2026. They contain 273 distinct normalized title/employer/location records,
first recorded on 15 dates. The first version already contained 20 records;
253 more were added in subsequent commits. The initial 20 are an imported
baseline, not independently verified email deliveries. All versions were
monotonic: no existing history keys disappeared.

The latest source is [the 12 November history commit](https://github.com/NnamdiOdozi/Adzuna_jobs_bot/commit/ca02ba1becdf326ed46299e08fdb4f011a8e6bec).
Each row in [the detailed CSV](filter_backtest_2026-11-12.csv) identifies its
first source commit, title, employer, location and matching rule terms.
Titles are normalized history text, so original capitalization is unavailable.

The comparison uses the title rules introduced by commit `e4f7879`, also
verified in the [revision used by today's run](https://github.com/NnamdiOdozi/Adzuna_jobs_bot/blob/f3d3236b400224f34c125b8380ec1ad73a86e667/config.toml).
Earlier bulletins used different rules. This asks how today's title rules would
treat their records; it does not reproduce their original searches or rankings.

History lacks descriptions, category tags, publication timestamps and rejected
search results. Therefore this replays the finance-title and exclusion checks,
not the complete category gate, ranking or search. It does not infer category
from a title. An old title passing here could still fail today's category gate.
Dates describe first entry into history, rather than independent inbox receipts.
Dates without new role records are absent, not assumed to be failed runs.

## Results

| First recorded | Historical records | Pass current title rules | Pass after proposed AVP/legal exclusions |
|---|---:|---:|---:|
| 2026-10-24 | 40 | 25 | 25 |
| 2026-10-26 | 20 | 14 | 14 |
| 2026-10-27 | 20 | 10 | 10 |
| 2026-10-28 | 20 | 11 | 11 |
| 2026-10-29 | 20 | 13 | 13 |
| 2026-10-30 | 20 | 9 | 9 |
| 2026-10-31 | 20 | 11 | 11 |
| 2026-11-02 | 20 | 10 | 10 |
| 2026-11-03 | 20 | 14 | 14 |
| 2026-11-04 | 20 | 13 | 13 |
| 2026-11-05 | 8 | 5 | 5 |
| 2026-11-06 | 3 | 1 | 1 |
| 2026-11-10 | 20 | 2 | 2 |
| 2026-11-11 | 11 | 11 | 11 |
| 2026-11-12 | 11 | 11 | 6 |
| **Total** | **273** | **160** | **155** |

Today's title rules reject 113 records: 84 have finance wording but an excluded
seniority/title term, and 29 lack the configured finance wording. These are rule
outcomes, not 113 confirmed unsuitable jobs. Some exclusions are questionable.

The proposed additional terms tested were `avp`, `lawyer`, `solicitor`,
`barrister`, `counsel`, `paralegal`, `pqe` and `magic circle`. Five currently
passing records match, all first recorded on 12 November:

- Asset Finance Lawyer — Eximius Law.
- Finance Lawyer 1–3 PQE — Eximius Law.
- Banking Finance Associate 1–4PQE Magic Circle Firm — Lewis Hunt.
- Magic Circle Asset Finance 1–4 — Eximius Law.
- Commercial Risk Financial Crime AVP — Crown Agents Bank.

Adding only the two explicitly agreed words, `avp` and `lawyer`, removes three
records. The wider tested set removes five. A whole-word `pqe` rule does not
match `4pqe`; the `magic circle` phrase catches that observed title. Several
proposed legal terms have no historical matches, so this sample provides no
evidence about their effect on future adverts.

## Preserve plausible matches

Only 13 of the 160 passing records contain the current junior-preference words.
Making those words compulsory would reject the other 147, including Finance
Analyst, Corporate Finance Analyst, Credit Analyst and Operational Treasury
Analyst. These are plausible candidates, not verified suitable jobs. Conversely,
the 13 include a PA/Team Assistant at an investment bank: assistant wording
alone does not establish a finance career or graduate fit.

The AVP/legal proposal retains all 13 junior-word records. That is a useful
sample check, not proof that the proposal has no false exclusions.

| Observed problem | Evidence | Recommendation and trade-off |
|---|---|---|
| Missing finance wording | Three Junior Business Analyst Bank records from Huxley Associates fail on 5 November | Consider the specific phrase `business analyst bank`; do not add `bank` alone, which also matches Bank Barista and Pharmacy Support Worker Bank. The three records are not three confirmed distinct vacancies. |
| Singular-only wording | Analyst Private Debt Investments and Analyst Infrastructure Investments fail | Consider `investments` or narrower role phrases. Whole-word matching does not automatically recognize plurals. This could also admit non-investment occupations mentioning an employer. |
| Employer wording mistaken for seniority | IG Credit Analyst Generalist Global Asset Manager London fails on `manager` | The word appears in the employer description, not clearly the applicant's rank. Avoid broad exceptions until role requirements can be checked. |
| Legal word used in accounting | Two Legal Entity Control Financial Accountant records pass | Do not exclude the bare word `legal`; it would remove accounting roles as well as legal careers. Graduate suitability remains unverified. |
| Ambiguous associate rank | Eleven passing records contain `associate`, including Analyst/Associate titles | Keep the current lower preference rather than blanket exclusion without experience evidence. |

## Further mismatches to review

Specific phrases identify six additional currently passing historical records:
Executive Search Consultant Alternative Investment (two), Content Producer
121 Mining Investment (one), Accounting Specialist Tutor (one), Night Auditor
(one), and Risk Management Surveyor (one). These expose occupational ambiguity
in finance wording. They are candidates for scoped exclusions, not six
independently confirmed false positives. The full adverts were not retrieved.

Applying those exact five phrases in addition to the AVP/legal proposal would
leave 149 historical records. The 13 junior-word records would remain. This is
a simulation only; the phrases have not been added to application config.

Other passing titles include Finance Business Partner (four records including
Revenue Finance Business Partner), expert titles (four), Market Risk Supervisor
(one), Technical Accountant and Management Accountant. Titles suggest useful
review targets, but cannot prove an essential experience requirement. Generic
`accountant`, `analyst`, `consultant` or `associate` exclusions would be too broad.
Some summer/placement programmes also require student or previous-intern status;
junior rank alone does not establish that a recent graduate is eligible.

## Duplicate suppression

There are 259 distinct normalized title/employer pairs among the 273 role
records. Thirteen pairs have multiple locations, including seven appearing
only within one day. Six pairs recur across days with only location changing:

| Employer and title | First record | Later record |
|---|---|---|
| Wells Fargo — Associate Credit Derivatives Trader | 2 Nov: The City, Central London | 4 Nov: London, UK |
| Sainsbury's — Commercial Finance Manager Technology 6m FTC | 30 Oct: London, UK | 31 Oct: Farringdon, Central London |
| Rule Recruitment — Executive Search Consultant Alternative Investment | 2 Nov: Central London, London | 3 Nov: London, UK |
| Harvey Nash — Trade Finance Analyst Junior ARM to RM | 5 Nov: London, UK | 6 Nov: South East London, London |
| Wells Fargo — EMEA Payroll Specialist | 11 Nov: The City, Central London | 12 Nov: London, UK |
| Wells Fargo — Legal Entity Control Financial Accountant | 11 Nov: The City, Central London | 12 Nov: London, UK |

These are probable repeats, not proof of identical vacancies. Ignoring location
would suppress them but could hide genuine separate openings at one employer.
The old history does not retain descriptions or requisition references to
resolve that ambiguity. Do not silently change the duplicate key as part of a
title-filter adjustment.

## What the backtest proves and cannot prove

The replay establishes reproducible rule matches on the historical title sample.
It does not measure precision, the share of selected jobs actually suitable, or
recall, the share of all suitable jobs retained. Both require suitability labels;
recall also requires jobs rejected by the old system or another representative
candidate set. The historic sent set is biased by earlier searches and filters.

No experience or qualification requirements were verified. No reviewer or model
labelled every record for suitability. Jev was not called: this work compared
deterministic text rules and history keys, rather than assigning semantic labels.

For future evaluation, save a sanitized pre-filter candidate set containing job
ID, title, employer, category, location, available description and each filter's
decision from the existing daily response. This needs no extra Adzuna search.
Review suitable/unsuitable/unknown examples against the candidate's agreed
criteria, including rejected jobs. Missing details must remain unknown.
Persisting descriptions and any publication or retention policy should be agreed
before implementation; these are not currently saved or exposed as artifacts.

## Recommended next changes, not applied

1. Add the agreed AVP/lawyer exclusions, and agree the wider legal-title phrases
   that catch the two remaining observed legal-career titles.
2. Agree narrowly scoped occupation exclusions and finance-title exceptions,
   using the examples above. Keep ordinary analyst/accountant roles eligible.
3. Separately decide how aggressively to suppress changed-location repeats.
4. Save future pre-filter decisions so suitability and missed matches can be
   evaluated honestly without spending additional search requests.
