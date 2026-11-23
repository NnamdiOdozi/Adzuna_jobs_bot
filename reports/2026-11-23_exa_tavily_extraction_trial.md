# Exa and Tavily URL-extraction trial — 23 November 2026

The user authorised quick live tests using their existing credentials. Secret
files were not inspected. One Exa Contents request was made for three URLs;
after the user clarified the Tavily credential name, one Tavily Extract request
returned HTTP 401 Unauthorized. No search, job-provider, Jev, email or history operations occurred.
The withdrawn direct-fetching feature remains withdrawn.

## Exa: useful retrieval on all three samples

Fresh retrieval was requested with `maxAgeHours: 0`, `text: true`, and a
15-second live-crawl limit. Exa returned three success statuses with source
`crawled`, in 1.79 seconds. Its response reported total cost $0.003. This is a
provider-reported request estimate, not an account invoice reconciliation.

| Page | Returned characters | Useful evidence |
|---|---:|---|
| Adzuna Underwriting Operations Analyst | 3,261 | Recovered the Lloyd's-market and previous underwriting-operations experience requirements missing from the 500-character API extract |
| Jobleads Graduate Business Finance Advisor | 14,845 | Salary £30,000–£35,000, qualifications, and wording that previous experience is not essential; also substantial navigation/related content |
| Fisher Paraplanner employer page | 3,392 | Recovered the required 3+ years of financial-services experience |

The Fisher URL was a separately located employer-page control. The other URLs
were a known Adzuna advert and an actual link from the saved JSearch batch. This
was URL extraction, not automatic discovery of matching employer URLs.

Exa materially outperformed our simple direct fetcher on the Adzuna and Jobleads
examples. Our direct fetcher had already worked on the Fisher employer page.
Three successes do not establish universal retrieval quality, freshness or
access across the daily batch. Jobleads' larger output includes irrelevant text;
more characters alone do not establish a better advert description.

## Tavily: authentication prevented the comparison

The initial program could not start with the supplied `Tavily_API_KEY` name. The
user clarified that the name is `TAVILY_API_KEY`. One request was then made to
the documented Extract endpoint using Bearer authentication. It returned HTTP
401 Unauthorized in 0.18 seconds, with no extracted content or usage information.
This is an authentication failure, not evidence that Tavily cannot retrieve the
pages. The key must be checked privately by the user before another trial. No
secret files, values, prefixes or alternative environment names were inspected.

## What these APIs return

Exa Contents and Tavily Extract return cleaned page text/Markdown and metadata.
That differs from downloading the complete HTML, CSS and browser assets. For
job suitability, the clean advert requirements are what matters; styling would
increase data volume without improving the decision.

References: [Exa Contents](https://exa.ai/docs/reference/get-contents),
[Tavily Extract](https://docs.tavily.com/documentation/api-reference/endpoint/extract).
The documentation's agent-navigation prompts were treated as page content, not
instructions governing this task.

## Saved evidence

[Sanitised request results](2026-11-23_exa_tavily_extraction_results.json) retain
URL-level outcomes, request identifiers, elapsed time and reported usage/cost.
Full extracted text is saved locally under the ignored directory
`artifacts/evaluation/exa-tavily-2026-11-23/`, without request headers or credentials.
Nothing was integrated into the daily bot or pushed by this trial.
