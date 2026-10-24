# Deferred onboarding and shortlist improvements

Recorded: 2026-10-24. Source: discussion of candidate preferences, ranking and
GitHub run logs. Status: proposals only; nothing in this document is implemented
or authorizes paid model calls, document collection or application submission.

The current bot searches Adzuna, scores titles by counting matching configured
keywords, uses listing date to break ties, removes excluded and previously sent
jobs, and emails up to the configured shortlist size. It does not assess a
candidate's experience or read free-text preferences.

## 1. Candidate preferences — deferred 2026-10-24

Define an editable candidate-preference section in configuration. Agree the
actual values with the friend before implementing filters. Separate hard
requirements, which reject a job, from preferences, which change its rank.

- Preferred roles and seniority; unwanted roles or responsibilities.
- Candidate experience and acceptable job requirements. Distinguish essential
  experience from desirable experience, ranges, and equivalent experience.
- Minimum salary and treatment of missing salary, estimated salary, and ranges
  that overlap the threshold. Compare compatible currencies and pay periods.
- Remote, hybrid or office attendance requirements and acceptable commute.
- Permanent, temporary or contract roles; full-time or part-time work.
- Required qualifications, relevant skills and transferable experience.
- Work authorization and sponsorship needs, where the advert supplies evidence.

Do not invent defaults for these choices. Changing the target candidate should
not require editing source code. Personal candidate information must stay out
of this public repository.

## 2. Evidence and filtering — deferred 2026-10-24

Use structured Adzuna fields and Python comparisons first, including salary and
contract information. Simple, explicit phrases may be parsed without a model.
Adzuna search results contain description snippets, so missing experience,
sponsorship or working-arrangement details mean unknown, not no requirement.

If full adverts are needed, first establish a permitted, practical retrieval
method and handle inaccessible pages explicitly. Preserve the evidence used for
each extracted requirement. Never infer a qualification or experience threshold
merely from a senior-sounding title.

For genuinely ambiguous text, compare a generative extraction model with a
bounded classifier. The extractor can discover requirements; Jev can judge a
specified requirement against supplied evidence using outcomes such as meets,
does_not_meet and insufficient_information. Exact arithmetic remains in Python.
Free-text instructions need an implemented interpretation step: adding a prompt
field alone does not change behaviour.

Initially retain uncertain matches for review. Define missing-evidence handling
explicitly so truncated adverts do not silently exclude suitable jobs. No model
or Jev calls have been authorized or performed for these proposals.

## 3. Ranking and cost controls — deferred 2026-10-24

Replace or supplement the current equal-weight title-word score with agreed
preference weights, candidate-fit findings and recency. Explain why each job
ranked highly and identify unmet or unknown requirements separately. Apply the
new criteria before choosing the final shortlist; scoring only the first 20
would miss potentially better candidates elsewhere in the fetched results.

Remove known and duplicate adverts and apply cheap exact filters before paid
analysis. Consider caching analysis for unchanged adverts. Estimate request
volume and spending, agree a limit before any paid trial, and decide whether
batch processing fits the morning delivery deadline. Keep the current one-page,
100-results-per-query search limit unless explicitly changed.

## 4. Review and validation — deferred 2026-10-24

Create a small hand-checked set of adverts before trusting automatic rejection.
Include missing salaries, estimated salaries, experience that is preferred rather
than required, alternative qualifications and incomplete descriptions. Compare
the new approach with the existing title rules. Measure suitable jobs wrongly
excluded, unsuitable jobs retained, unknown outcomes and cost per advert.

Valid structured output proves format, not correct interpretation. Display the
supporting wording so a person can check important judgments. If model confidence
labels are used, define their meanings and check their usefulness against the
reviewed examples rather than treating them as calibrated probabilities.

## 5. Inspectable shortlists and send records — deferred 2026-10-24

Log selected job IDs, titles and employers in send mode as well as summary counts.
Distinguish selection, Gmail acceptance and successful history persistence.
Consider a saved shortlist or downloadable GitHub artifact so the exact selection
can be inspected later without rerunning the search. Decide retention and access
before adding artifacts. Do not log credentials or private applicant information.

Consider a separate email-submission record with run time and selected job IDs.
The current seen.json is duplicate-suppression history, not an email audit trail
or proof of inbox delivery. Saving a shortlist must not mark its jobs as sent.

## Related future application feature

Applying on the friend's behalf remains separately deferred in DEFERRED_WORK.md.
That feature requires consent, private CV/contact storage, agreed submission
authority and duplicate-application controls. Shortlist relevance checks do not
authorize submitting an application.
