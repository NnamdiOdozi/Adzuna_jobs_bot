import assert from "node:assert/strict";
import { test } from "node:test";
import worker from "./worker.mjs";

const env = {
  GITHUB_REPO: "example/jobs",
  GITHUB_WORKFLOW: "daily-jobs.yml",
  GITHUB_REF: "main",
  GITHUB_DISPATCH_TOKEN: "synthetic-token",
  TIMEZONE: "Europe/London",
  SEND_TIME: "06:30",
  RECOVERY_TIME: "06:45",
  ALERT_TIME: "07:00",
  DELIVERY_HISTORY_PATH: "state/delivery.json",
  NTFY_URL: "https://ntfy.example",
  NTFY_TOPIC: "synthetic-topic",
  DISPATCH_RETRY_DELAYS_SECONDS: "2,5",
  DISPATCH_TIMEOUT_SECONDS: "10",
};

test("timer dispatches exactly at London's allowed time", async (t) => {
  const calls = [];
  t.mock.method(globalThis, "fetch", async (...args) => {
    calls.push(args);
    return { ok: true, status: 200 };
  });
  t.mock.method(console, "log", () => {});
  const cases = [
    ["2026-10-26T05:30:00Z", false],
    ["2026-10-26T06:30:00Z", true],
    ["2026-07-20T05:30:00Z", true],
    ["2026-07-20T06:30:00Z", false],
    ["2026-10-24T05:30:00Z", false],
    ["2026-10-25T06:30:00Z", false],
    ["2027-03-28T05:30:00Z", false],
    ["2027-03-29T05:30:00Z", true],
  ];
  for (const [when, expected] of cases) {
    const previous = calls.length;
    await worker.scheduled({ scheduledTime: Date.parse(when) }, env);
    assert.equal(calls.length - previous, Number(expected), when);
  }
  const [url, request] = calls[0];
  assert.equal(url, "https://api.github.com/repos/example/jobs/actions/workflows/daily-jobs.yml/dispatches");
  assert.equal(request.method, "POST");
  assert.equal(request.headers.Authorization, "Bearer synthetic-token");
  assert.deepEqual(JSON.parse(request.body), { ref: "main", inputs: { mode: "send" } });
});

test("GitHub rejection fails visibly without printing its response", async (t) => {
  t.mock.method(console, "log", () => {});
  t.mock.method(globalThis, "fetch", async () => ({ ok: false, status: 403 }));
  await assert.rejects(
    worker.scheduled({ scheduledTime: Date.parse("2026-10-26T06:30:00Z") }, env),
    /GitHub dispatch failed: HTTP 403/,
  );
});

test("configured preview and test modes reach GitHub unchanged", async (t) => {
  const modes = [];
  t.mock.method(console, "log", () => {});
  t.mock.method(globalThis, "fetch", async (url, request) => {
    modes.push(JSON.parse(request.body).inputs.mode);
    return { ok: true, status: 200 };
  });
  for (const mode of ["preview", "test"]) {
    await worker.scheduled(
      { scheduledTime: Date.parse("2026-10-26T06:30:00Z") },
      { ...env, RUN_MODE: mode },
    );
  }
  assert.deepEqual(modes, ["preview", "test"]);
  await assert.rejects(
    worker.scheduled(
      { scheduledTime: Date.parse("2026-10-26T06:30:00Z") },
      { ...env, RUN_MODE: "mistyped" },
    ),
    /RUN_MODE must be/,
  );
  assert.equal(modes.length, 2);
});

