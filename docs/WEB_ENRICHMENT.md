# Webpage-fetching experiment — withdrawn

23 November 2026. We built and tested concurrent retrieval of linked vacancy
pages to supplement short provider descriptions. The user chose to withdraw it
because it produced no material description improvement on the saved JSearch
batch. Daily runs use descriptions supplied by JSearch; they do not fetch linked
webpages. JSearch remains primary, Adzuna remains disabled, and the salary
screening and extracted-salary display are retained.

## What we tried

The experiment fetched public HTTPS pages concurrently, observed robots rules,
checked advert identity and extracted structured JobPosting descriptions. It
preserved original API text and recorded failures. Both a restricted-host version
and an unrestricted-public-host version were tested with bounded requests.

| Test | Time | Descriptions improved |
|---|---:|---:|
| Two manually supplied Fisher employer pages | About 0.7 seconds | 2 |
| Existing host list, saved 42-job JSearch batch | About 1.2 seconds | 0 |
| Temporarily expanded source domains | About 5.7 seconds | 0 |
| Final unrestricted-host config, saved batch | About 9 seconds | 0 |

The final batch test considered up to twenty adverts: ten returned HTTP 403,
two timed out, two did not match the expected advert identity, two lacked usable
structured advert data, three offered no longer description, and one failed
robots retrieval. Twenty-one jobs were beyond the attempt cap and one was
seen/duplicate.

Direct Fisher employer pages did expose missing language/experience requirements,
but those working URLs were found separately. The real batch mostly supplied
aggregator links. The experiment did not automatically discover replacement
employer URLs, bypass website blocks or demonstrate access from GitHub runners.
Removing the local sandbox and expanding hosts did not improve this batch.

## Decision and retained evidence

The fetching configuration and runtime integration were reverted to the published
provider-only process. The fetching implementation and its dedicated tests were removed as part
of that rollback. This was not deployed to GitHub.

The three check reports remain as evidence:

- [Initial checks](../reports/2026-11-23_web_enrichment_checks.json).
- [Expanded-host check](../reports/2026-11-23_enrichment_expanded_hosts.json).
- [Final current-config check](../reports/2026-11-23_enrichment_current_config.json).

No paid provider/model requests, emails or sent-history writes were made for
these webpage-fetching tests. The measurements concern this saved batch, not a
claim that webpage enrichment can never help another source or set of adverts.

## Subsequent managed-extraction test

After withdrawing direct fetching, the user authorised a small Exa/Tavily trial.
Exa retrieved all three tested pages in 1.79 seconds and recovered missing
experience requirements, reporting $0.003 request cost. Tavily returned HTTP 401,
so its extraction quality remains untested. This changes the conclusion for
managed extraction services, not the decision to withdraw our direct fetcher.
See [the separate provider trial](../reports/2026-11-23_exa_tavily_extraction_trial.md).
No managed extraction service has been integrated into daily delivery.

## Managed extraction now integrated

2026-11-23: Exa text retrieval replaces the abandoned direct scraper in the
daily workflow. `jobs_bot/exa_contents.py` makes one bounded contents request
before ranking, skips sent/duplicate vacancies and known salary exclusions,
and retains original extracts and retrieval status in the run evidence.
This build was checked offline; the earlier three-URL live trial is the live
evidence, not a test of every future advert. Missing credentials or service
failures visibly fall back to provider descriptions. No automatic retries are
used here because extraction is optional and retrying can incur extra cost.
