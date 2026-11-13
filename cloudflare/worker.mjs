// Dashboard variables configure the schedule and GitHub destination; the token is a Secret.
export default {
  async scheduled(controller, env) {
    const mode = env.RUN_MODE ?? "send";
    if (!["preview", "test", "send"].includes(mode)) {
      throw new Error("RUN_MODE must be preview, test or send");
    }
    const scheduled = new Date(controller.scheduledTime);
    const parts = new Intl.DateTimeFormat("en-GB", {
      timeZone: env.TIMEZONE,
      weekday: "short",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    }).formatToParts(scheduled);
    const fields = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
    const time = `${fields.hour}:${fields.minute}`;
    const context = { at: new Date().toISOString(), scheduled: scheduled.toISOString() };
    // Both UTC hours are checked; only the one matching London time dispatches.
    if (fields.weekday === "Sun" || time !== env.SEND_TIME) {
      console.log(JSON.stringify({ ...context, event: "dispatch_skipped", time }));
      return;
    }
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
        response = await fetch(
          `https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/${env.GITHUB_WORKFLOW}/dispatches`,
          {
            method: "POST",
            signal: AbortSignal.timeout(timeout),
            headers: {
              Authorization: `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
              Accept: "application/vnd.github+json",
              "Content-Type": "application/json",
              "User-Agent": "adzuna-jobs-timer",
              "X-GitHub-Api-Version": "2026-03-10",
            },
            body: JSON.stringify({ ref: env.GITHUB_REF, inputs: { mode } }),
          },
        );
      } catch {
        // Fetch errors can contain credentials; record the outcome, not the exception.
      }
      const status = response?.status ?? "network_or_timeout";
      const retryable = !response || [500, 502, 503, 504].includes(status);
      const retry = retryable && attempt <= delays.length;
      const state = response?.ok ? "accepted" : retry ? "retry" : "failed";
      console.log(JSON.stringify({ ...context, at: new Date().toISOString(),
        event: "workflow_dispatch", mode, attempt, status, state,
        ...(retry ? { retry_in_ms: delays[attempt - 1] } : {}) }));
      // Acceptance is not email delivery; an ambiguous failure can dispatch twice.
      if (response?.ok) return;
      await response?.body?.cancel();
      if (!retry) throw new Error(`GitHub dispatch failed: HTTP ${status}`);
      await new Promise((resolve) => setTimeout(resolve, delays[attempt - 1]));
    }
  },
};