test("dispatch retries temporary failures with bounded waits and request timeouts", async (t) => {
  const scenarios = [
    { name: "server error recovers", outcomes: [500, 204], waits: [2000] },
    { name: "bad gateway recovers", outcomes: [502, 204], waits: [2000] },
    { name: "unavailable server recovers", outcomes: [503, 204], waits: [2000] },
    { name: "gateway timeout recovers", outcomes: [504, 204], waits: [2000] },
    { name: "network error recovers", outcomes: [new TypeError("network failed"), 204], waits: [2000] },
    { name: "request timeout recovers", outcomes: [new DOMException("timed out", "TimeoutError"), 204], waits: [2000] },
    { name: "server errors exhaust retries", outcomes: [500, 500, 500], waits: [2000, 5000], error: /HTTP 500/ },
    { name: "unauthorized stops immediately", outcomes: [401], waits: [], error: /HTTP 401/ },
    { name: "forbidden stops immediately", outcomes: [403], waits: [], error: /GitHub dispatch failed: HTTP 403/ },
    { name: "success stops immediately", outcomes: [204], waits: [] },
  ];
  for (const scenario of scenarios) {
    await t.test(scenario.name, async (subtest) => {
      const waits = [];
      const timeouts = [];
      let requests = 0;
      const nativeTimeout = AbortSignal.timeout.bind(AbortSignal);
      subtest.mock.method(console, "log", () => {});
      subtest.mock.method(globalThis, "setTimeout", (callback, delay) => {
        waits.push(delay);
        callback();
        return 0;
      });
      subtest.mock.method(AbortSignal, "timeout", (delay) => {
        timeouts.push(delay);
        return nativeTimeout(delay);
      });
      subtest.mock.method(globalThis, "fetch", async (url, request) => {
        assert.ok(request.signal instanceof AbortSignal);
        const outcome = scenario.outcomes[requests++];
        assert.notEqual(outcome, undefined, "unexpected extra dispatch attempt");
        if (outcome instanceof Error) throw outcome;
        return { ok: outcome >= 200 && outcome < 300, status: outcome };
      });
      const dispatch = worker.scheduled(
        { scheduledTime: Date.parse("2026-10-26T06:30:00Z") }, env,
      );
      if (scenario.error) await assert.rejects(dispatch, scenario.error);
      else await dispatch;
      assert.equal(requests, scenario.outcomes.length);
      assert.deepEqual(waits, scenario.waits);
      assert.deepEqual(timeouts, Array(requests).fill(10000));
    });
  }
});

