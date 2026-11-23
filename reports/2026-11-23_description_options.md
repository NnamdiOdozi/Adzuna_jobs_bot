# Investigation: better vacancy descriptions

23 November 2026. No paid API/model calls, emails, history writes or live changes.

## Recommendation

JSearch is the strongest immediate option for richer descriptions. Selective
retrieval from employer websites can supplement it, but arbitrary Adzuna links
are not currently dependable. Specialist jobs should be withheld when essential
eligibility cannot be established from an extract.

## Saved JSearch evidence

The saved eight-page batch from 16 November contains 42 jobs. Descriptions range
from 461 to 9,663 characters, with a median of 2,144. Thirty-one exceed 500
characters. There are 31 distinct description texts, of which 20 exceed 500.
Twelve rows repeat a training-course advert, inflating the raw long-text count.
None exceeds Python's current 12,000-character description limit.

These longer descriptions contain useful evidence beyond the first 500 characters:

- LSEG Business Analyst Graduate Programme: eligibility begins around character
  2,248, covering study disciplines and graduation timing.
- Checkout.com Finance Analytics Graduate Programme: a last-12-month graduation
  condition appears around character 2,919.
- The trainee-accountant advert discloses applicant-paid course fees around
  character 2,134. A graduate-looking title alone would conceal that.

Longer does not guarantee complete. Eleven descriptions are still 500 characters
or fewer, and none of these jobs has been matched to today's Adzuna vacancies.
We have not checked all 42 against their original webpages.

Our existing adapter already retains the supplied `job_description`. The provider
also documents `job_highlights` and `/job-details`; highlights are currently
ignored by our adapter. Preserving supplied qualification/requirements highlights
could help, but their actual presence and quality need checking. Job details
requires a JSearch ID, not an Adzuna ID, and extra requests may consume credits.
No detail requests were made.

Source: [OpenWeb Ninja's JSearch reference](https://github.com/OpenWeb-Ninja/openwebninja-skills/blob/main/openwebninja/apis/jsearch/README.md).
Saved local source: `artifacts/evaluation/jsearch-2026-11-16-eight-pages.json`.
That local dataset is not included in a fresh GitHub checkout.

## Direct advert retrieval

Ordinary Python HTTPS requests from this laptop produced:

| Page | Result |
|---|---|
| Original saved Adzuna Underwriting Analyst and Paraplanner links | Both HTTP 403, access denied |
| Corresponding Adzuna details pages | Both HTTP 403 |
| Matching Fisher Paraplanner employer page | HTTP 200; structured description 3,435 characters |
| Matching Fisher French Planning employer page | HTTP 200; structured description 3,152 characters |

Fisher embeds machine-readable JobPosting data in its pages. Simple Python
extraction recovered the Paraplanner's required three years of financial-services
experience and the French role's native French requirement. No browser automation,
login or additional model was needed for those two examples.

Fisher's robots file disallows its search-jobs path; the tested individual vacancy
paths are not covered by that listed exclusion. This does not establish blanket
permission, compliance with all terms, or future access. Adzuna's robots file
also returned 403. No denial was bypassed. GitHub runner access is untested.

Importantly, today's Adzuna records contain blocked Adzuna redirect URLs, not the
working employer URLs. Those employer pages were found during the investigation.
Automatically finding and verifying the matching original page remains additional
work. A successful employer-page fetch does not solve that discovery problem.

If implemented, retrieve only supported public sources, match employer/title/
location, preserve original text plus retrieval source/time/status, bound requests
and timeouts, and cache retrieved text. Restrict destination addresses and
redirects. Failed retrieval must remain missing evidence, never a successful
eligibility check. Do not bypass blocked pages or build an unrestricted scraper.

Sources: [Fisher Paraplanner](https://www.fishercareers.com/job/london/paraplanner/38252/100661120768),
[Fisher French Planning](https://www.fishercareers.com/job/london/french-financial-planning-associate/38252/103563536064).

## Withholding specialist roles without losing assistants

| Available evidence | Intended decision |
|---|---|
| Accounts Assistant, routine invoice duties, no visible conflict | Plausible junior role even if years are unstated |
| Graduate insurance operations scheme explicitly training entrants without prior experience | Eligible; insurance itself is not excluded |
| Lloyd's underwriting or regulated paraplanning work, but requirements missing from extract | Insufficient information; withhold |
| Full advert requires prior Lloyd's experience or mandatory experience over two years | Unsuitable for this known profile |
| Required French, which the candidate does not speak | Unsuitable |
| Another language merely desirable | Do not reject for that preference alone |

“Supportive team” and “develop your career” do not establish trainee eligibility.
Specialist duties also do not prove mandatory experience: missing evidence should
mean insufficient information, not invented seniority. Explain in the profile
that she has no prior insurance/Lloyd's experience, preserving trainee exceptions.

Use shorter ordered category rules and concrete examples rather than appending
more prose. The prior replay showed that prompt wording is fallible. A focused
trial with saved short/full-description pairs is needed before claiming these
instructions work. No new Jev trial was performed here.

## Suggested implementation order

First implement the separately requested salary cap and language restrictions,
clarify the profile and specialist-evidence policy, then test on saved examples.
Next consider JSearch as primary using the existing provider switch and normal
page budget. Compare actual suitability and eligibility evidence, not just counts.
Changing provider alone does not implement those screening controls.

Consider selected employer-page retrieval later where direct URLs and permitted
access are available. Merging JSearch does not automatically enrich each Adzuna
record. Do not silently increase daily searches or credits. All these remain
proposals; no live behaviour changed during the investigation.
