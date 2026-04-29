"""pr-summary-mesh: modular multi-LLM pull-request summarizer."""
from .core import SummaryConfig, SummaryDoc, run_summary
from .merge import merge_structural, vote_best
from .config import load_config_yaml, parse_inline_summarizer
from .diff import GithubDiffProvider

__version__ = "0.1.0"
__all__ = [
    "SummaryConfig", "SummaryDoc", "run_summary",
    "merge_structural", "vote_best",
    "load_config_yaml", "parse_inline_summarizer",
    "GithubDiffProvider",
]
