# Choose Adzuna or JSearch

The bot normally tries Adzuna first and can use JSearch as its automatic backup.
Cloudflare still requests the same GitHub workflow; the source that succeeds supplies vacancies before the existing
ranking, preview/email and sent-history steps. No LLM is involved.

## Configuration

In `config.toml`, the normal settings under `[search]` are:

```toml
provider = "adzuna"
fallback_provider = "jsearch" # An empty string disables the automatic backup.
```

The backup runs if Adzuna raises an HTTP error or produces no unseen matching
jobs, including an empty response or listings all rejected/previously emailed.
Adzuna first completes its existing smaller-page retry for HTTP 400. If at
least one unseen match survives, JSearch is not contacted; it does not top up
a short Adzuna email. Set provider to jsearch for direct JSearch use instead.
JSearch is tried at most once per run, never cycling back to Adzuna. Add its
GitHub Secret before publishing the enabled backup. A missing key, malformed
primary data or a non-HTTP network error still fails visibly; those failures
are not silently reinterpreted as an empty search.
Shared title preferences, exclusions and shortlist size remain in `[search]`.
That section's Adzuna endpoint, category, query terms, days and page sizes are
used only by Adzuna. The separate `[jsearch]` section supplies these parameters:

```json
{
  "query": "graduate finance jobs in London, UK",
  "country": "gb",
  "language": "en",
  "num_pages": 8,
  "date_posted": "week",
  "radius": 50
}
```

The radius is kilometres. London supplies the search location and 50 km asks for
nearby places. This covers parts of the surrounding counties, not every Home
County, and is not a postcode-distance check implemented by this bot. The API
accepts a free-form query; its documentation does not establish LLM-based
interpretation or guarantee that every returned location matches the radius.
The initial one-page preview had no radius parameter and cannot verify this
new radius. Review contradictory locations in the full advert.

One request asks for the entire configured batch. Eight pages mean up to 80
results, not a guaranteed 80. The response cursor is not followed. Each page
consumes one credit even when pages are bundled in one HTTP request. At the
advertised 200-credit monthly free limit, 23 weekday searches can consume 184
credits. Previews, sender-only tests, manual reruns and recovery searches share
that allowance. No remaining-credit meter is implemented; check your account.

The JSearch timeout is 60 seconds. There are no automatic JSearch request
retries, smaller-page retries or fallback back to Adzuna: these could repeat a
paid batch. Adzuna's HTTP error or empty-shortlist fallback uses the configured
JSearch batch. Logs identify the source transition and HTTP status or reason
without response bodies or credentials. If JSearch fails, normal send emails
a distinct 'JSearch API failed' notice instead of claiming no matching jobs.
Once Gmail accepts that notice, today's email date is recorded but seen-job
history is untouched. The workflow still fails visibly and its history-save
step preserves the accepted notice. Later automatic or manual sends that day
skip unless force_send is deliberately enabled. If Gmail also fails, no date
is recorded and normal recovery/alerting remains possible. Cloudflare recovery can request another workflow
when no send is recorded, which can consume another eight-page batch. Adzuna's
existing single smaller-page fallback remains unchanged.

## Activate locally and on GitHub

1. Keep the private key in user-managed configuration as `JSEARCH_API_KEY`.
   The outgoing HTTP header is `X-API-Key`, but that is not the shell variable
   name. The agent must not inspect or edit your secret files.
2. For GitHub, open **this repository → Settings → Secrets and variables →
   Actions → Secrets → New repository secret**. Set the name to
   **JSEARCH_API_KEY**, enter the private value and click **Add secret**.
   The workflow already maps that Secret to the program's environment.
   Do not use a public configuration value or ordinary repository Variable.
3. Keep provider=adzuna and fallback_provider=jsearch for automatic backup, or
   select provider=jsearch for direct use. A local edit affects only local runs;
   commit and push that configuration to activate it on GitHub. Cloudflare code
   and its provider-independent dispatch settings do not need another change.
4. Run a deliberate preview using the existing command:

   ```sh
   /home/nodozi/.local/bin/run-with-secrets python3 -m jobs_bot
   ```

   This makes a real eight-page search but sends nothing and leaves history
   unchanged. On GitHub, choose **Actions → Daily London job shortlist → Run
   workflow → preview → Run workflow**. Verify `event=jsearch_request`, pages
   and returned count, then inspect the shortlist. Do not run this merely to
   test code; it spends real credits. Only one live one-page trial was made
   during development; the eight-page/50 km settings are not live-verified.
5. A later `send` run makes a fresh search and sends to normal recipients,
   unless today's date is already recorded. `test` emails only the sender,
   spends search credits and preserves normal history. If both sources produce
   no unseen matches, normal send still delivers a short 'No matching jobs found
   today' notice. Gmail acceptance records today's send date, but adds no
   vacancy keys. The watchdog therefore confirms completion and stays quiet.
   A failed search is never presented as a successful zero-results notice.
   It uses the separate failure email described above. Preview prints that
   failure message without sending; test emails it only to the sender and
   preserves normal history. Both modes still report the search failure.

To restore Adzuna-only behaviour, select provider=adzuna and fallback_provider="",
retain valid Adzuna credentials and publish those settings. Do not reset either history file. Switching does not
override today's successful-send record or trigger an extra email by itself.

## Filtering, salary and history

JSearch fields are translated into the existing job format. IDs become
`jsearch:<source-id>`, while old Adzuna IDs stay unchanged. Both providers share
`state/seen.json`: matching title/employer/location keys can suppress the same
role across sources. Separate files would allow cross-provider repeat emails.
Different employer names, title wording or locations can still evade matching;
neither this key nor the daily date guard guarantees exactly-once delivery.

JSearch does not supply Adzuna's Accounting & Finance category tag. The adapter
does not invent one. For JSearch, configured finance words must appear in the
title or available description. This retains generic graduate analyst titles
whose adverts contain finance evidence, but incidental finance mentions can
still admit unsuitable roles. Adzuna keeps its stricter category-and-title rule.
Senior exclusions apply to titles for both sources; junior wording changes rank
and is not compulsory. Essential experience, programme eligibility and actual
employer identity remain unchecked. Provider employer fields may name a job
publisher instead of the hiring organisation.

Email subject and attribution follow the selected source. JSearch salary values
retain the supplied pay period; missing currency is labelled unknown rather
than inferred as GBP. Missing salaries remain unknown. No comparison treats
monthly or hourly figures as annual pay.

Run the offline checks without credentials or network access:

```sh
python3 -m unittest discover -s tests -v
```

They verify one-request bounds, malformed data, safe credential destination,
provider selection, field mapping and preview/send/history behaviour using
synthetic responses. They do not prove current quota, geographic precision,
graduate suitability or live email delivery.

Sources: [JSearch documentation](https://www.openwebninja.com/api/jsearch/docs)
and [provider-maintained API reference](https://github.com/OpenWeb-Ninja/openwebninja-skills/blob/main/openwebninja/apis/jsearch/README.md).
