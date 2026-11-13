# Daily jobs timer and completion check

Cloudflare supplies the clock. GitHub searches Adzuna, sends the jobs email and
saves its delivery record. The same Cloudflare Worker also checks completion
and can notify the operator through Ntfy. No new Worker, email-alert service,
database, package installation or public web endpoint is required.

| London time, Monday–Friday | Action |
|---|---|
| 06:30 | Request the normal GitHub workflow, with bounded retries. |
| 06:45 | Read today's delivery record. If missing, request one recovery run. |
| 07:00 | Check again. If missing or unreadable, publish an Ntfy alert. |

These are separate scheduled invocations, not a process waiting for 30 minutes.
An unreadable record means unknown, not proof of failed delivery. The 06:45
check does not dispatch recovery on unknown evidence. At 07:00 it still tries
Ntfy even if GitHub is unreachable. If today's date is present, checks finish
quietly. Preview and sender-only test modes disable recovery and alerts.

## Deploy the update in your existing Cloudflare Worker

The prepared script is local until committed/pushed. Neither a local edit nor a
GitHub push deploys this dashboard-managed Worker. Use the console for this
update; setting up Wrangler is unnecessary. Only the jobs-timer Worker changes.
The fixed-income Worker and shared ukba.workers.dev subdomain are unaffected.

1. In Cloudflare, go to **Workers & Pages → adzuna-jobs-timer → Production**.
   From the current Observability page, click **Settings** in the top row.
2. Under **Variables and Secrets**, use **Add** or **Edit** to set these **Text**
   variables. Keep the first eight existing values; add the watchdog settings.

   | Name | Value |
   |---|---|
   | `GITHUB_REPO` | `NnamdiOdozi/Adzuna_jobs_bot` |
   | `GITHUB_WORKFLOW` | `daily-jobs.yml` |
   | `GITHUB_REF` | `main` |
   | `TIMEZONE` | `Europe/London` |
   | `SEND_TIME` | `06:30` |
   | `RUN_MODE` | `send` |
   | `DISPATCH_RETRY_DELAYS_SECONDS` | `2,5` |
   | `DISPATCH_TIMEOUT_SECONDS` | `10` |
   | `RECOVERY_TIME` | `06:45` |
   | `ALERT_TIME` | `07:00` |
   | `DELIVERY_HISTORY_PATH` | `state/delivery.json` |
   | `NTFY_URL` | Your existing Ntfy server base address, using HTTPS |

   For NTFY_URL, use the address already configured as the Text variable of the
   same name in your fixed-income Cloudflare Worker. This is the server address,
   not the full topic URL. Save/deploy the variable changes if prompted.
3. Keep the existing **Secret** `GITHUB_DISPATCH_TOKEN`. Add a **Secret** named
   `NTFY_TOPIC`, entering the existing topic you subscribe to in the Ntfy app.
   Reusing that topic means jobs alerts appear alongside your existing alerts,
   with the distinct title **Adzuna jobs bot: delivery unconfirmed**. Cloudflare
   cannot reveal a saved Secret; obtain the topic from your own subscription or
   private records. Do not paste it into chat, source code or GitHub.
4. The GitHub token must still allow **Actions: Read and write** for this repo.
   The repository is public, and fine-grained tokens include public repository
   read access. No extra permission should be needed for this public file.
   If the repo becomes private, the token will also need **Contents: Read-only**.
   Do not replace or broaden a shared token unnecessarily. This implementation
   uses the existing topic-based Ntfy publishing setup; it does not add a
   separate Ntfy account access token.
5. Open local `cloudflare/worker.mjs` in your editor and copy all of it.
   In Cloudflare click **Edit code** at the top right. Replace the existing
   script contents with the complete file, keeping the editor's filename even
   if it is `worker.js`. Do not paste `worker.test.mjs`.
6. Click **Deploy**, wait for confirmation, and verify the new version is active
   in **Deployments → Production**. Saving an undeployed version is insufficient.
7. Return to **Settings → Triggers → Cron Triggers**. The section may instead
   be labelled **Trigger Events**. Edit the existing cron through its menu,
   choose the custom-expression field, and replace its expression with:

   ```text
   0,30,45 5,6,7 * * MON-FRI
   ```

   Save it. Replace the existing schedule rather than leaving duplicate triggers.
   Cloudflare documents up to 15 minutes for trigger changes to propagate.

The expression produces nine invocations per weekday. The script selects only
06:30, 06:45 and 07:00 London time; the other six finish without external
requests. This covers both winter and British Summer Time using one trigger.
The normal script requires both retry variables; absent recovery/alert times
leave those checks inactive. Use the exact distinct times in the table.

