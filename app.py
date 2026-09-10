"""
Streamlit Web Application for WikiRunner AI (v2.0)
High-Performance Bidirectional Wikipedia Speedrun Navigator.
"""

import sys
import os
import time
import streamlit as st

# Ensure src is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from wikirunner import WikiSpeedrunner, RunnerConfig

st.set_page_config(
    page_title="WikiSpeedrunner AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #1e1e2e;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #313244;
    }
    .path-step {
        display: inline-block;
        background-color: #313244;
        color: #cdd6f4;
        padding: 5px 12px;
        border-radius: 15px;
        margin: 4px;
        font-weight: 500;
    }
    .path-arrow {
        color: #89b4fa;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ WikiSpeedrunner AI")
st.caption("Bidirectional Informed Graph Traversal & Autonomous Speedrunner")

with st.sidebar:
    st.header("⚙️ Game Controls")
    start = st.text_input("Start Article", "Apple", help="Title of origin Wikipedia page")
    target = st.text_input("Target Article", "Steve Jobs", help="Title of destination Wikipedia page")

    st.markdown("---")
    st.subheader("🤖 AI Advisor")
    enable_llm = st.toggle(
        "Enable Strategic AI Advisor",
        value=False,
        help="Use Gemini / Groq as a fallback if search encounters a local plateau. Requires a valid API key."
    )

    gemini_key_override = ""
    if enable_llm:
        gemini_key_override = st.text_input(
            "Gemini API Key (optional override)",
            type="password",
            help="Paste a valid Gemini key here to override .env"
        )
        has_env_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY"))
        if not gemini_key_override and not has_env_key:
            st.warning("⚠️ No API key found. Turn off advisor or provide a key.")

    st.markdown("---")
    run_btn = st.button("🚀 Run Speedrunner", use_container_width=True, type="primary")

    st.markdown("---")
    st.markdown("""
    **Architecture Pillars:**
    - 🔄 **Bidirectional Target Backlinks**: Cuts graph search depth in half.
    - ⚡ **Two-Tier SQLite Cache**: Sub-millisecond retrieval on repeat visits.
    - 🌐 **MediaWiki Action API**: Clean structured payloads, no brittle DOM scraping.
    - 🧠 **Strategic AI Advisor**: Optional escape hatch if search enters stagnation.
    """)

if run_btn:
    if not start or not target:
        st.error("Please provide both a Start and a Target article.")
    else:
        # Build config dynamically based on sidebar toggle
        active_gemini_key = gemini_key_override.strip() if gemini_key_override.strip() else os.getenv("GEMINI_API_KEY", "")
        cfg = RunnerConfig(
            enable_llm_advisor=enable_llm,
            gemini_api_key=active_gemini_key
        )
        runner = WikiSpeedrunner(cfg)

        with st.spinner(f"Navigating Wikipedia from '{start}' to '{target}'..."):
            t0 = time.time()
            result = runner.run(start, target)
            elapsed = time.time() - t0

        status = result.status.upper()
        is_victory = (status == "VICTORY")

        # Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Status", "🏆 " + status if is_victory else "❌ " + status)
        with col2:
            st.metric("Steps Taken", result.steps)
        with col3:
            st.metric("Elapsed Time", f"{result.elapsed_seconds:.2f}s")
        with col4:
            st.metric("API Requests", result.api_calls)

        st.markdown("---")

        # Path Display
        st.subheader("🏁 Traversed Path")
        path = result.path_titles if result.path_titles else result.path
        if path:
            st.markdown(
                " " + " ➜ ".join([f"`{node}`" for node in path]) + " "
            )

        st.markdown("---")

        # Detailed Step Log
        st.subheader("📋 Step-by-Step Decision Log")
        for entry in result.log:
            step_num = entry.get("step", 1)
            curr = entry.get("current_title", "")
            chosen = entry.get("chosen_title", "")
            strat = entry.get("strategy", "")
            score = entry.get("score", 0.0)

            with st.expander(f"Step {step_num}: **{curr}** ➜ **{chosen}** ({strat})", expanded=(step_num <= 3)):
                st.write(f"**Strategy / Reason:** `{strat}` (Heuristic Score: `{score:.2f}`)")

                top_cands = entry.get("top_candidates", [])
                if top_cands:
                    st.write(f"**Top Evaluated Candidates:**")
                    st.write(", ".join([f"`{c.get('title')}`" for c in top_cands[:8]]))

                    st.markdown("**Detailed Ranking Scores:**")
                    for c in top_cands[:5]:
                        st.markdown(f"- **{c.get('title')}**: Score `{c.get('score', 0):.2f}` ({c.get('notes', '')})")

else:
    st.info("👈 Enter a Start and Target article in the sidebar and click **Run Speedrunner** to start!")
