# Saved real-vacancy evaluation batch — 2026-11-16

The user authorized one JSearch search of eight pages, budgeting approximately
eight credits. One request was made through the existing provider client, with
no retry, Adzuna request, model call, email send or delivery-history write.
Actual account billing and remaining credits were not inspected.

Parameters: query `graduate finance jobs in London, UK`, country `gb`, language
`en`, `num_pages=8`, `date_posted=week`, `radius=50` kilometres. The normal bot
configuration was not changed.

The response contained 42 jobs with 42 distinct provider IDs. All have nonempty
descriptions. Existing seen-job and duplicate checks leave 40 model candidates.
An offline run of the current JSearch rules selected a shortlist of 20; this is
not a count of human-verified suitable roles. Eight pages do not guarantee 80
results. The normalized snapshot is about 173 KB and retains the descriptions
returned by the provider before relevance/experience filtering.

Local files, deliberately under the existing ignored `artifacts/` directory:

- `artifacts/evaluation/jsearch-2026-11-16-eight-pages.json`: reusable snapshot
  with its search configuration, history context and integrity hash.
- `artifacts/evaluation/jsearch-2026-11-16-eight-pages.csv`: all 42 jobs, including
  descriptions and blank expected-suitability/review-reason columns for labelling.
- `artifacts/evaluation/jsearch-2026-11-16-eight-pages-summary.json`: request
  settings, acquisition timestamp, snapshot hash and counts.

These data files have not been published to GitHub or wired into its manual
comparison workflow. Existing synthetic examples remain unchanged. Replaying
the snapshot avoids further JSearch requests; model ranking would still consume
Nebius credits and has not been run on this batch.

Returned locations include London, Greater London, Hemel Hempstead, Guildford,
Luton and Milton Keynes. The response therefore does not prove a strict 50 km
cutoff. Location suitability needs review alongside experience and occupation.

Next: label suitable, unsuitable and uncertain vacancies before measuring
ranking quality. Keep the full pre-filter pool so false exclusions can be found.
This query targets graduate roles and is not representative of every finance
search; retain the small synthetic edge cases alongside real examples.
