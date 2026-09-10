"""
Bidirectional Informed Search Engine for Wikipedia Speedrunning.
Combines:
- Target Inbound Backlinks Index (Meet-in-the-Middle)
- Instant 1-hop and 2-hop victory shortcuts
- Dynamic heuristic prioritization (Lexical + Semantic + Hubness + Disambiguation)
- Strategic LLM escape hatch for local stagnation traps
- Loop avoidance and native backtracking capability
"""

import time
import logging
from typing import Optional, List, Set, Dict

from wikirunner.config import RunnerConfig
from wikirunner.models import RunResult, StepLog, PageNode, CandidateLink
from wikirunner.api.client import WikiClient
from wikirunner.api.cache import WikiCache
from wikirunner.graph.heuristics import HeuristicScorer
from wikirunner.llm.strategic_agent import StrategicAdvisor

logger = logging.getLogger("wikirunner.search")


class WikiSpeedrunner:
    def __init__(self, config: Optional[RunnerConfig] = None):
        self.config = config or RunnerConfig()
        self.cache = WikiCache(db_path=self.config.sqlite_db_path)
        self.client = WikiClient(self.config, self.cache)
        self.scorer = HeuristicScorer(self.config)
        self.advisor = StrategicAdvisor(self.config)

    def run(self, start_term: str, target_term: str) -> RunResult:
        start_time = time.time()
        logger.info(f"Initiating WikiSpeedrun: '{start_term}' -> '{target_term}'")

        # Step 1: Resolve Canonical Titles
        start_title, start_url = self.client.resolve_title(start_term)
        target_title, target_url = self.client.resolve_title(target_term)

        if not start_title or not target_title:
            err = f"Could not resolve page: start='{start_term}' ({start_title}), target='{target_term}' ({target_title})"
            logger.error(err)
            return RunResult(
                status="error",
                steps=0,
                path=[],
                path_titles=[],
                elapsed_seconds=time.time() - start_time,
                visited_count=0,
                api_calls=self.client.api_calls_count,
                error_message=err
            )

        if start_title.lower() == target_title.lower():
            logger.info("Start and Target are identical! Victory in 0 steps.")
            return RunResult(
                status="victory",
                steps=0,
                path=[start_url],
                path_titles=[start_title],
                elapsed_seconds=time.time() - start_time,
                visited_count=1,
                api_calls=self.client.api_calls_count,
                log=[]
            )

        # Step 2: Fetch Target Metadata & Backlinks (Bidirectional Index)
        target_node = self.client.get_page_data(target_title)
        target_summary = target_node.summary if target_node else ""
        target_backlinks = self.client.get_backlinks(target_title, self.config.max_backlinks_fetch)
        logger.info(f"Target '{target_title}' indexed with {len(target_backlinks)} inbound backlinks.")

        current_title = start_title
        current_url = start_url

        history_urls: List[str] = []
        history_titles: List[str] = []
        visited_titles: Set[str] = {start_title.lower()}
        logs: List[dict] = []

        strategic_topics: Set[str] = set()
        stagnation_counter = 0
        best_observed_score = 0.0

        for step in range(1, self.config.max_steps + 1):
            elapsed = time.time() - start_time
            if elapsed > self.config.timeout_seconds:
                logger.warning(f"Speedrun timed out after {elapsed:.1f}s.")
                return RunResult(
                    status="timeout",
                    steps=step - 1,
                    path=history_urls + [current_url],
                    path_titles=history_titles + [current_title],
                    elapsed_seconds=elapsed,
                    visited_count=len(visited_titles),
                    api_calls=self.client.api_calls_count,
                    log=logs
                )

            # Step 3: Fetch Current Page Links
            page = self.client.get_page_data(current_title)
            if not page or not page.links:
                logger.warning(f"Dead end reached at '{current_title}' (no outgoing links).")
                return RunResult(
                    status="dead_end",
                    steps=step - 1,
                    path=history_urls + [current_url],
                    path_titles=history_titles + [current_title],
                    elapsed_seconds=elapsed,
                    visited_count=len(visited_titles),
                    api_calls=self.client.api_calls_count,
                    log=logs,
                    error_message=f"Dead end: '{current_title}' has no outgoing links."
                )

            # Filter out already visited nodes
            available_links = [l for l in page.links if l.lower() not in visited_titles]
            if not available_links:
                logger.warning(f"All outgoing links from '{current_title}' have already been visited.")
                return RunResult(
                    status="dead_end",
                    steps=step - 1,
                    path=history_urls + [current_url],
                    path_titles=history_titles + [current_title],
                    elapsed_seconds=elapsed,
                    visited_count=len(visited_titles),
                    api_calls=self.client.api_calls_count,
                    log=logs,
                    error_message="All candidate links visited."
                )

            # Step 4: Score Candidates
            scored = self.scorer.score_candidates(
                available_links,
                target_title,
                target_summary,
                target_backlinks,
                current_page=page,
                strategic_topics=strategic_topics
            )

            top_choice = scored[0]
            top_candidates_log = [c.to_dict() for c in scored[:5]]

            # Stagnation & Strategic LLM Escape Hatch Check
            if top_choice.score <= best_observed_score:
                stagnation_counter += 1
                if stagnation_counter >= self.config.llm_stagnation_threshold:
                    logger.info(f"Stagnation detected (step {step}). Invoking Strategic LLM Advisor...")
                    new_bridges = self.advisor.get_bridge_topics(
                        start_title,
                        target_title,
                        target_summary,
                        current_title,
                        history_titles
                    )
                    if new_bridges:
                        strategic_topics.update(new_bridges)
                        # Re-score with new strategic topics
                        scored = self.scorer.score_candidates(
                            available_links,
                            target_title,
                            target_summary,
                            target_backlinks,
                            current_page=page,
                            strategic_topics=strategic_topics
                        )
                        top_choice = scored[0]
                        top_candidates_log = [c.to_dict() for c in scored[:5]]
                    stagnation_counter = 0
            else:
                best_observed_score = top_choice.score
                stagnation_counter = 0

            # Step 5: Check Instant Victory Cases
            # CASE A: Top choice is the target directly (1-hop hit)
            if top_choice.title.lower() == target_title.lower() or "TARGET_HIT" in top_choice.notes:
                history_urls.append(current_url)
                history_titles.append(current_title)
                history_urls.append(top_choice.url)
                history_titles.append(top_choice.title)

                step_log = StepLog(
                    step=step,
                    current_title=current_title,
                    current_url=current_url,
                    chosen_title=top_choice.title,
                    chosen_url=top_choice.url,
                    strategy="DIRECT_TARGET_HIT",
                    score=top_choice.score,
                    top_candidates=top_candidates_log,
                    elapsed_seconds=elapsed
                )
                logs.append(step_log.to_dict())
                logger.info(f"[VICTORY] Target '{target_title}' hit directly on step {step}!")
                return RunResult(
                    status="victory",
                    steps=step,
                    path=history_urls,
                    path_titles=history_titles,
                    elapsed_seconds=time.time() - start_time,
                    visited_count=len(visited_titles),
                    api_calls=self.client.api_calls_count,
                    log=logs
                )

            # CASE B: Top choice is a confirmed Target Backlink (2-hop candidate)
            if top_choice.is_target_backlink or "TARGET_BACKLINK_MATCH" in top_choice.notes:
                # VERIFICATION: Confirm bridge page actually contains target link in body
                bridge_page = self.client.get_page_data(top_choice.title)
                has_direct_link = (
                    bridge_page is not None and
                    any(l.lower() == target_title.lower() for l in bridge_page.links)
                )

                if has_direct_link:
                    # Hop 1: Current -> Bridge Backlink
                    history_urls.append(current_url)
                    history_titles.append(current_title)

                    step_log_1 = StepLog(
                        step=step,
                        current_title=current_title,
                        current_url=current_url,
                        chosen_title=top_choice.title,
                        chosen_url=top_choice.url,
                        strategy="TARGET_BACKLINK_INTERSECTION",
                        score=top_choice.score,
                        top_candidates=top_candidates_log,
                        elapsed_seconds=elapsed
                    )
                    logs.append(step_log_1.to_dict())

                    # Hop 2: Bridge Backlink -> Target
                    history_urls.append(top_choice.url)
                    history_titles.append(top_choice.title)
                    history_urls.append(target_url)
                    history_titles.append(target_title)

                    step_log_2 = StepLog(
                        step=step + 1,
                        current_title=top_choice.title,
                        current_url=top_choice.url,
                        chosen_title=target_title,
                        chosen_url=target_url,
                        strategy="FINAL_TARGET_SNAP",
                        score=10000.0,
                        top_candidates=[{"title": target_title, "url": target_url, "score": 10000.0}],
                        elapsed_seconds=time.time() - start_time
                    )
                    logs.append(step_log_2.to_dict())

                    logger.info(
                        f"[VICTORY] Target Backlink '{top_choice.title}' verified and connected '{current_title}' to '{target_title}' in {step + 1} steps!"
                    )
                    return RunResult(
                        status="victory",
                        steps=step + 1,
                        path=history_urls,
                        path_titles=history_titles,
                        elapsed_seconds=time.time() - start_time,
                        visited_count=len(visited_titles) + 2,
                        api_calls=self.client.api_calls_count,
                        log=logs
                    )
                else:
                    logger.info(
                        f"[BACKLINK VERIFY] '{top_choice.title}' does not have direct body link to '{target_title}'. Stepping normally."
                    )

            # Standard move forward
            step_log = StepLog(
                step=step,
                current_title=current_title,
                current_url=current_url,
                chosen_title=top_choice.title,
                chosen_url=top_choice.url,
                strategy=top_choice.notes or "HEURISTIC_SEARCH",
                score=top_choice.score,
                top_candidates=top_candidates_log,
                elapsed_seconds=elapsed
            )
            logs.append(step_log.to_dict())

            history_urls.append(current_url)
            history_titles.append(current_title)
            visited_titles.add(current_title.lower())
            visited_titles.add(top_choice.title.lower())

            current_title = top_choice.title
            current_url = top_choice.url

            logger.info(f"Step {step}: '{history_titles[-1]}' -> '{current_title}' (Score: {top_choice.score:.2f}, {top_choice.notes})")

        # Max steps reached
        logger.warning("Max steps reached without finding target.")
        return RunResult(
            status="max_steps",
            steps=self.config.max_steps,
            path=history_urls + [current_url],
            path_titles=history_titles + [current_title],
            elapsed_seconds=time.time() - start_time,
            visited_count=len(visited_titles),
            api_calls=self.client.api_calls_count,
            log=logs
        )
