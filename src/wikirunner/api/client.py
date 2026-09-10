"""
Production-grade MediaWiki Action API client.
Features connection pooling, automatic redirect resolution, batched requests,
backlinks discovery, and integration with the two-tier cache.
"""

import time
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Tuple, Set, List, Dict

from wikirunner.config import RunnerConfig
from wikirunner.models import PageNode
from wikirunner.api.cache import WikiCache

logger = logging.getLogger("wikirunner.client")


class WikiClient:
    def __init__(self, config: RunnerConfig, cache: Optional[WikiCache] = None):
        self.config = config
        self.cache = cache or WikiCache(db_path=config.sqlite_db_path)
        self.session = self._create_session()
        self.api_calls_count = 0

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": self.config.user_agent,
            "Accept": "application/json"
        })
        retries = Retry(
            total=self.config.max_retries,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=25)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _get(self, params: dict) -> Optional[dict]:
        self.api_calls_count += 1
        params["format"] = "json"
        params["formatversion"] = 2

        if self.config.throttle_seconds > 0:
            time.sleep(self.config.throttle_seconds)

        try:
            resp = self.session.get(
                self.config.api_endpoint,
                params=params,
                timeout=self.config.request_timeout
            )
            if resp.status_code != 200:
                logger.warning(f"MediaWiki API error: HTTP {resp.status_code} for params: {params.get('action')}")
                return None
            return resp.json()
        except requests.RequestException as e:
            logger.warning(f"Network error calling MediaWiki API: {e}")
            return None

    def resolve_title(self, title: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolves title capitalization and redirects to the canonical Wikipedia title and URL.
        Example: 'apple' -> ('Apple', '/wiki/Apple')
                 'steve jobs' -> ('Steve Jobs', '/wiki/Steve_Jobs')
        """
        norm = title.strip()
        if not norm:
            return None, None

        if self.config.enable_cache:
            cached = self.cache.get_canonical(norm)
            if cached:
                return cached

        params = {
            "action": "query",
            "titles": norm,
            "redirects": 1,
        }
        data = self._get(params)
        if not data or "query" not in data:
            return None, None

        pages = data["query"].get("pages", [])
        if not pages:
            return None, None

        page = pages[0]
        if page.get("missing") or page.get("invalid"):
            logger.warning(f"Title '{title}' does not exist on Wikipedia.")
            return None, None

        canonical_title = page.get("title")
        if not canonical_title:
            return None, None

        canonical_url = f"/wiki/{canonical_title.replace(' ', '_')}"
        if self.config.enable_cache:
            self.cache.set_canonical(norm, canonical_title, canonical_url)
            self.cache.set_canonical(canonical_title, canonical_title, canonical_url)

        return canonical_title, canonical_url

    def get_backlinks(self, title: str, max_count: Optional[int] = None) -> Set[str]:
        """
        Fetches the inbound links (pages linking TO this article).
        This is the secret weapon for Bidirectional search!
        """
        if max_count is None:
            max_count = self.config.max_backlinks_fetch

        norm = title.strip()
        if self.config.enable_cache:
            cached = self.cache.get_backlinks(norm)
            if cached and len(cached) > 0:
                logger.debug(f"Cache hit for backlinks of '{norm}': {len(cached)} backlinks")
                return cached

        backlinks = set()
        params = {
            "action": "query",
            "list": "backlinks",
            "bltitle": norm,
            "blnamespace": 0,       # Main article namespace only
            "blfilterredir": "all",  # Include redirects to this page
            "bllimit": "max"         # Usually 500 for standard clients
        }

        while len(backlinks) < max_count:
            data = self._get(params)
            if not data or "query" not in data:
                break

            items = data["query"].get("backlinks", [])
            for item in items:
                bl_title = item.get("title")
                if bl_title and ":" not in bl_title:
                    backlinks.add(bl_title)
                    if len(backlinks) >= max_count:
                        break

            # Handle pagination
            if "continue" in data and len(backlinks) < max_count:
                params["blcontinue"] = data["continue"].get("blcontinue")
            else:
                break

        logger.info(f"Retrieved {len(backlinks)} backlinks for '{norm}'")
        if self.config.enable_cache and len(backlinks) > 0:
            self.cache.set_backlinks(norm, backlinks)

        return backlinks

    def get_page_data(self, title: str) -> Optional[PageNode]:
        """
        Fetches full structured page information: lead summary, links, categories, out-degree.
        """
        norm = title.strip()
        if self.config.enable_cache:
            cached = self.cache.get_page(norm)
            if cached:
                return cached

        # Step 1: Query extracts and categories
        extract_params = {
            "action": "query",
            "titles": norm,
            "prop": "extracts|categories",
            "exintro": 1,
            "explaintext": 1,
            "cllimit": "max",
            "redirects": 1
        }
        data = self._get(extract_params)
        if not data or "query" not in data:
            return None

        pages = data["query"].get("pages", [])
        if not pages:
            return None

        page = pages[0]
        if page.get("missing") or page.get("invalid"):
            return None

        canonical_title = page.get("title", norm)
        canonical_url = f"/wiki/{canonical_title.replace(' ', '_')}"
        summary = page.get("extract", "") or ""

        categories = [
            c.get("title", "").replace("Category:", "")
            for c in page.get("categories", [])
            if c.get("title")
        ]

        is_disambig = (
            "(disambiguation)" in canonical_title.lower() or
            any("disambiguation" in cat.lower() for cat in categories)
        )

        # Step 2: Query main body links
        links = []
        links_params = {
            "action": "query",
            "titles": canonical_title,
            "prop": "links",
            "plnamespace": 0,
            "pllimit": "max",
            "redirects": 1
        }

        # Fetch up to 1000 links
        max_link_limit = 1000
        while len(links) < max_link_limit:
            link_data = self._get(links_params)
            if not link_data or "query" not in link_data:
                break

            l_pages = link_data["query"].get("pages", [])
            if not l_pages:
                break

            for l in l_pages[0].get("links", []):
                ltitle = l.get("title")
                if ltitle and ":" not in ltitle:
                    links.append(ltitle)

            if "continue" in link_data and len(links) < max_link_limit:
                links_params["plcontinue"] = link_data["continue"].get("plcontinue")
            else:
                break

        # Deduplicate preserving order
        seen = set()
        deduped_links = []
        for l in links:
            if l not in seen and l != canonical_title:
                seen.add(l)
                deduped_links.append(l)

        node = PageNode(
            title=canonical_title,
            url=canonical_url,
            summary=summary,
            links=deduped_links,
            categories=categories,
            out_degree=len(deduped_links),
            is_disambiguation=is_disambig
        )

        if self.config.enable_cache:
            self.cache.set_page(node)

        return node

    def get_batch_summaries(self, titles: List[str]) -> Dict[str, str]:
        """
        Batch retrieves summaries for up to 50 titles in a single network request.
        """
        if not titles:
            return {}

        results = {}
        batch = titles[:self.config.batch_size]
        params = {
            "action": "query",
            "titles": "|".join(batch),
            "prop": "extracts",
            "exintro": 1,
            "explaintext": 1,
            "redirects": 1
        }
        data = self._get(params)
        if data and "query" in data:
            for p in data["query"].get("pages", []):
                t = p.get("title")
                ext = p.get("extract", "")
                if t:
                    results[t] = ext

        return results
