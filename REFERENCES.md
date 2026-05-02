# Reference projects studied

Peer projects examined during the 2026-05-02 audit cycle.  Each entry notes
one concrete pattern borrowed or consciously diverged from.

| Project | Stars (approx.) | License | Pattern noted |
|---|---|---|---|
| [tldr-ai/pr-pilot](https://github.com/PR-Pilot-AI/pr-pilot) | ★900+ | Apache-2.0 | Prompt templates stored as discrete YAML files with a `{diff}` slot — keeps prompts editable without touching Python. Adopted here as the `_DEFAULT_PROMPT` template approach in `core.py`. |
| [hound-ci/hound](https://github.com/houndci/hound) | ★5 000+ | MIT | Multi-linter fan-out with per-linter independent timeouts and graceful degradation (partial results published even if one linter crashes). Inspired the `error`-field design in `SummaryDoc` and the "all failed vs. partial failure" distinction in `merge_structural`. |
| [reviewdog/reviewdog](https://github.com/reviewdog/reviewdog) | ★8 000+ | MIT | Vendor-neutral tool-runner registry (YAML `runner:` blocks, each with `name`, `cmd`, `errorformat`). Directly paralleled in our `SummaryConfig` schema (name + cmd list + timeout). |
| [coderabbitai/coderabbit](https://github.com/coderabbitai/coderabbit-docs) | ★1 000+, docs repo | CC-BY-4.0 | Section-labelled summary output (`## Walkthrough`, `## Changes`, `## Assessment`) — same structural approach as our four-section prompt (`TLDR`, `FILES`, `RISK`, `TESTS`). Key difference: we keep sections machine-parseable via line prefixes so multiple CLIs can be merged. |
| [github/issue-metrics](https://github.com/github/issue-metrics) | ★700+ | MIT | GitHub Action composite step pattern where the Action `action.yml` shells out to a pip-installed Python package rather than bundling its own runner. Matches our `action.yml` design. Also noted their use of `GITHUB_TOKEN` env-var injection rather than a custom secret, which we mirror. |

## Divergences and rationale

* **No server / daemon process**: reviewdog and CodeRabbit run persistent services; pr-summary-mesh is a pure CLI/Action — no port, no auth server, no webhook registration.  Simpler ops, narrower attack surface.
* **Vendor-neutral by default**: hound hardcodes Ruby/JS linters; we treat every LLM as an interchangeable subprocess behind a common interface.
* **Attribution in merge**: CodeRabbit produces a single-voice summary; our `merge` mode retains `[cli]` attribution per-line so reviewers can trace any claim back to a specific model.
