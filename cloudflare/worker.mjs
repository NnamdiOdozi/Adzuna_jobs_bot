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
    const response = await fetch(
      `https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/${env.GITHUB_WORKFLOW}/dispatches`,
      {
        method: "POST",
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
    console.log(JSON.stringify({ ...context, event: "workflow_dispatch", mode, status: response.status }));
    // Acceptance means GitHub received the request, not that an email was delivered.
    if (!response.ok) throw new Error(`GitHub dispatch failed: HTTP ${response.status}`);
  },
};
