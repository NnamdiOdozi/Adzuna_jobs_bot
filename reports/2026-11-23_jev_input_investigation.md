# What Jev received for the 23 November bulletin

Investigated 23 November 2026. No paid API calls, emails, live filter changes or
history changes. Evidence fetched from GitHub main `59f5d7b`; source daily run
`45124587299` used commit `baa0f08`, including yesterday's revised profile/policy.

## Express answer: the underwriting requirement was not provided to Jev

Adzuna supplied exactly 500 characters for Underwriting Operations Analyst
`5975589417`. The extract ends:

> Working closely with underwriting teams and key stakeholders, you will gain broad exposure to underwriting operations, regulat…

It contains neither the paragraph beginning “If you have experience within the
Lloyd's market” nor the skills/experience requirements in the fuller advert
pasted by the user. Jev received this short extract, not the full webpage.
Its decision was possible_fit, with .81 possible and .14 strong.

The exact candidate pool, original profile, policy and original assessment date
were reconstructed offline. Their computed input hash matches the recorded
receipt: `45a45cf67d9274d9f5a618c0fb060396a67e02625ffae0ddd3e9cf4e04d885ae`.
This verifies the supplied context rather than merely inferring it from titles.

The Jev request's advert fields are title, employer, location, description and
the Python truncation flag. Salary is not sent. The flag indicates whether
Python shortened a supplied description; it does not detect Adzuna's shortening.

## Other confirmed problems

| Job | Saved extract / actual decision | Additional evidence |
|---|---|---|
| French Financial Planning Associate `5975767292` | Title contains French; extract omits language requirements. Selected possible .44 versus insufficient .42. | Employer advert requires native French and English proficiency. |
| Paraplanner `5975767157`, `5975760648` | Identical 500-character descriptions about regulated advice and portfolio recommendations. Neither contains required years. Both selected. | Matching Fisher advert requires 3+ years of financial-services experience. |
| Political Violence & Terrorism Account Handler `5975373329` | Extract describes Lloyd's broking and technical duties; no required years. Selected possible .48. | Matching recruiter advert requires at least four years of London Market account-handling/broker-support experience and relevant risk experience. |

Sources checked online on 23 November, with matching employer and opening text:

- [Fisher Paraplanner](https://www.fishercareers.com/job/london/paraplanner/38252/100661120768).
- [Fisher French Financial Planning Associate](https://www.fishercareers.com/job/london/french-financial-planning-associate/38252/103563536064).
- [Nashrock's account-handler advert](https://uk.linkedin.com/jobs/view/account-handler-political-violence-terrorism-at-nashrock-insurance-recruitment-4487486754).

These matching public adverts clarify the likely full requirements. They were
not part of today's recorded model inputs. Online pages can change; the user's
pasted underwriting advert is the direct full-text evidence for that role.

The recorded candidate profile says spoken English/Vietnamese but treats other
languages as unknown. It does not explicitly say she does not speak French or
that she has no insurance/Lloyd's-market experience. The user has now clarified
both. Even before this clarification, accepting the French title over missing
eligibility was weak behaviour. Salary and description completeness are separate
missing inputs; a prompt edit cannot reconstruct absent requirements.

Both Paraplanner adverts have the same employer, title and description, but
locations London UK versus Fenchurch St Central London. Existing duplicate keys
include location, explaining why both passed. Do not solve this by suppressing
all jobs sharing a title: identical substantive advert text is stronger evidence.

## Requested salary cap and its effect

The user requests a £50,000 annual cap as a suitability screen. A proposed Python
rule would reject a job when its known GBP annual upper salary exceeds £50,000,
including Adzuna estimates. This is deliberately conservative: estimates may be
wrong and ranges overlapping £50,000 would also be excluded. Unknown currencies
or daily/hourly rates must not be compared directly with an annual GBP threshold.
The threshold belongs in config and exclusions should be logged by job ID.

On today's seven selections, four exceed the cap:

- Underwriting Operations Analyst: upper advertised salary £65,000.
- Risk Analyst: Adzuna estimate £51,393.21.
- Political Violence & Terrorism Account Handler: estimate £68,199.45.
- Second Paraplanner: estimate £51,759.56.

That leaves Credit Controller, the first Paraplanner and the French role.
The cap alone therefore does not solve suitability. The French role is
incompatible with the clarified language profile, and the matching full
Paraplanner advert's required experience exceeds the target profile.

## Proposed focused changes, before broader searches

1. Enforce the configurable salary cap in Python, shared across ranking modes;
   preserve raw fetched evidence and log exclusions. Do not rely on Jev arithmetic.
2. Update the candidate profile with known language exclusions and no prior
   insurance/Lloyd's-market experience. Keep genuine trainee insurance jobs
   eligible when they explicitly provide training and do not require that experience.
3. Make Jev distinguish demonstrated junior eligibility from general phrases
   such as “develop your career.” For specialist regulated-advice or insurance
   roles whose requirements are absent, withhold as insufficient information.
   Do not reject a plainly junior Accounts Assistant merely for missing years.
4. Address identical-description/employer reposts with differing local location
   labels, with care around short or generic descriptions and distinct vacancies.
5. Decide separately how to obtain fuller descriptions. Merging JSearch adds
   candidates but does not automatically enrich these existing Adzuna records.
   Compare available provider descriptions before changing the daily credit budget.

These are investigation findings and a proposed implementation, not deployed
fixes. The Saturday Copilot review remains a separate pending task; it cannot
prevent tomorrow's bad selections until the daily process itself is improved.
