"""
WikiRunner - High-Performance Intelligent Wikipedia Speedrun Engine.
"""

from wikirunner.config import RunnerConfig
from wikirunner.models import RunResult, StepLog, PageNode, CandidateLink
from wikirunner.graph.search import WikiSpeedrunner

__version__ = "2.0.0"

__all__ = [
    "WikiSpeedrunner",
    "RunnerConfig",
    "RunResult",
    "StepLog",
    "PageNode",
    "CandidateLink",
]
