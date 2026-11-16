# Agent connection experiments — 2026-11-16

These manual experiments use synthetic roles, not job-provider searches. They
send no email and do not update sent-job history. Daily delivery stays on Jev.

| Experiment | Execution | Evidence |
| --- | --- | --- |
| Qwen through Copilot SDK | Failed during provider discovery, before agent ranking | [Run 43934364822](https://github.com/NnamdiOdozi/Adzuna_jobs_bot/actions/runs/43934364822) |
| Qwen through Copilot CLI, initial trial | Failed: model setting did not reach the CLI | [Run 43934646775](https://github.com/NnamdiOdozi/Adzuna_jobs_bot/actions/runs/43934646775) |
| CLI follow-up with engine.model | Failed: framework resolved its fallback `auto`, not Qwen | [Run 43935583696](https://github.com/NnamdiOdozi/Adzuna_jobs_bot/actions/runs/43935583696) |
| Corrected CLI ranking, bounded direct-JSON task | Passed agent execution, completion and independent output validation | [Run 43939683674](https://github.com/NnamdiOdozi/Adzuna_jobs_bot/actions/runs/43939683674) |
| Native Copilot CLI | Passed connection and nonempty-response checks | [Run 43934631965](https://github.com/NnamdiOdozi/Adzuna_jobs_bot/actions/runs/43934631965) |

The SDK log explicitly skipped `Qwen/Qwen3-235B-A22B-Instruct-2507` because
it found no supported SDK wire API. It then failed to resolve the external
provider from the gateway's model metadata. Changing Nemotron to Qwen therefore
did not fix the agent-runtime integration. The separate direct Nebius ranking
job succeeded, so the failure does not establish that Qwen or the key is broken.

The CLI variant was tested on branch `experiment/qwen-cli` and is now the
maintained manual agentic route on main. It removes
`copilot-sdk: true` and the SDK-only tool-call limit from the maintained source,
then recompiles the generated lock file. Everything else, including Qwen,
the four unseen synthetic candidates and the output validator, stays the same.
Both comparison runs also execute the existing direct Nebius ranking job.
The initial CLI trial reported zero tokens and required an explicit model;
the compiled sandbox command excluded the model environment setting. GitHub's
CLI supports either its model argument or its model environment variable; the
problem was delivery of the setting, not a universal requirement for an argument.
One follow-up adds `engine.model` from the same configuration output. The
framework retried the initial configuration error three times without inference;
this is not evidence that those retries were useful or incurred model token cost.
The follow-up still selected the framework's `auto` fallback and failed model
catalog resolution. The compiled workflow retained Qwen in the provider setting
but emitted a separate fallback model selector. Dynamic model selection therefore
remains unresolved. Neither CLI failure proves Qwen inference incompatibility.
The user requested continued diagnosis after this initial report was published.
A fallback-setting trial also failed because that engine environment expression
was excluded. The next correction uses `engine.model` and removes the redundant
`engine.env.COPILOT_MODEL`. Before dispatch, inspection confirmed the compiled
workflow passes the config-selected model without excluding it from the runtime.
Run 43937838249 confirmed Qwen model resolution and tool execution, but was
cancelled after more than five minutes when generated Python failed on JSON
booleans. The following trial requested direct JSON, allowed at most twelve
inference requests, used a five-minute execution budget and disabled whole-task
retries. Run 43939683674 passed agent execution, conclusion and comparison
validation. All four unseen IDs, input hashes and evidence quotations were
accepted. This is structural validation, not an independently scored suitability
benchmark. Despite the direct-JSON instruction, Qwen still used a scratch
script; task wording did not enforce that restriction.

All six comparison runs completed their
separate direct Nebius ranking call successfully. Actual account charges were
not inspected; do not interpret the failed agent steps as making the whole runs free.

The native example is `.github/workflows/native-copilot-probe.yml`, 33 lines.
It follows GitHub's documented Actions-token authentication and asks about a
graduate accounts assistant and a senior finance lawyer. It checks out no code,
allows no tools and has no repository write permission. Its answer appears in
the run summary and in the `native-copilot-response` artifact. Successful exit
and a nonempty answer prove connectivity, not ranking accuracy or tool execution.
No new subscription or credential was installed; account billing was not inspected.

To repeat it: open **Actions → Native Copilot connection probe → Run workflow**,
select **main**, then **Run workflow**. Open the new run and read its summary.
This consumes the owner's available Copilot allowance, not Nebius/job API credit.
No paid upgrade is part of this experiment.

To repeat the working external-provider comparison, open **Compare finance job
rankings → Run workflow**, choose **main**, enable **example_data** and
**include_agent**, leave **fresh_search** off, and keep **mode=preview**. This
consumes Nebius credits. The failed SDK configuration is retained in the original
run and Git history, not selected by the current workflow.

Offline verification: 156/156 Python tests passed; combined line/branch coverage
was 91.23%. The CLI definition compiled with gh-aw v1.2.2 in strict mode.
These checks cannot prove external-provider compatibility; the linked live runs
are the evidence for that boundary. The long lock YAML is compiler output;
maintained instructions remain short; the original SDK source was 111 lines.
The native connection probe remains 33 lines.

Reference: [GitHub's native CLI example and permission requirements](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli-in-actions).

GitHub guidance checked during the continued investigation:

- [CLI model selection](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference): accepts `--model` or `COPILOT_MODEL`.
- [Agentic Workflows external-provider configuration](https://github.github.com/gh-aw/reference/engines/copilot/): requires a model for external providers, documents provider credentials staying outside the agent container, and distinguishes CLI from SDK operation.
- [Engine model configuration](https://github.github.com/gh-aw/reference/engines/): supports `engine.model` and documents model-resolution evidence and live catalog limitations.
- [GitHub issue 46672](https://github.com/github/gh-aw/issues/46672): records the same missing-model message, but was closed by automatic expiry, not a verified repair.

The documentation supports both model-setting mechanisms. It does not establish
that every dynamic engine environment expression survives the pinned compiler's
isolation boundary. That narrower diagnosis comes from our generated workflow
and execution logs, not a claim that GitHub forbids `engine.env.COPILOT_MODEL`.

Fusion Standard was researched, not run in this experiment. GitHub documents
`copilot --model fusion --fusion-tier standard -p "YOUR PROMPT"` for native
selection. It is available on Copilot Free but uses the underlying model's AI
credits; it is not unlimited free inference. See [Fusion billing](https://docs.github.com/en/copilot/concepts/models/copilot-fusion).
