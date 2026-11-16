# Real-vacancy ranking evaluation — 2026-11-16

## Scope and reference labels

The previously authorized eight-page JSearch acquisition returned 42 adverts.
Existing history/duplicate checks leave 40 candidates. This evaluation reused
that local snapshot, with no further vacancy searches, emails, history writes
or changes to normal delivery. The synthetic fixture remains unchanged.

Codex assigned provisional reference labels before inspecting any model output:
19 plausible early-career finance opportunities, 17 unsuitable and 4 uncertain.
These are agent assessments, not human-reviewed ground truth. A plausible match
means worth considering, not verified eligibility. Unknown degree grades,
technical skills, work authorization and exact graduation dates were not invented.
The geographic reference uses the user's broader Home Counties preference;
it is not a computed 50 km boundary. Future-start programmes were not rejected
merely because their start date is in 2027.

The four uncertain cases are a programme welcoming 2026/2027 graduates without
an explicit exclusion of earlier graduates, a programme with contradictory
graduation-year wording, a last-12-month graduation window requiring the actual
graduation date, and a financial-crime data engineering role requiring technical
skills not supplied in the candidate profile.

The reference JSON was saved before invoking Nebius. No Jev calls were made:
this is the explicitly requested Nebius comparison, and the reference labels
remain disclosed provisional agent judgments rather than another paid judge.

## Python rules results

| Reference assessment | All 40 candidates | In the actual 20-job shortlist |
| --- | ---: | ---: |
| Plausible match | 19 | 6 |
| Unsuitable | 17 | 13 |
| Uncertain | 4 | 1 |

Only 6/20 shortlisted adverts are plausible matches against these labels. One
additional advert remains uncertain; it is not counted as an established error.
The shortlist retains 6/19 plausible matches and leaves 13 outside the top 20.
An offline replay with a larger shortlist limit shows all 40 pass the existing
JSearch eligibility rules. Thus the 13 missed plausible matches were displaced
by ranking and the 20-job cap, rather than rejected by suitability filters.

Twelve adverts contain the same £999 accounting-training course description
under different towns. Eleven appear in the actual shortlist. The description
explicitly says it is a training course and fees apply. These are course offers
with a later placement promise, not current salaried vacancies. The other two
unsuitable shortlisted adverts are reception/VIP office support at a finance
firm and a scheme whose description places the work in Eccles or Wellingborough
despite its Welwyn Garden City location field.

The rules also let through graduation-year and student-status mismatches, although
those did not all reach the top 20. The most important missing controls here are
paid-course detection, occupation relevance, applicant eligibility and reconciling
location fields with the description. These are distinct from seniority checks.

## Repeated adverts and limits of the measurement

Grouping identical title, employer and description across locations reduces the
40 candidates to 29 content groups: 19 plausible, 6 unsuitable and 4 uncertain.
The selected adverts represent 10 such groups: 6 plausible, 3 unsuitable and
1 uncertain. This grouping is an analytical view only; normal duplicate handling
has not changed. The repeated course therefore inflates the per-advert error
count, while also demonstrating the real cost of letting it fill the shortlist.

Some Newlon adverts also appear to describe the same opportunity with different
titles and employer representations. Exact grouping does not prove they are
distinct opportunities. This one graduate-targeted query is not representative
of every provider or finance search. Results apply to this saved JSearch pool,
not automatically to the daily Adzuna selection.

## Nebius attempt: incomplete comparison

The authorized direct ranking attempt used the existing four-batch path for
40 candidates, with no request retries. It failed and saved `status=failed`,
`error_type=RuntimeError`; there is no validated model result to score.
The current failure artifact omits the specific safe error category, batch
progress and token usage. The exact number of attempted/completed calls and
billed tokens cannot be recovered from that artifact. No automatic second
attempt was made.

A subsequent non-generating request to Nebius's `/v1/models` returned HTTP 200
and listed the configured Nemotron model. That verifies local metadata access,
not a successful larger generation. It does not distinguish an HTTP rejection
of the ranking request, a transport failure, invalid JSON or output truncation.
The earlier successful four-job GitHub run remains evidence for that smaller
case only. The separate GitHub agent compatibility problem also remains open.

Before another paid trial, preserve safe error codes and batch progress, retain
completed validated assessments on later failure, and record whether generation
ended normally or hit its output limit. Never log credentials, request headers
or raw provider error bodies. This review does not implement those changes.

## Saved local evidence and next action

Under `artifacts/evaluation/`, the `jsearch-2026-11-16-` prefix identifies:

- `reference-labels.json`: frozen labels and their reasons, bound to the snapshot.
- `rules.json`: actual 20-job rules selection.
- `nebius.json`: explicit failed model result, not a substitute ranking.
- `evaluation.csv`: all 40 candidates with reference labels, reasons, location,
  selected/not-selected flags and content groups.
- `evaluation-summary.json`: counts and the recorded validation boundaries.

These data files remain local under the existing ignored artifacts directory.
They are not yet available to GitHub's replay workflow. Human review of the
uncertain labels and a successfully instrumented Nebius trial are still needed
before claiming that an LLM improves on this baseline. No ranking, filtering,
prompt, retry or daily-delivery policy was changed by this evaluation.
