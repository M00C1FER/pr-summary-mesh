"""Core dispatch — runs the same summarization prompt across all configured CLIs in parallel.

Mirrors the design pattern of `triple-review`: a `SummaryConfig` describes one
LLM CLI's name + argv + timeout. Multiple configs run in parallel via
ThreadPoolExecutor; the output of each is aggregated downstream.
"""
from __future__ import annotations

import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class SummaryConfig:
    """Per-CLI launch config. Same shape as triple-review.ReviewConfig."""
    cli: str
    cmd: List[str] = field(default_factory=list)
    runner: Optional[Callable[[str, str], "SummaryDoc"]] = None
    timeout_s: int = 300


@dataclass
class SummaryDoc:
    """One CLI's structured summary of a PR."""
    cli: str
    tldr: str = ""           # one-paragraph high-level summary
    files_changed: str = ""  # per-file walkthrough
    risk: str = ""           # what could break
    test_plan: str = ""      # how to verify
    raw: str = ""            # full raw model output for audit
    error: Optional[str] = None

    def is_empty(self) -> bool:
        return not (self.tldr or self.files_changed or self.risk or self.test_plan)

    def to_dict(self) -> Dict:
        return {
            "cli": self.cli,
            "tldr": self.tldr,
            "files_changed": self.files_changed,
            "risk": self.risk,
            "test_plan": self.test_plan,
            "error": self.error,
        }


_DEFAULT_PROMPT = """Summarize this pull-request diff for reviewers.

Output four sections, each on its own line, prefixed exactly:
TLDR: <one paragraph, 2-3 sentences, what the PR does>
FILES: <one short bullet per changed file, what changed in it>
RISK: <what could break, 1-3 sentences>
TESTS: <how a reviewer should verify, 1-3 sentences>

Diff:
---
{diff}
---"""


def _shell_runner(cli: str, cmd: List[str], timeout: int):
    """Builds a runner that pipes the diff to a CLI binary's stdin."""
    def run(diff: str, prompt: str) -> SummaryDoc:
        if not shutil.which(cmd[0]):
            return SummaryDoc(cli=cli, error=f"{cmd[0]} not on PATH")
        full_prompt = prompt.format(diff=diff)
        try:
            proc = subprocess.run(
                cmd + [full_prompt],
                input=diff, capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return SummaryDoc(cli=cli, error=f"{cli} timeout after {timeout}s")
        return _parse_summary(cli, proc.stdout)
    return run


def _parse_summary(cli: str, raw: str) -> SummaryDoc:
    """Best-effort parse of the prefixed-section format. Tolerates extra prose."""
    doc = SummaryDoc(cli=cli, raw=raw)
    if not raw.strip():
        return doc
    sections: Dict[str, List[str]] = {"TLDR": [], "FILES": [], "RISK": [], "TESTS": []}
    current: Optional[str] = None
    for line in raw.splitlines():
        stripped = line.strip()
        for key in sections:
            prefix = key + ":"
            if stripped.upper().startswith(prefix):
                current = key
                rest = stripped[len(prefix):].strip()
                if rest:
                    sections[key].append(rest)
                break
        else:
            if current and stripped:
                sections[current].append(stripped)
    doc.tldr = " ".join(sections["TLDR"]).strip()
    doc.files_changed = "\n".join(sections["FILES"]).strip()
    doc.risk = " ".join(sections["RISK"]).strip()
    doc.test_plan = " ".join(sections["TESTS"]).strip()
    return doc


def default_configs() -> List[SummaryConfig]:
    """Bundled 3-CLI preset.

    Like `triple-review.default_configs()`, this is one valid configuration —
    not a hard requirement. Register any CLI via the YAML config or
    `--cli name=cmd[,arg,...]` flag.
    """
    return [
        SummaryConfig(cli="claude",  cmd=["claude",  "-p", "--output-format=text"], timeout_s=300),
        SummaryConfig(cli="gemini",  cmd=["gemini",  "-p"],                          timeout_s=300),
        SummaryConfig(cli="copilot", cmd=["copilot", "-p"],                          timeout_s=300),
    ]


def run_summary(diff: str, configs: Optional[List[SummaryConfig]] = None,
                prompt: str = _DEFAULT_PROMPT) -> List[SummaryDoc]:
    """Run the summary prompt across all configured CLIs in parallel."""
    cfgs = configs or default_configs()
    out: List[SummaryDoc] = []
    with ThreadPoolExecutor(max_workers=len(cfgs)) as pool:
        futures = {}
        for cfg in cfgs:
            runner = cfg.runner or _shell_runner(cfg.cli, cfg.cmd, cfg.timeout_s)
            futures[pool.submit(runner, diff, prompt)] = cfg.cli
        for fut in as_completed(futures):
            cli = futures[fut]
            try:
                out.append(fut.result())
            except Exception as e:
                out.append(SummaryDoc(cli=cli, error=f"{type(e).__name__}: {e}"))
    return out
