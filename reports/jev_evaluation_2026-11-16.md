# Jev suitability evaluation — 2026-11-16

## Decision and scope

The user chose Jev as the preferred direction for semantic vacancy assessment,
primarily on cost. This report records a real local trial, not an integrated
production feature. Daily delivery remains on Python rules; GitHub's workflows
have not been changed or pushed by this trial.

The existing secret launcher supplied authentication to the direct TypeSafe API.
No secret files or credential values were inspected. Two requests were made to
`POST https://api.typesafe.ai/v1/systemone`, without retries, using the pinned
`jev-1.14.0` model. Each request contained twenty independent Choice questions,
one per saved vacancy. No JSearch/Adzuna calls, Nebius calls, emails or delivery
history writes occurred. Jev was actually called and supplied all forty decisions.

## Inputs and selection policy

The existing eight-page JSearch snapshot supplied forty unseen, deduplicated
candidates. The candidate profile and common interpretation rules were shared
state. Each question contained its own title, employer, location and full available
description. Long provider identifiers, links and irrelevant fields stayed local.
Short question identifiers bound answers back to their original vacancies.

The four outcomes were `strong_fit`, `possible_fit`, `unlikely_fit` and
`insufficient_information`. Criteria distinguished genuine paid vacancies from
applicant-paid courses, actual duties from the employer's industry, and mandatory
eligibility from preferences. Missing candidate qualifications were not invented.

Python accepted adverts whose selected outcome was strong or possible fit, then
sorted them by `P(strong_fit) + P(possible_fit)`, breaking ties with the strong-fit
probability. It selected up to twenty. This is probability of the defined match
categories, not likelihood of interview or job offer. No tuned numeric threshold
or automatic application authority was introduced.

## Results against provisional labels

| Reference assessment | All candidates | Rules shortlist | Jev shortlist |
| --- | ---: | ---: | ---: |
| Plausible match | 19 | 6 | 18 |
| Unsuitable | 17 | 13 | 0 |
| Uncertain | 4 | 1 | 2 |
| Total | 40 | 20 | 20 |

Jev rejected all twelve copies of the £999 training-course advert. It also
rejected the reception/VIP support role at a finance firm and the misleading
Welwyn Garden City advert whose description gives work in Eccles/Wellingborough.

The one provisional plausible match rejected was Lendable's Operations
Investigations Graduate. Jev assigned about 0.19 combined fit probability.
Whether complaints operations in a lender counts as desired finance work is a
real preference boundary, not automatically a model defect. The reference label
used a broad financial-services interpretation; junior accounting may warrant a
narrower interpretation. Keep this example for the user's decision.

Two uncertain adverts entered the Jev shortlist: Colgate-Palmolive's programme
welcoming 2026/2027 graduates, and Checkout.com's programme with a last-12-month
graduation condition. Their combined fit probabilities were about 0.59 and 0.63.
The exact graduation date or employer eligibility clarification is still needed.
Jev rejected the contradictory Mercedes-Benz cohort advert and the data-engineer
role whose technical eligibility is unknown in the profile.

Jev selected only strong/unlikely labels in this trial despite having two other
options. Therefore category names alone should not be read as proof of certainty.
Preserve the full probability distributions and flag these borderline cases for
review rather than treating the chosen category as verified eligibility.

## Usage and latency

| Request | Questions | Input tokens | Output tokens | Measured elapsed |
| --- | ---: | ---: | ---: | ---: |
| 1 | 20 | 17,863 | 1,063 | 0.371 seconds |
| 2 | 20 | 14,394 | 1,063 | 0.328 seconds |
| Total | 40 | 32,257 | 2,126 | 0.699 seconds |

At the published direct-API input price of $0.042 per million tokens, with free
output tokens, estimated inference cost is $0.001354794. This is a calculation
from returned usage and published pricing, not an account-billing reconciliation.
Elapsed time measures the two API calls, not the entire evaluation workflow.

## Evidence and validation boundaries

Saved locally under `artifacts/evaluation/jev-2026-11-16-` are the manifest, both
request payloads, both responses with usage/timing and request hashes, the joined
evaluation CSV, shortlist JSON and summary JSON. All forty expected answers were
present, categories were valid, probabilities were finite and summed to one, and
response snapshot bindings matched the frozen reference labels. Request/response
files contain no authentication headers or credential values.

These checks prove structural completeness and numerical validity, not semantic
correctness, calibration or applicant eligibility. The reference labels were
created by Codex before the trial, not independently reviewed by the candidate.
This is one graduate-targeted query containing repeated adverts, not a held-out
representative benchmark. No conclusion about universal accuracy or probability
calibration follows from this comparison.

## Integration still required

Add Jev as an explicit ranking method in the application and manual comparison
flow, with centrally editable criteria and selection policy, repository Secret
mapping, offline boundary tests, inspectable probabilities and safe failure
records. Keep Python responsible for history, selection and email formatting.
Jev does not need the Copilot agent runtime or a generated agentic workflow.
Agree how to display borderline cases and the complaints-operations boundary
before activating daily delivery. Current timer, providers and history stay intact.

Official references: [Models and pricing](https://docs.typesafe.ai/models),
[Choice probabilities](https://docs.typesafe.ai/primitives/choice),
[Structured questions](https://docs.typesafe.ai/primitives/advanced).
