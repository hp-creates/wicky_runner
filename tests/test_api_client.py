"""
Unit tests for WikiClient and WikiCache.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from wikirunner.config import RunnerConfig
from wikirunner.api.client import WikiClient
from wikirunner.api.cache import WikiCache


@pytest.fixture
def test_client(tmp_path):
    db_file = str(tmp_path / "test_cache.db")
    config = RunnerConfig(sqlite_db_path=db_file)
    cache = WikiCache(db_path=db_file)
    return WikiClient(config, cache)


def test_resolve_title_canonical(test_client):
    title, url = test_client.resolve_title("apple")
    assert title == "Apple"
    assert url == "/wiki/Apple"


def test_resolve_title_redirect(test_client):
    title, url = test_client.resolve_title("USA")
    assert title == "United States"
    assert url == "/wiki/United_States"


def test_get_page_data_and_caching(test_client):
    page = test_client.get_page_data("Python (programming language)")
    assert page is not None
    assert page.title == "Python (programming language)"
    assert page.out_degree > 50
    assert len(page.summary) > 20

    # Second fetch should hit cache
    cached_page = test_client.cache.get_page("Python (programming language)")
    assert cached_page is not None
    assert cached_page.title == page.title


def test_get_backlinks(test_client):
    backlinks = test_client.get_backlinks("Steve Jobs", max_count=50)
    assert len(backlinks) > 10
    assert "Apple Inc." in backlinks
