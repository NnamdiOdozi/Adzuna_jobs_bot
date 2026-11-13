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
    ["2026-10-24T05:30:00Z", true],
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
