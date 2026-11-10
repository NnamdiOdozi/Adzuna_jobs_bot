# Understanding checklist — 2026-10-24

These are conversation checkpoints, not requirements imposed on unattended runs.

- [x] User clarified that the data provider is Adzuna, not Azure.
- [x] On 2026-11-10, user approved fixing finance relevance before junior ranking
  after unrelated jobs appeared in the bulletin, then authorized one live check.
- [x] On 2026-11-09, user clarified the intended one-request search budget and
  requested 400 listings with a fallback to 100 if the larger request is rejected.
- [ ] Confirm that the fallback can consume a second request and requested result
  counts are not evidence of the provider's actual cap or remaining credits.
- [x] On 2026-11-09, user requested Monday–Friday emails and prefers avoiding
  Cloudflare edits; the bot now enforces normal delivery days itself.
- [x] On 2026-10-25, user moved the schedule to 02:30 London time Monday to Saturday
  as a four-hour buffer for GitHub delays; recipients remain visible to each other.
- [x] User requested that previously emailed jobs be suppressed on future days.
- [x] On 2026-11-04, user approved targeted junior searches, senior title exclusions
  and junior-first ranking with ordinary Python rules, preserving GitHub history.
- [x] User chose repository Secrets for email addresses after discussing public logs.
- [x] On 2026-10-26, user requested a check against multiple daily sends after
  discussing a delayed schedule following a manual send.
- [x] On 2026-10-26, user requested a configurable test override and a minimal
  Cloudflare timer for 06:30, to deploy through the dashboard.
- [ ] Confirm that force_send bypasses the daily limit for every send while true,
  and Cloudflare dispatch acceptance does not confirm GitHub execution or email.
- [ ] Confirm that daily-send dates and vacancy history serve different purposes,
  and separate local checkouts need current history to share the protection.
- [ ] Confirm that preview searches but neither sends nor changes sent-job history.
- [ ] Confirm that title-word ranking is not an assessment of candidate suitability.
- [ ] Confirm the trade-off between suppressing reposts and hiding separate vacancies
  with identical employer, title and location.
- [ ] Confirm the delivery/history failure gap and local-to-GitHub history migration.
- [ ] Confirm public/private repository choice before publication.
