# Daily jobs timer

Cloudflare supplies the clock; GitHub still searches Adzuna, sends the email and
saves history. This replaces GitHub's delayed native schedule. There is no
automatic timer until you deploy this Worker and add its Cron Trigger.

## Update the existing Worker after a failed dispatch

On 13 November the timer fired, but GitHub dispatch returned HTTP 500. This
replacement script retries temporary failures; it does not add a watchdog.
Use the dashboard for this update because the existing Worker is managed there.
Pushing files to GitHub does not deploy it, and no Wrangler setup is required.

1. From the current **Observability** screen, click **Settings** in the top row.
   Check that the breadcrumb still names **adzuna-jobs-timer → Production**.
2. Find **Variables and Secrets** and add these two **Text** variables using
   **Add** or **Edit**, depending on the panel shown. These values are not secrets.

   | Variable name | Exact value | Meaning |
   |---|---|---|
   | `DISPATCH_RETRY_DELAYS_SECONDS` | `2,5` | Two waits, allowing three attempts altogether |
   | `DISPATCH_TIMEOUT_SECONDS` | `10` | Maximum wait for each GitHub response |

   Save the variables and click **Deploy** if offered. Add them before replacing
   the script: the old script ignores them; the new script requires them.
   Keep all existing variables and the `GITHUB_DISPATCH_TOKEN` Secret.
3. Open the local `cloudflare/worker.mjs` file in your editor and copy its entire
   contents. It contains code, not credentials. In Cloudflare click **Edit code**
   at the top right, select the existing script contents and replace them with
   the complete contents of that file. Keep the existing editor filename, even
   if Cloudflare calls it `worker.js`. Do not paste `worker.test.mjs`.
4. Click **Deploy** in the editor and wait for its success confirmation. Return
   to **Deployments** and check that the new deployment is active in Production.
   If the editor only saves a version, deploy that version to Production before
   leaving. The location or wording of the final deploy button may vary.
5. Under **Settings**, check the existing Cron Trigger still reads
   `30 5,6 * * MON-FRI`, as confirmed in the 13 November dashboard. Keep
   `TIMEZONE=Europe/London`, `SEND_TIME=06:30` and normal `RUN_MODE=send`.
   No trigger or shared `ukba.workers.dev` subdomain change is needed.

This updates only the jobs timer. It does not alter the fixed-income Worker,
GitHub secrets, job filters, Adzuna request logic or sent-job history. It will
not automatically replay today's missed run. Monday–Friday scheduling means
the next normal morning after Friday 13 November is Monday 16 November.

### Verify retries without sending mail or spending API requests

From a terminal in this repository, run:

```sh
node --test cloudflare/worker.test.mjs
```

These local tests replace GitHub requests and retry waits with simulations.
They do not contact Cloudflare, GitHub, Adzuna or Gmail and do not change history.
They cover server failures, network errors/timeouts, eventual success, exhausted
retries and authentication errors that stop immediately. Passing them checks
the script's logic; it does not verify what was pasted into the dashboard.

At the next normal scheduled run, open **Observability**, set its date range to
include 06:30 and expand the `workflow_dispatch` entry if necessary to see JSON.
Healthy dispatch shows `state: accepted`, normally `status: 204`, `attempt: 1`.
A temporary failure shows `state: retry`, `status: 500` (or another retryable
status), `attempt: 1`, `retry_in_ms: 2000`. A successful second attempt shows
`state: accepted`, `attempt: 2`. After three failed attempts it shows
`state: failed` and an error. A matching GitHub Actions run must also appear;
then inspect its Gmail-acceptance and history-save events. Dispatch acceptance
alone is not proof that email was submitted or received.

For a deliberate live test without recipients, follow the existing preview
instructions below. Preview still spends an Adzuna request; `test` sends a real
sender-only email. Do not change the timer merely to run the free offline tests.

The configured retries cover HTTP 500/502/503/504 and fetch errors, including
timeouts. Other HTTP statuses stop immediately; 401/403 require investigating
credentials/permissions, and 429 requires checking rate limits before retrying.
Each attempt has a fresh timeout. Logs omit tokens, request headers, response
bodies and network exception messages. With values above, three timed-out
attempts take approximately 37 seconds including waits.

An ambiguous failure can still have created a workflow run. GitHub concurrency
and the bot's daily-send history reduce repeat-send risk, but Gmail acceptance
followed by a history/push failure can still permit a duplicate. Retries do not
monitor email completion or recover a prolonged outage. A separate watchdog
remains a possible future addition, requiring its own deployment and permissions.

## Set up in the Cloudflare dashboard

1. Create a Worker named `adzuna-jobs-timer`. Open **Edit code**, replace the
   starter script with all of `worker.mjs` in this folder, and deploy it.
   The script has no imports, packages, database or other Worker dependencies.
