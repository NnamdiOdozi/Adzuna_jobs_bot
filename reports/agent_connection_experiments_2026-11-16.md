# Agent connection experiments — 2026-11-16

These manual experiments use synthetic roles, not job-provider searches. They
send no email and do not update sent-job history. Daily delivery stays on Jev.

| Experiment | Execution | Evidence |
| --- | --- | --- |
| Qwen through Copilot SDK | Failed during provider discovery, before agent ranking | [Run 43934364822](https://github.com/NnamdiOdozi/Adzuna_jobs_bot/actions/runs/43934364822) |
| Qwen through Copilot CLI, initial trial | Failed: CLI required an explicit model argument | [Run 43934646775](https://github.com/NnamdiOdozi/Adzuna_jobs_bot/actions/runs/43934646775) |
| CLI follow-up with engine.model | Failed: framework resolved its fallback `auto`, not Qwen | [Run 43935583696](https://github.com/NnamdiOdozi/Adzuna_jobs_bot/actions/runs/43935583696) |
| Native Copilot CLI | Passed connection and nonempty-response checks | [Run 43934631965](https://github.com/NnamdiOdozi/Adzuna_jobs_bot/actions/runs/43934631965) |

The SDK log explicitly skipped `Qwen/Qwen3-235B-A22B-Instruct-2507` because
it found no supported SDK wire API. It then failed to resolve the external
provider from the gateway's model metadata. Changing Nemotron to Qwen therefore
did not fix the agent-runtime integration. The separate direct Nebius ranking
job succeeded, so the failure does not establish that Qwen or the key is broken.

The CLI variant is isolated on branch `experiment/qwen-cli`. It removes
`copilot-sdk: true` and the SDK-only tool-call limit from the maintained source,
then recompiles the generated lock file. Everything else, including Qwen,
the four unseen synthetic candidates and the output validator, stays the same.
Both comparison runs also execute the existing direct Nebius ranking job.
The initial CLI trial reported zero tokens and required an explicit model;
the compiler did not translate the environment setting into a CLI argument.
One follow-up adds `engine.model` from the same configuration output. The
framework retried the initial configuration error three times without inference;
this is not evidence that those retries were useful or incurred model token cost.
The follow-up still selected the framework's `auto` fallback and failed model
catalog resolution. The compiled workflow retained Qwen in the provider setting
but emitted a separate fallback model selector. Dynamic model selection therefore
remains unresolved. Neither CLI failure proves Qwen inference incompatibility.
No further trials were launched. All three comparison runs completed their
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

To repeat either external-provider comparison, open **Compare finance job
rankings → Run workflow**, choose **main** for SDK or **experiment/qwen-cli**
for CLI, enable **example_data** and **include_agent**, leave **fresh_search**
off, and keep **mode=preview**. These consume Nebius credits.

Offline verification: 156/156 Python tests passed; combined line/branch coverage
was 91.23%. The CLI definition compiled with gh-aw v1.2.2 in strict mode.
These checks cannot prove external-provider compatibility; the linked live runs
are the evidence for that boundary. The long lock YAML is compiler output;
maintained agent instructions are 111 lines (SDK) or 110 lines (corrected CLI).

Reference: [GitHub's native CLI example and permission requirements](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli-in-actions).
