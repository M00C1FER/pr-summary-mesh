"""DiffProvider abstraction — fetches a unified diff for a PR from any host.

Default impl: GitHub via the `gh` CLI (no SDK dep). Pluggable: anyone can
write a DiffProvider implementing `(repo, pr) -> str` to point at GitLab,
Gitea, Bitbucket, local git, etc.
"""
from __future__ import annotations

import shutil
import subprocess
from typing import Protocol


class DiffProvider(Protocol):
    """Fetch a unified diff for a (repo, pr) pair."""

    def fetch(self, repo: str, pr: int | str) -> str: ...


class GithubDiffProvider:
    """Uses the `gh` CLI (must be installed + authenticated).

    `repo` is the `owner/name` form. `pr` is the PR number.
    """

    def __init__(self, gh_path: str = "gh"):
        self.gh_path = gh_path

    def fetch(self, repo: str, pr: int | str) -> str:
        if not shutil.which(self.gh_path):
            raise RuntimeError(f"`{self.gh_path}` not on PATH; install gh or pass an explicit gh_path")
        proc = subprocess.run(
            [self.gh_path, "pr", "diff", str(pr), "--repo", repo],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"gh pr diff failed: {proc.stderr.strip()}")
        return proc.stdout


class StaticDiffProvider:
    """Returns a pre-supplied string. Useful for tests + offline runs."""

    def __init__(self, diff: str):
        self.diff = diff

    def fetch(self, repo: str, pr: int | str) -> str:  # noqa: ARG002
        return self.diff
