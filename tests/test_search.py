"""
Unit tests for WikiSpeedrunner search engine.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from wikirunner.config import RunnerConfig
from wikirunner.graph.search import WikiSpeedrunner


def test_identical_start_and_target():
    runner = WikiSpeedrunner(RunnerConfig())
    res = runner.run("Apple", "Apple")
    assert res.status == "victory"
    assert res.steps == 0
    assert len(res.path) == 1


def test_invalid_article():
    runner = WikiSpeedrunner(RunnerConfig())
    res = runner.run("Xksjdflkjw908239048", "Apple")
    assert res.status == "error"
    assert "Could not resolve" in res.error_message


def test_speedrun_apple_to_steve_jobs():
    runner = WikiSpeedrunner(RunnerConfig())
    res = runner.run("Apple", "Steve Jobs")
    assert res.status == "victory"
    assert res.steps <= 3
    assert "Steve Jobs" in res.path_titles[-1]


def test_path_links_actually_exist_on_preceding_page():
    runner = WikiSpeedrunner(RunnerConfig())
    res = runner.run("Apple", "Steve Jobs")
    assert res.status == "victory"
    assert len(res.path_titles) >= 2
    for i in range(len(res.path_titles) - 1):
        source = res.path_titles[i]
        dest = res.path_titles[i + 1]
        page = runner.client.get_page_data(source)
        assert page is not None
        # Check that destination is indeed among the outgoing links of source
        assert any(l.lower() == dest.lower() for l in page.links), f"Link '{dest}' was not found on page '{source}'!"

