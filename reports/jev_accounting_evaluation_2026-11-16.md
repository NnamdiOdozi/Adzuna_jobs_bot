# Jev reassessment with corrected accounting profile — 2026-11-16

## Subsequent user clarification and provisional score

The user confirmed that financial-services complaints work should be rejected,
but graduate investment banking and graduate schemes offering training should
remain eligible. Lack of prior derivatives expertise must not itself reject a
programme that teaches those skills. The investment-banking rejection is therefore
a clear error under the clarified policy. Revise the criteria before any future
trial; no further paid calls were made for this clarification.

Mapping strong/possible to suitable, unlikely to unsuitable and insufficient to
review, the saved results agree with 34/40 provisional reference labels (85%)
after changing the complaints reference to unsuitable. The other original labels
remain frozen. Six disagreements include the investment-banking rejection, cautious
review of a plausible accounting vacancy, and unresolved graduation/student/technical
role cases. This is provisional three-way agreement, not independently verified
accuracy, calibration, or evidence that all six disagreements are clear mistakes.

The user clarified that the master's is in Finance and Accounting, with an
accounting emphasis, rather than specialist markets/derivatives expertise.
Legal occupations and mid-level/senior roles are explicitly excluded. The user
authorized a reassessment of the same forty saved JSearch candidates.

Two twenty-question direct Jev requests completed successfully without retries,
using `jev-1.14.0`. No new vacancy searches, Nebius calls, email sends or normal
history writes occurred. All forty expected answers passed category, probability
and coverage checks. Original trial requests and responses were preserved.

The corrected candidate profile is also saved in local `config.toml` so future
experiments do not silently revert to the earlier finance-only wording. Daily
ranking remains Python rules: these semantic exclusions are not yet integrated
into normal delivery, and no changes have been pushed or deployed.

## Results

| Outcome | Jobs |
| --- | ---: |
| Strong fit | 13 |
| Possible fit | 4 |
| Unlikely fit | 20 |
| Insufficient information | 3 |

Python shortlisted the seventeen strong/possible matches, sorted by combined
fit probability with strong-fit probability as the tie-breaker. It did not fill
the remaining places with unsuitable or insufficient-information adverts.
Against the earlier provisional reference labels, sixteen selected adverts were
plausible and one uncertain. Those labels used the earlier broader profile and
are not a fresh independent accuracy benchmark for the revised requirements.

The Graduate Investment Banker advert changed from strong to unlikely fit.
Commercial finance advisor, depositary analyst, financial administrator and
commercial finance broker changed from strong to possible fit. Strong selections
include graduate finance assistants, finance administration, graduate accounting,
treasury analysis and decision-support work.

Three adverts now require review: the real-estate finance accountant advert
mentioning a 2022/2023 graduation cohort; Checkout.com's last-12-month graduation
eligibility; and the Allianz student summer internship. The Colgate-Palmolive
programme welcoming 2026/2027 graduates remains selected despite an unresolved
cohort question, at about 0.64 combined fit probability. Thus this run improves
uncertainty handling but does not remove the need to check graduation eligibility.

All twelve paid-course adverts remain rejected. Financial-services complaints
operations and the data-engineering role remain rejected. There are no explicit
legal-role examples in this forty-job pool, so naming legal exclusions in the
criteria does not establish live performance on lawyers; retain the synthetic
legal case for the eventual integrated evaluation.

## Usage and evidence

The two requests reported 35,985 input tokens and 2,135 output tokens and took
about 0.757 seconds together. At the published input rate of $0.042 per million
tokens, estimated cost is $0.00151137, excluding any account-specific billing
differences. No assumption of calibrated probabilities follows from these counts.

Saved artifacts are under
`artifacts/evaluation/jev-2026-11-16-accounting/`: the request/response files,
manifest, evaluated rows, selected shortlist and usage summary. Short identifiers
map back to the same original jobs. These local files are ignored by Git and are
not available to the GitHub comparison workflow until explicitly integrated.
