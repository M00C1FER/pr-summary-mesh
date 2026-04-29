"""Aggregate multiple SummaryDoc objects into one consolidated output.

Two modes:
  • merge_structural — concatenate sections with per-CLI attribution
  • vote_best        — pick the single SummaryDoc whose sections are the
                       longest non-empty (proxy for "most thorough")
"""
from __future__ import annotations

from typing import List

from .core import SummaryDoc


def merge_structural(docs: List[SummaryDoc]) -> SummaryDoc:
    """Build a single SummaryDoc by concatenating per-CLI contributions.

    Each section becomes a multi-paragraph block with `[cli]` prefixes so
    reviewers can trace back to source. Errors are surfaced as a footnote.
    """
    valid = [d for d in docs if not d.error and not d.is_empty()]
    errored = [d for d in docs if d.error]

    if not valid:
        msg = "All summarizers failed or returned empty."
        if errored:
            msg += " " + "; ".join(f"{d.cli}: {d.error}" for d in errored)
        return SummaryDoc(cli="merged", error=msg)

    def join(field: str) -> str:
        chunks = []
        for d in valid:
            value = getattr(d, field, "").strip()
            if value:
                chunks.append(f"[{d.cli}] {value}")
        return "\n\n".join(chunks)

    merged = SummaryDoc(
        cli="merged",
        tldr=join("tldr"),
        files_changed=join("files_changed"),
        risk=join("risk"),
        test_plan=join("test_plan"),
    )
    if errored:
        # Append degraded-vendors footnote
        notes = "\n_Note: " + ", ".join(f"{d.cli} ({d.error})" for d in errored) + "_"
        merged.tldr = (merged.tldr + notes) if merged.tldr else notes
    return merged


def vote_best(docs: List[SummaryDoc]) -> SummaryDoc:
    """Pick the SummaryDoc with the most filled-in content (proxy for thoroughness)."""
    valid = [d for d in docs if not d.error and not d.is_empty()]
    if not valid:
        return SummaryDoc(cli="vote", error="no valid summaries")

    def score(d: SummaryDoc) -> int:
        return sum(len(getattr(d, f, "")) for f in ("tldr", "files_changed", "risk", "test_plan"))

    return max(valid, key=score)


def render_pr_body(merged: SummaryDoc, marker: str = "<!-- pr-summary-mesh -->") -> str:
    """Format a merged SummaryDoc as a PR description body fragment.

    Wraps the output in marker comments so an updater can find/replace it
    on subsequent runs.
    """
    if merged.error:
        return f"{marker}\n_pr-summary-mesh: {merged.error}_\n{marker}\n"
    parts = [marker, "## Summary (auto-generated)"]
    if merged.tldr:
        parts.append("**TL;DR**\n\n" + merged.tldr + "\n")
    if merged.files_changed:
        parts.append("**Changed files**\n\n" + merged.files_changed + "\n")
    if merged.risk:
        parts.append("**Risk**\n\n" + merged.risk + "\n")
    if merged.test_plan:
        parts.append("**How to verify**\n\n" + merged.test_plan + "\n")
    parts.append(marker)
    return "\n".join(parts) + "\n"