2. Under **Settings → Variables and Secrets**, add these plain-text variables:

   | Name | Value |
   |---|---|
   | `GITHUB_REPO` | `NnamdiOdozi/Adzuna_jobs_bot` |
   | `GITHUB_WORKFLOW` | `daily-jobs.yml` |
   | `GITHUB_REF` | `main` |
   | `TIMEZONE` | `Europe/London` |
   | `SEND_TIME` | `06:30` |
   | `RUN_MODE` | `send` normally; `preview` or `test` for testing |
   | `DISPATCH_RETRY_DELAYS_SECONDS` | `2,5` |
   | `DISPATCH_TIMEOUT_SECONDS` | `10` |

3. Add a **Secret** named `GITHUB_DISPATCH_TOKEN`. Supply a GitHub fine-grained
   personal access token restricted to this repository with **Actions: Read and
   write** permission. Keep the token private and note its expiry date. The
   fixed-income token can be reused only if its repository access and permissions
   cover this repository; the Worker code does not require the same token.
4. Under **Settings → Triggers → Cron Triggers**, add the custom expression
   `30 5,6 * * MON-FRI` and save it. Cloudflare uses UTC. The Worker checks London
   time, allowing 06:30: 06:30 UTC in winter, 05:30 UTC in summer.
   The other invocation skips without contacting GitHub. Changing `SEND_TIME`
   also requires adjusting the UTC trigger hours/minutes accordingly.
   The bot also permits normal emails Monday–Friday only. Older daily cron
   expressions remain safe: Saturday dispatch exits with `reason=non_send_day`
   before Adzuna or Gmail, and the Worker itself skips Sundays.
5. Enable **Workers Logs** under the Worker's observability settings. Cron changes
   can take up to 15 minutes to propagate. Look for `workflow_dispatch` in the
   Worker logs and a matching run under GitHub Actions. A successful dispatch
   confirms GitHub accepted the request, not successful execution or email receipt.

There is no public HTTP endpoint to trigger an email. Visiting the Worker's URL
does not run the scheduled handler. A dashboard test of the scheduled handler at
06:30 London time sends a real GitHub request and may cause a real email. Use the
offline checks below for testing without services.

## Daily limit and testing

There are three workflow modes:

| Mode | Email | Normal history |
|---|---|---|
| `preview` | None; prints the shortlist in GitHub logs | Unchanged |
| `test` | Only the Gmail account in `GMAIL_SENDER`; subject starts `[TEST]` | Unchanged |
| `send` | Normal configured recipients | Updated after acceptance |

Preview and test still search Adzuna. Test sends a real email to the sender,
never reads the normal recipient settings, and works after today's normal send.
It still excludes previously emailed jobs, so an empty test shortlist is possible.
No email address needs to be added to the public code.

To use the new modes from Cloudflare, first replace its deployed code with the
latest `worker.mjs` here and deploy. Changing GitHub files alone does not update
the dashboard-managed Worker. In **Settings → Variables and Secrets**, add or
edit the Text variable `RUN_MODE`, set it to `test` (or `preview` for no email),
and click **Deploy**. If omitted, the Worker retains its original `send` behaviour.

For a complete Cloudflare-to-GitHub test today, choose a London time at least
20 minutes ahead. Set `SEND_TIME` to that time in `HH:MM` form and deploy. Under
**Settings → Triggers → Cron Triggers**, temporarily edit the existing expression
to `* * * * *`. It will check every minute but dispatch only at your chosen time;
Sunday remains excluded. Allow up to 15 minutes for the trigger change to apply.
Watch Worker logs for `workflow_dispatch` with `mode: test`, then the GitHub
Actions run and your own inbox. With `preview`, inspect GitHub logs instead.

Afterwards, restore `SEND_TIME` to `06:30`, `RUN_MODE` to `send`, and the Cron
Trigger to `30 5,6 * * MON-FRI`. Save/deploy the settings. Until restored, the timer
will continue using the test time or test mode. To test GitHub alone without
Cloudflare, use **Actions → Daily London job shortlist → Run workflow → test**.
Locally, use the approved launcher with `python3 -m jobs_bot --test-send`.

In the root `config.toml`, `[email]` contains `force_send = false`. Set it to
`true` for a deliberate extra email on the same day, then restore `false`.
The override still filters previously emailed vacancies. It also still makes
real Adzuna requests and sends real mail when you use send mode. A local config
edit affects local commands; GitHub uses the version committed to `main`.
While `true` is published, every send run can bypass the daily limit.

Run from the repository root:

```sh
python3 -m unittest discover -s tests -v
node --test cloudflare/worker.test.mjs
```

These checks use synthetic credentials and replace service calls. Python 3.12+
and Node.js 22+ suffice; no packages or manual downloads are needed. Tests cover
winter/summer, the clock-change weekends, Sundays, the GitHub request and rejected
requests. They do not prove deployed credentials, actual timer delivery or inbox
receipt. Retries are bounded and there is no delivery monitor; check GitHub if
an email is missing. GitHub runner availability can still delay execution after
Cloudflare's request.

References: [Cloudflare Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/)
and [GitHub workflow dispatch](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event).
