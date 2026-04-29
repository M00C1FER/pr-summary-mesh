"""pr-summary-mesh CLI."""
from __future__ import annotations

import argparse
import sys
from typing import List

from .config import load_config_yaml, parse_inline_summarizer
from .core import SummaryConfig, default_configs, run_summary
from .diff import GithubDiffProvider
from .merge import merge_structural, render_pr_body, vote_best


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pr-summary-mesh",
        description="Modular multi-LLM PR summarizer (any vendor, registered via YAML or inline)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
CLI registration (mutually compatible):
  --config triple-review.yaml         load summarizers from a YAML file
  --cli name=cmd[,arg,...]            register a single summarizer inline (repeatable)
  (none of the above)                 use the bundled 3-CLI preset

Diff source (one required, except --list-clis):
  --pr <repo>#<n>                     fetch via gh CLI (e.g. owner/repo#42)
  --diff-file <path>                  read a unified diff from a file
""",
    )
    parser.add_argument("--config", metavar="PATH", help="YAML config file")
    parser.add_argument("--cli", action="append", metavar="NAME=CMD[,ARG,...]",
                        default=[], help="register a summarizer inline (repeatable)")
    parser.add_argument("--pr", help="PR ref like owner/repo#42 (uses `gh pr diff`)")
    parser.add_argument("--diff-file", help="read a unified diff from a local file")
    parser.add_argument("--mode", choices=["merge", "vote"], default="merge",
                        help="aggregation strategy (default: merge)")
    parser.add_argument("--render", choices=["pr-body", "raw", "json"], default="pr-body",
                        help="output format")
    parser.add_argument("--list-clis", action="store_true",
                        help="print resolved summarizer registry and exit")
    args = parser.parse_args()

    configs = _resolve_configs(args)
    if args.list_clis:
        for c in configs:
            print(f"  {c.cli:20} cmd={c.cmd}  timeout={c.timeout_s}s")
        return 0

    if not args.pr and not args.diff_file:
        parser.error("provide --pr <repo>#<n> or --diff-file <path>")

    diff = _resolve_diff(args)
    docs = run_summary(diff, configs=configs)
    merged = merge_structural(docs) if args.mode == "merge" else vote_best(docs)

    if args.render == "raw":
        print(merged.raw or "")
    elif args.render == "json":
        import json
        print(json.dumps(merged.to_dict(), indent=2))
    else:
        print(render_pr_body(merged))
    return 0 if not merged.error else 1


def _resolve_configs(args) -> List[SummaryConfig]:
    cfgs: List[SummaryConfig] = []
    if args.config:
        cfgs.extend(load_config_yaml(args.config))
    for spec in args.cli:
        cfgs.append(parse_inline_summarizer(spec))
    if not cfgs:
        cfgs = default_configs()
    return cfgs


def _resolve_diff(args) -> str:
    if args.diff_file:
        with open(args.diff_file, encoding="utf-8") as f:
            return f.read()
    repo, _, pr = args.pr.partition("#")
    if not repo or not pr:
        raise SystemExit(f"--pr must be `owner/repo#N`, got {args.pr!r}")
    return GithubDiffProvider().fetch(repo, pr)


if __name__ == "__main__":
    sys.exit(main())
