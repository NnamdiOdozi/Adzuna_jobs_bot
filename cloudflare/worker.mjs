// Dashboard variables configure timing and destinations; tokens and the topic stay Secrets.
function log(context, fields) {
  console.log(JSON.stringify({ ...context, at: new Date().toISOString(), ...fields }));
}

function githubHeaders(env, accept = "application/vnd.github+json") {
  return {
    Authorization: `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
    Accept: accept,
    "Content-Type": "application/json",
    "User-Agent": "adzuna-jobs-timer",
    "X-GitHub-Api-Version": "2026-03-10",
  };
}

async function request(env, url, options, context, event, label) {
    const delays = (env.DISPATCH_RETRY_DELAYS_SECONDS ?? "").split(",")
      .map((value) => value.trim() === "" ? NaN : Number(value) * 1000);
    const timeout = Number(env.DISPATCH_TIMEOUT_SECONDS) * 1000;
    if (!Number.isInteger(timeout) || timeout <= 0 ||
        delays.some((delay) => !Number.isInteger(delay) || delay < 0)) {
      throw new Error("Set valid DISPATCH_RETRY_DELAYS_SECONDS and DISPATCH_TIMEOUT_SECONDS");
    }
    for (let attempt = 1; attempt <= delays.length + 1; attempt++) {
      let response;
      try {
        response = await fetch(url, { ...options, signal: AbortSignal.timeout(timeout) });
      } catch {
        // Fetch errors can contain credentials; record the outcome, not the exception.
      }
      const status = response?.status ?? "network_or_timeout";
      const retryable = !response || [500, 502, 503, 504].includes(status);
      const retry = retryable && attempt <= delays.length;
      const state = response?.ok ? "accepted" : retry ? "retry" : "failed";
      log(context, { event, attempt, status, state,
        ...(retry ? { retry_in_ms: delays[attempt - 1] } : {}) });
      // Acceptance is not email delivery; an ambiguous failure can dispatch twice.
      if (response?.ok) return response;
      await response?.body?.cancel();
      if (!retry) throw new Error(`${label} failed: HTTP ${status}`);
      await new Promise((resolve) => setTimeout(resolve, delays[attempt - 1]));
    }
}

async function deliveryStatus(env, context) {
  try {
    const path = env.DELIVERY_HISTORY_PATH.split("/").map(encodeURIComponent).join("/");
    const response = await request(env,
      `https://api.github.com/repos/${env.GITHUB_REPO}/contents/${path}?ref=${encodeURIComponent(env.GITHUB_REF)}`,
      { method: "GET", headers: githubHeaders(env, "application/vnd.github.raw+json") },
      context, "delivery_read", "GitHub history read");
    const dates = await response.json();
    if (!Array.isArray(dates) || dates.some((date) =>
      typeof date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
      new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) !== date)) {
      throw new Error("Invalid delivery history");
    }
    return dates.includes(context.date) ? "confirmed" : "missing";
  } catch {
    // Unreadable history is not proof that no email was sent.
    return "unknown";
  }
}

async function notify(env, context, status) {
  const server = new URL(env.NTFY_URL);
  if (server.protocol !== "https:" || server.username || server.password ||
      server.search || server.hash || !env.NTFY_TOPIC) {
    throw new Error("Set a valid HTTPS NTFY_URL and private NTFY_TOPIC");
  }
  const message = status === "missing"
    ? `Adzuna jobs bot ${context.date}: today's email-submission record is missing. Check GitHub Actions; this does not prove inbox delivery failed.`
    : `Adzuna jobs bot ${context.date}: unable to confirm today's email submission because GitHub history could not be checked. The email may or may not have been sent. Check GitHub Actions.`;
  await request(env, `${server.href.replace(/\/$/, "")}/${encodeURIComponent(env.NTFY_TOPIC)}`,
    { method: "POST", body: message, headers: {
      Title: "Adzuna jobs bot: delivery unconfirmed", Priority: "high", Tags: "warning",
    } }, context, "ntfy_alert", "Ntfy alert");
}

export default {
  async scheduled(controller, env) {
    const mode = env.RUN_MODE ?? "send";
    if (!["preview", "test", "send"].includes(mode)) {
      throw new Error("RUN_MODE must be preview, test or send");
    }
    const scheduled = new Date(controller.scheduledTime);
    const parts = new Intl.DateTimeFormat("en-GB", {
      timeZone: env.TIMEZONE, weekday: "short", year: "numeric", month: "2-digit",
      day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
    }).formatToParts(scheduled);
    const fields = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
    const time = `${fields.hour}:${fields.minute}`;
    const context = { scheduled: scheduled.toISOString(), mode,
      date: `${fields.year}-${fields.month}-${fields.day}` };
    const recovery = time === env.RECOVERY_TIME;
    const alert = time === env.ALERT_TIME;
    // Both UTC hours may fire; only the matching London time performs each task.
    if (["Sat", "Sun"].includes(fields.weekday) ||
        (time !== env.SEND_TIME && !recovery && !alert)) {
      log(context, { event: "dispatch_skipped", time });
      return;
    }
    if (recovery || alert) {
      if (mode !== "send") {
        log(context, { event: "watchdog_skipped", reason: "non_send_mode" });
        return;
      }
      const status = await deliveryStatus(env, context);
      log(context, { event: "delivery_check", state: status });
      if (status === "confirmed") return;
      if (alert) return notify(env, context, status);
      if (status === "unknown") return;
    }
    await request(env,
      `https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/${env.GITHUB_WORKFLOW}/dispatches`,
      { method: "POST", headers: githubHeaders(env),
        body: JSON.stringify({ ref: env.GITHUB_REF, inputs: { mode } }) },
      context, "workflow_dispatch", "GitHub dispatch");
  },
};
