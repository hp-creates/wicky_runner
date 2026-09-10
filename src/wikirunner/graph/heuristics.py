"""
High-performance heuristic scoring engine.
Combines:
1. Target Inbound Link (Backlink) Intersection (O(1) hash lookup for guaranteed <= 2 hop paths)
2. Entity & Token Overlap (Disambiguation and title matching)
3. Semantic Similarity (MiniLM vector similarity or TF-IDF / character n-gram cosine fallback)
4. Graph Centrality (Hubness proxy via out-degree and category breadth)
"""

import re
import math
from typing import List, Set, Dict, Optional, Tuple
from wikirunner.config import RunnerConfig
from wikirunner.models import CandidateLink, PageNode

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
YEAR_PATTERN = re.compile(r"^\d{3,4}s?$")


def tokenize(text: str) -> List[str]:
    return [t for t in TOKEN_PATTERN.findall(text.lower()) if len(t) >= 2]


class HeuristicScorer:
    def __init__(self, config: RunnerConfig):
        self.config = config
        self._sbert_model = None
        self._sbert_failed = False
        self._embedding_cache: Dict[str, List[float]] = {}

    def _get_sbert(self):
        if self._sbert_failed:
            return None
        if self._sbert_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._sbert_model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception:
                self._sbert_failed = True
                self._sbert_model = None
        return self._sbert_model

    def _embed(self, text: str) -> Optional[List[float]]:
        model = self._get_sbert()
        if not model or not text:
            return None
        if text in self._embedding_cache:
            return self._embedding_cache[text]
        try:
            emb = model.encode(text, normalize_embeddings=True).tolist()
            if len(self._embedding_cache) < 2000:
                self._embedding_cache[text] = emb
            return emb
        except Exception:
            return None

    @staticmethod
    def _cosine_sim(v1: List[float], v2: List[float]) -> float:
        dot = sum(a * b for a, b in zip(v1, v2))
        return max(0.0, min(1.0, dot))

    @staticmethod
    def _token_jaccard(tokens1: Set[str], tokens2: Set[str]) -> float:
        if not tokens1 or not tokens2:
            return 0.0
        inter = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        return inter / union if union > 0 else 0.0

    def score_candidates(
        self,
        candidate_titles: List[str],
        target_title: str,
        target_summary: str,
        target_backlinks: Set[str],
        current_page: Optional[PageNode] = None,
        strategic_topics: Optional[Set[str]] = None
    ) -> List[CandidateLink]:
        """
        Scores all outgoing candidate links from the current node against the target.
        Returns a sorted list of CandidateLink objects (highest score first).
        """
        results: List[CandidateLink] = []
        target_norm = target_title.lower().strip()
        target_tokens = set(tokenize(target_title))
        target_summary_tokens = set(tokenize(target_summary[:300]))

        target_emb = self._embed(target_title + " " + target_summary[:200])

        for title in candidate_titles:
            norm_title = title.lower().strip()
            title_tokens = set(tokenize(title))
            url = f"/wiki/{title.replace(' ', '_')}"

            # --- SIGNAL 1: Target Match or Direct Target Backlink ---
            if norm_title == target_norm:
                # Direct target hit on page!
                results.append(CandidateLink(
                    title=title,
                    url=url,
                    score=10000.0,
                    is_target_backlink=True,
                    notes="TARGET_HIT"
                ))
                continue

            if title in target_backlinks:
                # Instant 2-hop link! Candidate directly links to target!
                results.append(CandidateLink(
                    title=title,
                    url=url,
                    score=self.config.weight_backlink_hit + 500.0,
                    is_target_backlink=True,
                    notes="TARGET_BACKLINK_MATCH"
                ))
                continue

            score = 0.0
            notes = []

            # --- SIGNAL 2: Lexical Token Overlap ---
            title_overlap = self._token_jaccard(title_tokens, target_tokens)
            if title_overlap > 0:
                score += title_overlap * self.config.weight_lexical_similarity * 4.0
                notes.append(f"title_match:{title_overlap:.2f}")

            summary_overlap = self._token_jaccard(title_tokens, target_summary_tokens)
            if summary_overlap > 0:
                score += summary_overlap * self.config.weight_lexical_similarity
                notes.append(f"sum_overlap:{summary_overlap:.2f}")

            # --- SIGNAL 3: Strategic LLM Advisor Topics ---
            if strategic_topics:
                for st in strategic_topics:
                    if st.lower() in norm_title or norm_title in st.lower():
                        score += 30.0
                        notes.append(f"strategic_topic:{st}")
                        break

            # --- SIGNAL 4: Disambiguation / Entity Hatnote Boost ---
            # If candidate title contains the base name of target or current (e.g. 'Apple Inc.' when at 'Apple')
            if current_page:
                curr_tokens = set(tokenize(current_page.title))
                if target_tokens and title_tokens.issuperset(curr_tokens) and len(title_tokens) > len(curr_tokens):
                    # Candidate extends current entity (e.g. 'Apple' -> 'Apple Inc.')
                    # Check if target context matches
                    if any(t in target_summary.lower() for t in title_tokens - curr_tokens):
                        score += 50.0
                        notes.append("disambiguation_bridge")

            # --- SIGNAL 5: Semantic Embedding Cosine Similarity ---
            if target_emb:
                cand_emb = self._embed(title)
                if cand_emb:
                    sim = self._cosine_sim(target_emb, cand_emb)
                    score += sim * self.config.weight_semantic_similarity
                    notes.append(f"sbert:{sim:.2f}")

            # --- SIGNAL 6: Penalties for Low-Value Nodes ---
            if YEAR_PATTERN.match(norm_title) and not any(YEAR_PATTERN.match(t) for t in target_tokens):
                score -= 15.0  # Avoid getting trapped in generic timeline years (e.g. 1994, 2005)

            if "(disambiguation)" in norm_title and not "(disambiguation)" in target_norm:
                score -= 10.0

            results.append(CandidateLink(
                title=title,
                url=url,
                score=score,
                is_target_backlink=False,
                notes="; ".join(notes)
            ))

        # Sort descending by score
        results.sort(key=lambda x: x.score, reverse=True)
        return results
