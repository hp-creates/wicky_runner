"""
Configuration management for WikiRunner.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class RunnerConfig:
    # API & Networking
    api_endpoint: str = "https://en.wikipedia.org/w/api.php"
    base_url: str = "https://en.wikipedia.org"
    user_agent: str = "WikiSpeedrunner/2.0 (Senior-Arch Bot; https://github.com/example/wiki-speedrunner)"
    request_timeout: float = 10.0
    max_retries: int = 3
    throttle_seconds: float = 0.05  # Polite delay between outbound calls
    batch_size: int = 50

    # Search & Constraints
    max_steps: int = 15
    timeout_seconds: float = 120.0
    max_backlinks_fetch: int = 500  # Number of backlinks to index for target
    beam_width: int = 5

    # Caching
    cache_dir: str = "cache"
    sqlite_db_path: str = "cache/wiki_cache.db"
    enable_cache: bool = True

    # Heuristics
    weight_backlink_hit: float = 1000.0  # Dominant bonus for connecting to target backlink
    weight_lexical_similarity: float = 10.0
    weight_semantic_similarity: float = 5.0
    weight_hubness: float = 1.0

    # Strategic LLM
    enable_llm_advisor: bool = True
    llm_stagnation_threshold: int = 2
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    preferred_llm_provider: str = "auto"  # "auto", "groq", "gemini"
    gemini_model: str = "models/gemini-1.5-flash"
    groq_model: str = "llama-3.1-8b-instant"
