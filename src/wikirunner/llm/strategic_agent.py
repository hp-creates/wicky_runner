"""
Strategic LLM Advisor.
Called ONLY when search encounters a plateau or local maximum trap.
Generates conceptual bridge topics to guide the graph search across domains.
"""

import os
import logging
from typing import List, Set, Optional

from wikirunner.config import RunnerConfig

logger = logging.getLogger("wikirunner.llm")


class StrategicAdvisor:
    def __init__(self, config: RunnerConfig):
        self.config = config
        self._gemini_client = None
        self._groq_client = None

    def _init_gemini(self):
        if self._gemini_client is not None:
            return self._gemini_client
        api_key = self.config.gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self._gemini_client = genai.GenerativeModel(self.config.gemini_model)
            return self._gemini_client
        except Exception as e:
            logger.warning(f"Could not initialize Gemini client: {e}")
            return None

    def _init_groq(self):
        if self._groq_client is not None:
            return self._groq_client
        api_key = self.config.groq_api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            return None
        try:
            from groq import Groq
            self._groq_client = Groq(api_key=api_key)
            return self._groq_client
        except Exception as e:
            logger.warning(f"Could not initialize Groq client: {e}")
            return None

    def get_bridge_topics(
        self,
        start_title: str,
        target_title: str,
        target_summary: str,
        current_title: str,
        path_history: List[str]
    ) -> Set[str]:
        """
        Queries LLM to identify 3-5 bridge Wikipedia page topics that connect the current
        plateau node to the target.
        """
        if not self.config.enable_llm_advisor:
            return set()

        prompt = (
            f"You are an expert Wikipedia Speedrun strategist navigating between articles.\n"
            f"START ARTICLE: {start_title}\n"
            f"TARGET ARTICLE: {target_title}\n"
            f"TARGET CONTEXT: {target_summary[:200]}\n"
            f"CURRENT ARTICLE: {current_title}\n"
            f"RECENT PATH: {' -> '.join(path_history[-4:])}\n\n"
            f"The search is temporarily stuck near '{current_title}'.\n"
            f"List 3 to 5 specific Wikipedia articles or bridge concepts that exist as links "
            f"and can bridge the conceptual gap from '{current_title}' toward '{target_title}'.\n"
            f"Reply ONLY with a comma-separated list of article titles. Do not number or explain."
        )

        # Try Gemini first
        gemini = self._init_gemini()
        if gemini:
            try:
                resp = gemini.generate_content(prompt)
                raw = resp.text.strip()
                topics = {t.strip() for t in raw.split(",") if t.strip()}
                logger.info(f"Strategic LLM (Gemini) suggested bridges: {topics}")
                return topics
            except Exception as e:
                logger.warning(f"Gemini advisor call failed: {e}")

        # Try Groq fallback
        groq = self._init_groq()
        if groq:
            try:
                resp = groq.chat.completions.create(
                    model=self.config.groq_model,
                    messages=[
                        {"role": "system", "content": "You are a Wikipedia navigation expert. Reply with comma-separated article titles."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=50
                )
                raw = resp.choices[0].message.content.strip()
                topics = {t.strip() for t in raw.split(",") if t.strip()}
                logger.info(f"Strategic LLM (Groq) suggested bridges: {topics}")
                return topics
            except Exception as e:
                logger.warning(f"Groq advisor call failed: {e}")

        logger.info("No LLM advisor available or keys not set; continuing with heuristic search.")
        return set()
