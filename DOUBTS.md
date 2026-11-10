# Decisions to review

5. 2026-11-10 — Require both the finance category and explicit finance-title words.
   **Why:** ranking zero-finance titles admitted 18 unrelated bulletin entries.
   **Affects:** missing/wrong categories and generic Junior Analyst titles are
   rejected; Accounts/Payroll/Bookkeeping/Auditor/Actuarial terms are included.
   **Assumptions:** Adzuna category tags are useful but imperfect evidence.
   Alternative considered: permit either category or title evidence; this could
   retain unrelated titles misclassified in finance. **Status:** strict rule
   implemented and disclosed within the approved relevance fix. See DESIGN_CHOICES.md.

4. 2026-11-09 — Treat the first HTTP 400 as grounds for the requested size retry.
   **Why:** Adzuna documents 400 for invalid parameters but publishes no page-size
   maximum or dedicated size-error code. A single retry can recover from an
   oversized request. **Affects:** at most two API attempts per search.
   **Assumptions:** a size rejection uses HTTP 400. An unrelated invalid parameter
   could cause one unsuccessful extra request. Alternative considered: parse
   error-body text, but no stable documented size-error format was found.
   **Status:** implemented with a bounded retry; actual page-size support remains
   unverified. See DESIGN_CHOICES.md, single combined search.

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
