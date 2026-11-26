# Jev local recovery replay — 2026-11-26

Replayed the 26 saved vacancies from GitHub run 45774259929 using the current
production Jev ranker and ten-vacancy batches. No JSearch or Exa requests,
email delivery or delivery-history changes were made. Previously sent roles
and duplicates were filtered using the original snapshot history.

The archive contains original JSearch descriptions, not the Exa-enriched text
from the failed ranking. This trial therefore cannot establish the cause of
the earlier HTTP 400 or guarantee success on enriched descriptions.

All three Jev requests succeeded: 10, 10 and 4 vacancies, comprising 20, 20
and 8 questions. There were 24 candidates after duplicate/history filtering,
and 13 were selected. Reported usage was 44,755 input and 2,442 output tokens
across the three calls. Request bodies were 120,895, 72,107 and 23,277 bytes;
bytes are not token counts. Successful structural validation does not prove
that all suitability decisions were correct. No manual quality assessment was
performed in this connectivity and batching test.

Detailed local results: `artifacts/evaluation/jev-recovery-2026-11-26/`
contains `summary.json`, `receipt.json` and `shortlist.json`.

Remaining: preserve enriched candidates before ranking can fail, and capture
safe provider rejection codes and request-size diagnostics. These are needed
to diagnose the earlier failure without another search or extraction.
