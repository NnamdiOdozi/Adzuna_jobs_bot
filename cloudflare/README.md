# Daily jobs timer

Cloudflare supplies the clock; GitHub still searches Adzuna, sends the email and
saves history. This replaces GitHub's delayed native schedule. There is no
automatic timer until you deploy this Worker and add its Cron Trigger.

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

3. Add a **Secret** named `GITHUB_DISPATCH_TOKEN`. Supply a GitHub fine-grained
   personal access token restricted to this repository with **Actions: Read and
   write** permission. Keep the token private and note its expiry date. The
   fixed-income token can be reused only if its repository access and permissions
   cover this repository; the Worker code does not require the same token.
4. Under **Settings → Triggers → Cron Triggers**, add the custom expression
   `30 5,6 * * *` and save it. Cloudflare uses UTC. The Worker checks London time,
   allowing only 06:30 Monday–Saturday: 06:30 UTC in winter, 05:30 UTC in summer.
   The other invocation skips without contacting GitHub. Changing `SEND_TIME`
   also requires adjusting the UTC trigger hours/minutes accordingly.
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
Trigger to `30 5,6 * * *`. Save/deploy the settings. Until restored, the timer
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
receipt. This minimal Worker has no retries or delivery monitor; check GitHub if
an email is missing. GitHub runner availability can still delay execution after
Cloudflare's request.

References: [Cloudflare Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/)
and [GitHub workflow dispatch](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event).
