# Provider-boundary brittleness review — 2026-11-26

## What failed

GitHub run 45776261953 used send-again-today correctly and passed the code-check
guard. The search failed at 07:34:09 with ValueError reason=incomplete_vacancy.
The old parser aborted the entire response on the first vacancy missing any
required field. Exa and Jev were not reached. The response was not retained,
so the exact missing field and otherwise valid row count cannot be reconstructed.
The 06:30 failure predates detailed validation logs; its cause remains unknown.

## Changes made

| Demonstrated weakness | Resulting behaviour |
|---|---|
| One malformed vacancy discards the whole search | Skip that row, log its index and fixed missing-field names, retain complete rows; fail if all returned rows are invalid. |
| Invalid optional currency/period types crash salary filtering | Normalize these optional fields to unknown, with a warning. |
| Malformed URL can escape Exa fallback before extraction | Skip that target and retain its original vacancy description. |
| Ten enriched vacancies can still exceed Jev context limits | Split only on max_tokens_exceeded; count every attempt against existing call and time budgets. No partial bulletin if recovery fails. |
| Workflow timeout shorter than combined configured search/ranking limits | Allow twenty minutes for the existing bounded operations and their waits. |

An independent read-only review reproduced the optional salary and malformed
URL failures. All fixes were verified offline. 213/213 tests passed with 91.43%
coverage. No paid API calls, emails or delivery-history changes were made.

## Provider-change hypothesis and remaining limits

No published JSearch change notice confirming a deployment on 26 November was
found in the checked official sources. Its search documentation describes
Google for Jobs and public-site data; changing or incomplete upstream adverts
are another possible cause. This is not proof that the provider did not change.
Reference: https://www.openwebninja.com/api/jsearch

The system cannot guarantee remote availability or that Jev makes correct
suitability decisions. A wholly unusable response, failed model validation,
single-vacancy context overflow or exhausted recovery budget still stops the
bulletin visibly. Failed requests may consume credits. Shared Gmail acceptance
and local history saving are not an atomic transaction; an interruption between
them remains an accepted operational limitation. Enriched evidence persistence
before a failed model call remains tracked in DEFERRED_WORK.md. No new browser,
provider or scheduling architecture was introduced for this repair.