test("watchdog checks delivery before independent recovery and alerts", async (t) => {
  const cases = [
    { name: "confirmed delivery prevents recovery", time: "06:45", history: ["2026-10-26"], actions: ["history"] },
    { name: "confirmed delivery prevents alert", time: "07:00", history: ["2026-10-26"], actions: ["history"] },
    { name: "missing delivery triggers recovery", time: "06:45", history: ["2026-10-23"], actions: ["history", "dispatch"] },
    { name: "missing delivery triggers alert", time: "07:00", history: [], actions: ["history", "alert"], message: /missing/i },
    { name: "GitHub exhausted retries still alerts", time: "07:00", statuses: [500, 500, 500], actions: ["history", "history", "history", "alert"], message: /unable.*confirm|cannot.*confirm|unconfirmed/i },
    { name: "forbidden history is unknown", time: "07:00", statuses: [403], actions: ["history", "alert"], message: /unable.*confirm|cannot.*confirm|unconfirmed/i },
    { name: "invalid JSON is unknown", time: "07:00", malformed: true, actions: ["history", "alert"], message: /unable.*confirm|cannot.*confirm|unconfirmed/i },
    { name: "invalid schema is unknown", time: "07:00", history: { date: "2026-10-26" }, actions: ["history", "alert"], message: /unable.*confirm|cannot.*confirm|unconfirmed/i },
    { name: "invalid date is unknown", time: "07:00", history: ["yesterday"], actions: ["history", "alert"], message: /unable.*confirm|cannot.*confirm|unconfirmed/i },
    { name: "unknown does not trigger recovery", time: "06:45", statuses: [403], actions: ["history"] },
    { name: "unreachable history does not trigger recovery", time: "06:45", statuses: ["network", "network", "network"], actions: ["history", "history", "history"] },
    { name: "Saturday recovery skips", date: "2026-10-24", time: "06:45", actions: [] },
    { name: "Sunday alert skips", date: "2026-10-25", time: "07:00", actions: [] },
    { name: "summer recovery uses London time", date: "2026-07-20", time: "05:45", history: [], actions: ["history", "dispatch"] },
    { name: "summer alert uses London date", date: "2026-07-20", time: "06:00", history: ["2026-07-20"], actions: ["history"] },
    ...["preview", "test"].flatMap((mode) => ["06:45", "07:00"].map((time) => ({ name: `${mode} skips ${time}`, mode, time, actions: [] }))),
    { name: "recovery dispatch retries", time: "06:45", history: [], dispatch: [502, 204], actions: ["history", "dispatch", "dispatch"] },
    { name: "notification retries then visibly fails safely", time: "07:00", history: [], alert: ["network", 503, 503], actions: ["history", "alert", "alert", "alert"], error: true },
  ];
  for (const scenario of cases) {
    await t.test(scenario.name, async (subtest) => {
      const actions = [], timeouts = [], waits = [], logs = [], notifications = [];
      const counters = { history: 0, dispatch: 0, alert: 0 };
      subtest.mock.method(console, "log", (line) => logs.push(line));
      subtest.mock.method(globalThis, "setTimeout", (callback, delay) => { waits.push(delay); callback(); return 0; });
      subtest.mock.method(AbortSignal, "timeout", (delay) => { timeouts.push(delay); return new AbortController().signal; });
      subtest.mock.method(globalThis, "fetch", async (url, request) => {
        const action = url.includes("/contents/") ? "history" : url.includes("ntfy.example") ? "alert" : "dispatch";
        actions.push(action);
        assert.ok(request.signal instanceof AbortSignal);
        const index = counters[action]++;
        const status = (action === "history" ? scenario.statuses : scenario[action])?.[index] ?? 200;
        if (action === "history") {
          assert.equal(url, "https://api.github.com/repos/example/jobs/contents/state/delivery.json?ref=main");
          assert.equal(request.method ?? "GET", "GET");
          assert.equal(new Headers(request.headers).get("Accept"), "application/vnd.github.raw+json");
          assert.equal(new Headers(request.headers).get("Authorization"), "Bearer synthetic-token");
        } else if (action === "dispatch") {
          assert.equal(url, "https://api.github.com/repos/example/jobs/actions/workflows/daily-jobs.yml/dispatches");
          assert.equal(request.method, "POST");
          assert.deepEqual(JSON.parse(request.body), { ref: "main", inputs: { mode: "send" } });
        } else {
          assert.equal(url, "https://ntfy.example/synthetic-topic");
          assert.equal(request.method, "POST");
          assert.equal(new Headers(request.headers).has("Authorization"), false);
          notifications.push(request.body);
        }
        if (status === "network") throw new TypeError("private https://ntfy.example/synthetic-topic synthetic-token");
        return { ok: status >= 200 && status < 300, status, json: async () => {
          if (scenario.malformed) throw new SyntaxError("private response body");
          return scenario.history;
        } };
      });
      const date = scenario.date ?? "2026-10-26";
      const run = worker.scheduled({ scheduledTime: Date.parse(`${date}T${scenario.time}:00Z`) }, { ...env, RUN_MODE: scenario.mode ?? "send" });
      if (scenario.error) {
        let failure;
        await assert.rejects(run, (error) => { failure = error.message; return true; });
        const visible = [failure, ...logs].join(" ");
        assert.doesNotMatch(visible, /synthetic-token|synthetic-topic|ntfy\.example|private response body/);
        assert.ok(logs.some((line) => JSON.parse(line).state === "failed"));
      } else await run;
      assert.deepEqual(actions, scenario.actions);
      assert.deepEqual(timeouts, Array(actions.length).fill(10000));
      const retries = scenario.actions.length - new Set(scenario.actions).size;
      assert.deepEqual(waits, [2000, 5000].slice(0, retries));
      if (scenario.message) {
        assert.match(notifications[0], scenario.message);
        assert.match(notifications[0], new RegExp(date));
        if (scenario.history === undefined || !Array.isArray(scenario.history) || scenario.history.includes("yesterday")) {
          assert.doesNotMatch(notifications[0], /delivery (?:is )?missing|email (?:was )?not (?:sent|delivered)/i);
        }
      }
    });
  }
});
