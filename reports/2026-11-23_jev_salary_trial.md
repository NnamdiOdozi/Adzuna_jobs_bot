# Live salary-wording assessment — 23 November 2026

The user authorised a live test. This reused the 42 vacancies obtained in today's
real eight-page JSearch request; it did not purchase another search. Jev assessed
the same 41 unseen/duplicate-filtered jobs with a separate salary question per job.
Three successful API requests contained 82 questions in total: 41 suitability
questions and 41 salary questions. No emails or sent-history changes occurred.

## Where the salary information comes from

All 42 JSearch records lack structured salary values. A local regex nevertheless
finds pound/GBP amounts in 18 descriptions. These include genuine starting pay,
future commission earnings, company financial figures and applicant-paid course
fees. A currency match alone is therefore not a salary extraction.

The additional Jev question reads the advert description and classifies current
annual GBP base pay against the configured cap. It returns a bounded category
and probabilities, not invented salary amounts. Python excludes above-cap pay
and ranges/upper bounds crossing the cap. Unknown salaries remain eligible.

## Actual live results

| Salary category | Assessed jobs |
|---|---:|
| Within £50,000 | 5 |
| Range/upper bound crosses £50,000 | 1 |
| Entirely above £50,000 | 0 |
| Unknown current annual GBP base salary | 35 |
| Total | 41 |

Examples checked against the actual description:

- Graduate Finance Accountant, real-estate startup: basic salary up to £65k.
  Classified crosses_cap and excluded, despite possible_fit suitability.
- Graduate Business Finance Advisor: £30,000–£35,000 starting salary plus bonus.
  Classified within_cap.
- Graduate Finance Broker: annual starting salary £36,000–£50,000.
  Classified within_cap.
- Entry-Level Commercial Finance Adviser: £37,000–£42,000 per annum plus bonus.
  Classified within_cap, but withheld on suitability.
- Vecta graduate broker: £70,000–£85,000 earnings after the programme, with
  commission. Classified unknown base pay rather than invented annual salary.
- The course adverts' £999 fees and £92 instalments were not treated as salaries.

Twenty jobs remain selected because at least twenty still pass suitability and
salary screening. Only two of those twenty have a within_cap salary decision;
the other eighteen have unknown base pay. The report does not establish that
the twenty all pay below £50,000. Reposts and sales-heavy roles remain issues.

## Implementation and evidence

`prompts/jev_salary.json` holds the question, category definitions and excluded
labels. `[jev].salary_policy_path` enables it and `[search].max_salary_gbp` supplies
the cap. Jev's adapter validates each salary answer and saves its category and
probabilities alongside suitability. Missing salary answers fail visibly.
The ordinary structured-salary Python screen remains in place.

The original numeric salary fields remain missing when JSearch supplies none.
The shortlist and receipts now also contain `salary_assessment`: Jev's category
and probabilities, copied minimum/maximum figures where a clear salary phrase
is present, its currency/explicit period and the exact supporting text. These
figures are extracted from the advert, not estimated by Jev. Unknown amounts
remain null. Existing trial records were enriched offline without new API calls;
`salary_enrichment.json` records this addition. Future Jev shortlists include it
automatically. Original provider salary fields remain unchanged.
This classifier does not populate those fields or recover pay absent from the
description. The [comparison CSV](2026-11-23_jev_salary_trial/comparison.csv)
shows extracted pay passages next to the decisions, rather than fabricated figures.
The regular email's numeric salary line has not been changed by this trial.

[Saved evidence](2026-11-23_jev_salary_trial/) includes full receipts, the selected
jobs, policy/profile, comparison CSV and operational events. Jev reported 77,476
input tokens and 4,213 output tokens. This is measured usage, not an invoice.
Separate salary questions roughly double the advert text supplied across questions;
we have not established a cheaper alternative through an equivalent live comparison.

Offline checks passed: 193/193 tests, 91.04% combined line/branch coverage. The
new mocked tests verify filtering above-cap/crossing salaries, retaining unknown
pay, and rejecting missing salary answers. Those tests do not prove classification
accuracy; the live examples above provide a limited spot-check.

No new JSearch request, webpage retrieval, email or history write was made in this
salary replay. Changes and evidence are local, not committed or pushed.
