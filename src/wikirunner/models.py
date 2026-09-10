"""
Data models and typed structures for WikiRunner.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set


@dataclass
class CandidateLink:
    title: str
    url: str
    score: float = 0.0
    is_target_backlink: bool = False
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "score": round(self.score, 4),
            "is_target_backlink": self.is_target_backlink,
            "notes": self.notes,
        }


@dataclass
class PageNode:
    title: str
    url: str
    summary: str = ""
    links: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    out_degree: int = 0
    is_disambiguation: bool = False


@dataclass
class StepLog:
    step: int
    current_title: str
    current_url: str
    chosen_title: str
    chosen_url: str
    strategy: str
    score: float
    top_candidates: List[dict] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "current_title": self.current_title,
            "current_url": self.current_url,
            "chosen_title": self.chosen_title,
            "chosen_url": self.chosen_url,
            "strategy": self.strategy,
            "score": round(self.score, 4),
            "top_candidates": self.top_candidates,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
        }


@dataclass
class RunResult:
    status: str  # "victory", "timeout", "dead_end", "max_steps", "error"
    steps: int
    path: List[str]  # List of URLs: e.g. ["/wiki/Apple", "/wiki/Apple_Inc.", "/wiki/Steve_Jobs"]
    path_titles: List[str]
    elapsed_seconds: float
    visited_count: int
    api_calls: int
    log: List[dict] = field(default_factory=list)
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "steps": self.steps,
            "path": self.path,
            "path_titles": self.path_titles,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "visited_count": self.visited_count,
            "api_calls": self.api_calls,
            "log": self.log,
            "error_message": self.error_message,
        }
