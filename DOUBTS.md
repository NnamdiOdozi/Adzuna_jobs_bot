# Decisions to review

3. 2026-11-09 — Apply the weekday limit to all normal sends, including manual
   force_send runs; retain weekend preview and sender-only test.
   **Why:** the same command receives both Cloudflare and manual requests;
   keeping one delivery rule avoids sending the friend a weekend test by mistake.
   **Affects:** manual weekend sends now skip; Cloudflare need not be edited.
   **Assumptions:** the requested weekday restriction applies to normal recipient
   delivery. Alternative considered: restrict only automated dispatches, requiring
   separate trigger context in the bot. **Status:** implemented and disclosed;
   no new option to override permitted weekdays was requested.

1. 2026-10-24 — Retain public GitHub visibility until explicitly changed.
   Why: approval covered initializing and connecting the local repository, and
   did not unambiguously select public or private visibility.
   Affects: eventual publication of source, sender address and sent-job keys.
2. 2026-10-24 — Exclude recruiter and recruitment-consultant title matches.
   Why: a live preview surfaced a recruiter role among finance vacancies.
   Affects: shortlist relevance; exclusion terms remain editable in config.toml.
