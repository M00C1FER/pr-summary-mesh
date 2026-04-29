"""YAML loader for the CLI registry.

Schema is intentionally identical to triple-review's so a single
`triple-review.yaml` (or `pr-summary.yaml`) can power both tools.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from .core import SummaryConfig


def load_config_yaml(path: str | Path) -> List[SummaryConfig]:
    """Load summarizers from a YAML config.

    Schema:
        clis:                                       # OR  summarizers: (alias)
          - name: claude
            cmd: ["claude", "-p"]
            timeout_s: 300
          - name: ollama
            cmd: ["ollama", "run", "qwen2.5"]
            timeout_s: 600
    """
    try:
        import yaml  # type: ignore
    except ImportError as e:
        raise RuntimeError("PyYAML required: pip install pyyaml") from e
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"config not found: {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{p}: top-level must be a mapping")
    entries = data.get("summarizers", data.get("clis"))
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"{p}: missing top-level `summarizers:` (or `clis:`) list")
    out: List[SummaryConfig] = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"{p}: entry {i} is not a mapping")
        name = entry.get("name")
        cmd = entry.get("cmd")
        if not name or not isinstance(name, str):
            raise ValueError(f"{p}: entry {i} missing required `name`")
        if not cmd or not isinstance(cmd, list):
            raise ValueError(f"{p}: entry {i}.cmd must be a non-empty list")
        out.append(SummaryConfig(
            cli=name,
            cmd=[str(x) for x in cmd],
            timeout_s=int(entry.get("timeout_s", 300)),
        ))
    return out


def parse_inline_summarizer(spec: str) -> SummaryConfig:
    """Parse `--cli name=arg1,arg2,...` into a SummaryConfig."""
    if "=" not in spec:
        raise ValueError(f"--cli spec must be `name=cmd[,arg,...]`, got {spec!r}")
    name, _, rest = spec.partition("=")
    name = name.strip()
    if not name:
        raise ValueError(f"--cli spec missing name: {spec!r}")
    parts = [p for p in rest.split(",") if p]
    if not parts:
        raise ValueError(f"--cli spec missing cmd: {spec!r}")
    return SummaryConfig(cli=name, cmd=parts, timeout_s=300)
