# Decisions to review

7. 2026-11-13 — Keep shared history and use description evidence for JSearch.
   **Why:** provider categories are incompatible, generic graduate titles can be
   relevant, and separate histories could repeat roles when switching sources.
   **Affects:** JSearch may admit incidental finance mentions; common role keys
   can suppress cross-source adverts but may merge distinct matching vacancies.
   **Assumptions:** the never-emailed-before requirement outweighs separate
   provider files; radius remains a provider filter rather than a guaranteed
   county boundary. **Status:** shared history explicitly approved by the user;
   implemented and explained. Adzuna's stricter
   relevance rule and old history stay unchanged. The user subsequently approved
   automatic Adzuna-to-JSearch fallback for HTTP errors or no unseen matches.

6. 2026-11-13 — Use one combined cron for send, recovery and alert tasks.
   **Why:** one edit to the existing trigger is simpler than adding schedules;
   the script already selects exact London times. **Affects:** nine invocations
   per weekday, six skipping before network access. **Assumptions:** keep the
   documented distinct task times; reconfigure cron if those times move outside
   its UTC hours/minutes. **Status:** implemented locally and documented, pending
   dashboard deployment. Same-Worker hosting and Ntfy-only alerts were user choices.

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
