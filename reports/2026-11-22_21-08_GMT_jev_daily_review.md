# Review of daily Jev shortlists, 17–20 November 2026

Reviewed 2026-11-22, 21:08 GMT. Recommendations only: no live settings, prompts,
delivery history or workflows changed. No Adzuna, JSearch, Jev or Qwen calls and
no emails were sent during this review.

## Conclusion

Keep Jev in the daily process. It is excluding obvious senior and specialist
vacancies that the rules would still admit. The main weakness is inconsistent
treatment of missing eligibility evidence, made worse by very short provider
descriptions. Improve that evidence and the category definitions before imposing
a blanket probability cutoff. The email also needs to distinguish advertised
salaries from Adzuna estimates.

This is a review of visible evidence, not a measured accuracy score. We do not
have candidate-confirmed labels or full adverts for these jobs. A plausible job
is worth considering, not proof that Vanessa meets every requirement.

## Evidence and coverage

I fetched GitHub main at `954e72b`, inspected all four archived daily batches,
all 199 recorded assessments, the three saved email bodies, and the five daily
Actions job logs from 16–20 November. Local uncommitted README work was preserved.
The first actual Jev morning was 17 November. The 16 November run used rules;
its test-step simulated failures must not be confused with live search failures.

| Date | GitHub run | Fetched | Assessed | Strong / possible / unlikely / insufficient | Emailed |
|---|---|---:|---:|---|---:|
| 17 Nov | [44031751284](https://github.com/NnamdiOdozi/Adzuna_jobs_bot/actions/runs/44031751284) | 50 | 50 | 1 / 7 / 40 / 2 | 8 |
| 18 Nov | [44251874979](https://github.com/NnamdiOdozi/Adzuna_jobs_bot/actions/runs/44251874979) | 50 | 50 | 1 / 8 / 37 / 4 | 9 |
| 19 Nov | [44472700056](https://github.com/NnamdiOdozi/Adzuna_jobs_bot/actions/runs/44472700056) | 50 | 49 | 0 / 8 / 37 / 4 | 8 |
| 20 Nov | [44688314046](https://github.com/NnamdiOdozi/Adzuna_jobs_bot/actions/runs/44688314046) | 50 | 50 | 2 / 8 / 38 / 2 | 10 |
| Total | Four Jev mornings | 200 | 199 | 4 / 31 / 152 / 12 | 35 |

The missing assessment on 19 November is accounted for: Senior Financial Analyst,
Prime Video Accounting (`5971029618`) matched a role key already in sent history.
There are 199 distinct assessed IDs and no repeated assessed ID across these days.
This does not prove that differently named reposts were absent.

Every morning used Adzuna only: one request asking for 400, returning 50. There
were no JSearch top-ups, retries or live API failures in these four logs. Each
day made three Jev requests, in batches of 20/20/10 or 20/20/9. Total reported
usage was 104,332 input and 10,500 output tokens across 12 requests. These are
usage counts, not a verified invoice.

All four runs started around 06:30:44–45 GMT and logged Gmail acceptance for two
recipients followed by history saving. GitHub success and Gmail acceptance do
not prove inbox arrival. The 18–20 November reports also record
`accepted_history_saved`; 17 November predates saved email bodies.

All archived file hashes matched their current manifests. The two historically
enriched archives explicitly record that enrichment; this check verifies their
current recorded contents, not that they are untouched original downloads.
The Jev policy file was identical at all four source commits, with SHA-256
`473cd96e8e11064d3801db71ad0620c1f51b2095726e7a81706cfb64cc07bf52`.

The [assessment CSV](2026-11-22_21-08_GMT_jev_daily_assessments.csv) lists every
assessment with date, fetched index, ID, description, category and probabilities.
The frozen [GitHub archive](https://github.com/NnamdiOdozi/Adzuna_jobs_bot/tree/954e72b/archive)
contains the source snapshots, receipts and available emails. IDs below locate
the corresponding CSV rows and archive records.

## What Jev is doing well

Its exclusions generally reflect the candidate's level rather than merely
matching a finance word. Examples include Associate Director/private credit,
senior reporting and actuarial managers, and the Fund Finance Partner legal role
(`5969660806`). Core junior selections include Accounts Assistant in Uxbridge
(`5968244244`), Project Finance & Commercial Assistant (`5969571338`), Junior
Assistant–Loan Administration (`5969527344`) and Assistant Management Accountant
(`5972341728`). Relevant complaints work remains eligible, as requested.

I also ran the existing Python rules offline on each identical snapshot, using
its saved search settings and prior history. This required no external calls.

| Date | Rules would select | Jev selected | Shared selections |
|---|---:|---:|---:|
| 17 Nov | 11 | 8 | 5 |
| 18 Nov | 8 | 9 | 2 |
| 19 Nov | 7 | 8 | 4 |
| 20 Nov | 11 | 10 | 2 |

Rules would admit the seasoned Service Accountant, a qualified Management
Accountant and Finance Expert on 17 November, the Fund Finance Partner on
18 November, and an SVP Equity Derivatives role on 20 November. Jev withheld
these. The comparison shows concrete benefits, not an overall accuracy ranking.
Do not restore all title rules in front of Jev: that would also remove accounting
and operations jobs which Jev correctly recognises from their descriptions.

## The largest limitation: Jev sees extracts, not full adverts

All 200 provider descriptions were at most 500 characters. Their daily median
was exactly 500; 198 ended in an ellipsis. The saved vacancy field contains the
entire text supplied by Adzuna, not the entire vacancy webpage.

Several extracts consist almost entirely of employer introductions or application
instructions. The three Close Brothers analyst/assurance selections on 18 November
(`5969735922`, `5969735912`, `5969528293`) mainly show generic recruitment wording.
They do not establish the actual experience requirements. Jev still accepted them.

The receipt's empty `truncation` list is not evidence of complete adverts. It
only means Python did not cut the supplied text at its 12,000-character limit.
Recommendation: separately record provider-extract/unknown completeness and
whether duties or eligibility evidence are actually present. Do not promise full
advert retrieval without first checking provider capabilities and access rules.
Do not automatically spend JSearch credits on every extract: that is a separate
budget decision, and it is not guaranteed to recover the same vacancies.

## Selections that deserve caution

Python accepts either `strong_fit` or `possible_fit`, without a probability
threshold. It orders accepted jobs by the sum of those two probabilities. Thus
the winning category can be possible while most total probability lies elsewhere.

| Date / ID | Job | Why reconsider |
|---|---|---|
| 17 Nov / `5968403290` | Night Auditor | Hotel night-crew work with account balancing. Possible .36, strong .34. Decide whether predominantly hospitality work is wanted; the accounting words alone do not settle it. |
| 18 Nov / `5969694597` | Senior Administrator | Property contract administration/invoicing. Combined fit .55; neither junior level nor predominantly finance duties is established. |
| 19 Nov / `5971094915` | Climate Adaptation & Nature Finance Analyst | Possible .35 versus insufficient .33; combined fit only .40. Junior eligibility is absent from the extract. |
| 19 Nov / `5971094913` | Green Finance & Climate Policy Associate | Combined fit .45; finance-adjacent policy duties do not establish junior suitability. |
| 20 Nov / `5972365618` | Sanctions Operations Consultant | Possible .47 ties insufficient .47 in stored probabilities. Extract mainly contains application acknowledgements. Selection is fragile, although unrounded probabilities are unavailable. |
| 20 Nov / `5972215685` | Spanish Client Service Associate | Language-specific title accepted although Spanish ability is unknown. The Mandarin accounting role below was withheld. Treat language eligibility consistently. |

These are evidence gaps or preference questions, not six proved bad vacancies.
Associate titles, investment work, insurance operations and temporary contracts
are not automatic exclusions. Nor should salary alone be used to infer seniority.

## Possible missed positives and inconsistent boundaries

* `5972147127`, Temporary Customer Services Executive / Accounts Assistant,
  Richmond: rejected despite no visible senior requirement. Mixed customer-service
  duties may justify caution, but the actual proportion of accounting work is
  unknown. This is a candidate for review, not a confirmed false negative.
* `5972147192`, Interim Part Qualified Finance Officer: invoice processing and
  routine administration are relevant. Part-qualified status is unknown for
  Vanessa. Missing qualification information should not be confused with a known
  mismatch; likewise the title alone does not prove eligibility.
* `5972142946`, Temporary Credit Controller: rejected while another collections
  Credit Controller (`5972280669`) was accepted. The former requests experience
  without stating years. This difference may be reasonable, but merits a labelled
  comparison rather than a blanket controller exclusion.
* `5972306278`, Chinese Speaking Accounting Officer: correctly held as
  insufficient information because business-fluent Mandarin is required and the
  candidate's languages are unknown. Apply the same reasoning to Spanish roles.
* Legal Cashier is accounting in a law firm, not a lawyer. The 19 November
  selection (`5971040066`) is therefore reasonable. Two 17 November Legal Cashier
  extracts mostly contained employer publicity and were rejected; these need
  more evidence, not a legal-occupation assumption. Another explicitly sought
  solid legal-cashiering experience, so different outcomes can be justified.

## Recommended prompt changes, in priority order

These are proposed additions to the shared policy, not changes already deployed.

1. **Separate absent evidence from an observed conflict.** Suggested wording:
   “Boilerplate, inclusion statements and application instructions are not evidence
   of junior eligibility. Use insufficient_information when these prevent assessing
   duties or level. Use unlikely_fit for an observed incompatible requirement or
   clear senior/non-finance duties, not merely because information is missing.”
2. **Give possible_fit a positive basis without making recall collapse.**
   “Require visible junior/support-level accounting or relevant financial-services
   work, or a clearly junior title. Missing salary or an unstated experience count
   alone does not disqualify a plausible Accounts Assistant. A generic Analyst,
   Associate or Officer title alone does not establish junior eligibility.”
3. **Make essential eligibility consistent.** “If an explicitly mandatory language,
   professional qualification or student status is unknown for the candidate,
   classify as insufficient_information. Employer-funded qualification study is
   different from requiring an existing qualification. Do not infer that unknown
   means met or failed.” Confirm Vanessa's relevant qualifications/languages
   privately rather than inventing them.
4. **Distinguish occupation from employer and title ambiguity.** Preserve legal
   cashier/accounting jobs in law firms and junior collections work. Exclude actual
   legal practice and senior financial control. Preserve graduate investment
   training and complaints operations. Ask the user about hospitality/night audit
   and finance-sales roles before silently widening or narrowing them.

## Why not just raise the probability threshold?

An offline calculation on the existing outputs gives:

| Required combined strong + possible probability | Remaining selections out of 35 |
|---|---:|
| Current category rule, no minimum | 35 |
| At least .50, in addition to current rule | 32 |
| At least .60 | 29 |
| At least .70 | 21 |
| At least .80 | 16 |

The .50 rule would remove the two climate roles and Interim Revenue Assurance
Analyst (`5972131711`). It would retain the boilerplate-only Sanctions Consultant
at .51. A .70 rule also removes Accounts Payable Assistant, Trainee Wealth Adviser
and Legal Cashier. A winning-margin rule is problematic too: the good Accounts
Assistant with 1–3 years' experience (`5968162255`) has a margin of only .02,
because strong and possible share nearly all probability between them.

Recommendation: flag weak evidence and borderline fit for review first; evaluate
any hard threshold on human-labelled cases before deployment. These probabilities
have not been calibrated against Vanessa's choices. Do not call .70 a verified
70% chance of suitability, or interpret agreement between two model outputs as
proof of correctness.

## Other process improvements

**Mark estimated salaries.** In the raw snapshots, 24 of the 35 selected roles
have Adzuna's `salary_is_predicted = 1`: 5/8, 7/9, 6/8 and 6/10 by day. The model
preparation drops that flag, and the shared email builder prints the figures as
ordinary salaries. The saved 18–20 November emails therefore present some
estimates with misleading precision. Preserve the flag through selection and
label these “Adzuna estimate”; present sensible rounding and retain missing-salary
information. This is a presentation fix, independent of Jev's ranking.

**Retain sufficient replay context.** Snapshots save vacancies, search settings
and seen history, but not the full candidate profile and Jev policy. The receipt
has an input hash, not the policy text. The source commit allowed reconstruction
here. Save a policy/profile version or safe copy with future assessments so a
later replay can explicitly choose original versus revised instructions. Never
include credentials or email addresses in that context.

**Monitor quality alongside delivery.** Keep the existing completion checks.
Add lightweight summary counts for strong/possible/insufficient, weak-evidence
selections and estimated salaries. Do not treat a small shortlist as a failure:
the current 8–10 jobs are preferable to padding to 20. All four mornings returned
50 provider jobs, so the configured 25-job top-up was correctly inactive. Whether
to buy wider coverage is separate from judging these 50 well.

## Proportionate next step

Agree the disputed role preferences and label a compact set of the concrete
examples above, including good assistants, mixed-duty jobs, unknown languages,
boilerplate-only analysts and clear senior/legal exclusions. Then amend only the
policy and replay the same saved candidates once, comparing good matches retained,
unsuitable matches admitted and plausible jobs lost. Such a replay needs model
credits but no new job-search request. Obtain approval before those paid calls.

The offline arithmetic here demonstrates current behaviour and trade-offs. It
does not demonstrate that a proposed prompt improves Jev, establish recall over
vacancies the APIs never returned, or prove full-advert eligibility. No new test
suite, scheduling change or replacement architecture is needed for this review.
