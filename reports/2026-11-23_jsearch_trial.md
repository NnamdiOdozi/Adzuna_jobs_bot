# JSearch-only live preview — 23 November 2026

The user authorised one eight-page JSearch search and Jev assessment. Adzuna is
disabled in local config: provider is JSearch and fallback is empty. No email
was sent. Both history files were checked before/after and remained unchanged.
Today's GitHub history was brought into the checkout before searching.

## Result

- One JSearch HTTP request, eight pages requested; 42 vacancies returned.
- Descriptions: 416–8,925 characters, median 2,144. These are available provider
  descriptions, not independently verified complete adverts.
- Jev assessed 41 jobs in three requests after duplicate/history preparation.
- Categories: 20 strong, 5 possible, 12 unlikely, 4 insufficient information.
- The configured maximum of 20 selected 20 of the 25 accepted jobs.
- Jev reported 41,368 input and 2,173 output tokens. Account charges and remaining
  JSearch credits were not inspected; eight pages consume page-based credits.

## Quality observations

The result is more graduate-focused than this morning's Adzuna bulletin. Examples
include Graduate KYC Analyst, Finance Graduate Scheme in Guildford, Graduate Risk,
Project-style finance rotations, and Graduate Finance Trainee in insurance.
Jev rejected the applicant-paid trainee-accountant course adverts and a recruitment
consultant role. This is encouraging evidence, not measured classification accuracy.

There are important remaining limitations:

1. All 42 records lacked structured numeric salary figures. The new £50,000
   annual GBP cap therefore excluded none. Some descriptions contain salary
   information, but the deterministic screen does not extract pay from prose.
   The first selected Graduate Finance Broker description advertises £70,000–£85,000
   earnings potential after its programme. That is commission-related future
   earnings, not a verified starting base salary; it must not be silently
   interpreted as either below or above a base-salary cap.
2. Probable reposts remain: three Vecta graduate broker listings, three NEP finance
   programme listings and related SEFE listings. Locations, titles or employer
   labels differ. These need careful duplicate matching rather than blindly
   removing every role with a similar title.
3. Several shortlisted roles are sales or brokerage careers. The candidate's
   preference between those and core accounting remains unresolved.
4. Some descriptions are still short, and graduation dates, degree grades and
   other eligibility must be checked. The radius does not establish that every
   returned location falls within 50 km; Milton Keynes appears in the selection.

## Changes applied locally before this trial

The daily coordinator now applies a configured `max_salary_gbp = 50000` before
rules/Jev/Qwen selection, retaining raw fetched evidence and logging exclusions.
It rejects known annual GBP salary upper figures above the cap, including
estimates and ranges crossing the cap. Unknown pay, foreign currencies and
nonannual rates remain eligible rather than being guessed.

The candidate profile explicitly records English/Vietnamese only, no French or
other languages, and no prior insurance/underwriting/Lloyd's experience. The
shared Jev/Qwen policy was shortened into category rules: required other languages
and observed incompatible experience exclude; uncertain specialist eligibility
is withheld; clear junior accounting, temporary work and genuine graduate training
remain eligible. These are model instructions, not deterministic guarantees.

Offline checks passed: 191/191 tests and 91.25% combined line/branch coverage.
The mocked tests prove salary-screen behaviour and wiring, not semantic quality.
No website retrieval or additional provider requests were introduced.

## Saved evidence

[Trial folder](2026-11-23_jsearch_trial/) contains the normalized provider snapshot,
all candidate descriptions, model assessments, numbered shortlist, prepared email
body, machine-readable run report and readable summary. The saved snapshot
retains the prior history needed to replay this trial without another search.
Reassessing with Jev would still incur model charges.

These changes and evidence have not been committed or pushed. GitHub's daily run
continues with its existing configuration until publication.
