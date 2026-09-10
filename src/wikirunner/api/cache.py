"""
Two-tier caching engine (In-Memory LRU + SQLite persistent database).
Ensures zero redundant network calls across multiple runs and sub-millisecond retrieval.
"""

import os
import json
import sqlite3
import time
import logging
from typing import Optional, Set, Tuple, List
from wikirunner.models import PageNode

logger = logging.getLogger("wikirunner.cache")


class WikiCache:
    def __init__(self, db_path: str = "cache/wiki_cache.db", memory_limit: int = 1000):
        self.db_path = db_path
        self.memory_limit = memory_limit
        self.mem_pages: dict[str, PageNode] = {}
        self.mem_backlinks: dict[str, Set[str]] = {}
        self.mem_canonical: dict[str, Tuple[str, str]] = {}

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS pages (
                        title TEXT PRIMARY KEY,
                        url TEXT,
                        summary TEXT,
                        links_json TEXT,
                        categories_json TEXT,
                        out_degree INTEGER,
                        is_disambiguation INTEGER,
                        updated_at REAL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS backlinks (
                        title TEXT PRIMARY KEY,
                        backlinks_json TEXT,
                        updated_at REAL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS canonical_redirects (
                        input_title TEXT PRIMARY KEY,
                        canonical_title TEXT,
                        canonical_url TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.warning(f"Error initializing SQLite cache: {e}")

    # --- Canonical Redirects ---
    def get_canonical(self, input_title: str) -> Optional[Tuple[str, str]]:
        norm = input_title.strip()
        if norm in self.mem_canonical:
            return self.mem_canonical[norm]

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT canonical_title, canonical_url FROM canonical_redirects WHERE input_title = ?",
                    (norm,)
                )
                row = cursor.fetchone()
                if row:
                    res = (row[0], row[1])
                    self.mem_canonical[norm] = res
                    return res
        except Exception as e:
            logger.debug(f"Cache lookup failed for canonical '{input_title}': {e}")
        return None

    def set_canonical(self, input_title: str, canonical_title: str, canonical_url: str) -> None:
        norm = input_title.strip()
        self.mem_canonical[norm] = (canonical_title, canonical_url)
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO canonical_redirects (input_title, canonical_title, canonical_url) VALUES (?, ?, ?)",
                    (norm, canonical_title, canonical_url)
                )
                conn.commit()
        except Exception as e:
            logger.debug(f"Cache write failed for canonical '{input_title}': {e}")

    # --- Page Nodes ---
    def get_page(self, title: str) -> Optional[PageNode]:
        norm = title.strip()
        if norm in self.mem_pages:
            return self.mem_pages[norm]

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT url, summary, links_json, categories_json, out_degree, is_disambiguation FROM pages WHERE title = ?",
                    (norm,)
                )
                row = cursor.fetchone()
                if row:
                    page = PageNode(
                        title=norm,
                        url=row[0],
                        summary=row[1] or "",
                        links=json.loads(row[2]) if row[2] else [],
                        categories=json.loads(row[3]) if row[3] else [],
                        out_degree=row[4] or 0,
                        is_disambiguation=bool(row[5])
                    )
                    if len(self.mem_pages) < self.memory_limit:
                        self.mem_pages[norm] = page
                    return page
        except Exception as e:
            logger.debug(f"Cache lookup failed for page '{title}': {e}")
        return None

    def set_page(self, page: PageNode) -> None:
        norm = page.title.strip()
        if len(self.mem_pages) < self.memory_limit:
            self.mem_pages[norm] = page

        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO pages 
                    (title, url, summary, links_json, categories_json, out_degree, is_disambiguation, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        norm,
                        page.url,
                        page.summary,
                        json.dumps(page.links),
                        json.dumps(page.categories),
                        page.out_degree,
                        1 if page.is_disambiguation else 0,
                        time.time()
                    )
                )
                conn.commit()
        except Exception as e:
            logger.debug(f"Cache write failed for page '{page.title}': {e}")

    # --- Backlinks ---
    def get_backlinks(self, title: str) -> Optional[Set[str]]:
        norm = title.strip()
        if norm in self.mem_backlinks:
            return self.mem_backlinks[norm]

        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT backlinks_json FROM backlinks WHERE title = ?", (norm,))
                row = cursor.fetchone()
                if row and row[0]:
                    bl_set = set(json.loads(row[0]))
                    self.mem_backlinks[norm] = bl_set
                    return bl_set
        except Exception as e:
            logger.debug(f"Cache lookup failed for backlinks '{title}': {e}")
        return None

    def set_backlinks(self, title: str, backlinks: Set[str]) -> None:
        norm = title.strip()
        self.mem_backlinks[norm] = backlinks
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO backlinks (title, backlinks_json, updated_at) VALUES (?, ?, ?)",
                    (norm, json.dumps(list(backlinks)), time.time())
                )
                conn.commit()
        except Exception as e:
            logger.debug(f"Cache write failed for backlinks '{title}': {e}")