Deployment does not replay a missed morning automatically. The recovery and
alert tasks run at their scheduled times. On Friday 13 November after 07:00,
the next normal cycle is Monday 16 November.

## What to look for in the logs

Open **Observability**, choose a time range containing the scheduled tasks and
expand an entry to inspect its JSON fields. The scheduled timestamp and London
date identify the daily cycle. The actual timestamp and attempt identify retries.

- At 06:30, `workflow_dispatch` should show `state: accepted`, normally status
  204. A temporary failure shows `state: retry` and its wait; exhausting all
  attempts produces `state: failed` and an error.
- At 06:45, `delivery_check` shows `confirmed`, `missing` or `unknown`.
  Missing is followed by a recovery `workflow_dispatch`; unknown is not.
- At 07:00, a missing or unknown result is followed by `ntfy_alert`.
  Accepted means Ntfy accepted the publication, not that the phone displayed it.
  Exhausted notification attempts produce a visible failure.
- `dispatch_skipped` at the unused UTC times is expected. In preview/test mode,
  `watchdog_skipped` is expected, with no history read or notification.

Also inspect GitHub Actions for the jobs run, Gmail acceptance and saved history.
The checker reads GitHub's committed delivery record, not local laptop state.
That record proves Gmail accepted a submission, not inbox receipt. A delayed or
failed history push may cause a recovery attempt or an unconfirmed-delivery
alert even though Gmail already accepted the message.

## Test without contacting services

From this repository, run:

```sh
node --test cloudflare/worker.test.mjs
```

Node.js 22+ suffices, with no packages or manual downloads. Tests replace requests
and waits with simulations. They contact no Cloudflare, GitHub, Adzuna, Gmail or
Ntfy service and alter no delivery history. They cover temporary failure,
timeouts, retry bounds, both seasons, weekends, recovery, malformed history,
mode skips and Ntfy attempts despite GitHub failures.

These checks prove programmed decisions and timeout wiring. They do not prove
the deployed script/settings match, actual timer delivery, live credentials,
network cancellation or phone/inbox receipt. No live Ntfy publication was made
while preparing this update. A live notification test would need deliberate
authorization and would send a real phone notification.

For GitHub-only preview/test, choose **Actions → Daily London job shortlist →
Run workflow** and select a mode. Preview makes a real Adzuna search but sends
nothing. Test makes a search and sends only to the Gmail sender with a [TEST]
subject. Both leave normal history unchanged; neither tests the watchdog.

A complete Cloudflare preview/test can be scheduled deliberately: choose a
London SEND_TIME at least 20 minutes ahead, set RUN_MODE to preview or test,
deploy, then temporarily use cron `* * * * *`. Only that chosen time dispatches.
Allow trigger propagation, then restore all normal values and the combined
cron above. Watchdog tasks are disabled during these modes.

## Request bounds and remaining limitations

All three types of network work use the configured request timeout and retry
waits: GitHub dispatch, delivery-history reads and Ntfy publication. Values 2,5
allow three attempts, waiting two then five seconds. HTTP 500/502/503/504 and
fetch failures are retried. Other statuses stop immediately; 401/403 need
credentials/permissions investigation and 429 needs rate-limit investigation.
A successful response ends retries. Logs omit private URLs, topics, tokens,
response bodies and exception messages.

Healthy daily operation makes one workflow dispatch and two GitHub history
reads. Checking completion spends no Adzuna credits. A recovery workflow can
make a real Adzuna search and send a real email to normal recipients. The
existing daily-send check and workflow concurrency remain in force; keep
`force_send=false` in the bot config during ordinary operation.

Ambiguous POST failures can cause duplicate dispatches or phone alerts.
Gmail acceptance followed by a failed history save/push can still permit
duplicate email. There is no new persistent notification ledger or alert storm
loop: checks happen at the configured times, with bounded request attempts.

A Cloudflare outage or broken Worker deployment can stop both sending and
checking. A prolonged GitHub outage cannot be repaired by retrying. An Ntfy
outage can prevent alerts; there is no Resend/email fallback in this version.

References: [Cloudflare scheduling](https://developers.cloudflare.com/workers/runtime-apis/handlers/scheduled/),
[Cron configuration](https://developers.cloudflare.com/workers/configuration/cron-triggers/),
[GitHub repository contents](https://docs.github.com/en/rest/repos/contents),
[GitHub token permissions](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
and [Ntfy publishing](https://docs.ntfy.sh/publish/).
