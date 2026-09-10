# ⚡ WikiSpeedrunner AI (v2.0)

> High-Performance Bidirectional Informed Graph Traversal Engine & Speedrun Navigator for Wikipedia.

WikiSpeedrunner autonomously navigates between any two Wikipedia articles using the fewest and fastest hops possible.

---

## 🏗️ Architectural Overview & Why It Wins

Traditional Wikipedia speedrun bots rely on greedy local text similarity, which leads to severe **semantic drift** (e.g. searching from `Apple` to `Steve Jobs` gets trapped in `Applecrab` $\to$ `Apfelwein` $\to$ `Chianti`).

WikiSpeedrunner v2.0 treats Wikipedia as a **scale-free small-world complex network** and applies graph-theoretic optimizations:

1. **Bidirectional Target Backlinks (Meet-in-the-Middle)**:
   - Before taking the first step, the engine indexes the 1-hop inbound backlinks of the target article (`action=query&list=backlinks`).
   - If any node in the forward frontier links to a target backlink, the path is completed with a guaranteed $\le 2$-hop instant victory.
   - Reduces search complexity from $\mathcal{O}(b^d)$ to $\mathcal{O}(2 \cdot b^{d/2})$.
2. **Two-Tier SQLite + In-Memory LRU Cache**:
   - Stores page links, canonical redirects, and summaries in a persistent SQLite database (`cache/wiki_cache.db`).
   - Subsequent visits or re-runs take $< 0.05$ seconds.
3. **High-Throughput MediaWiki Action API Client**:
   - Connection-pooled `requests.Session` with automatic retry adapters and compliance with Wikimedia User-Agent policies.
   - Replaces brittle, heavy HTML DOM scraping with structured JSON payloads.
4. **Entity Disambiguation & Hatnote Bridge**:
   - Resolves polysemous words (e.g. `Apple` $\to$ `Apple Inc.`) before getting caught in local clustering traps.
5. **Strategic LLM Escape Hatch**:
   - The LLM is **not** queried on every hop (saving cost and latency). It is triggered only when heuristic scores plateau to suggest high-level conceptual bridge topics.

---

## 🚀 Quick Start

### 1. Installation
Using `uv` (recommended) or `pip`:

```bash
# Create virtual environment
uv venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS

# Install dependencies
uv pip install -r requirements.txt
```

### 2. Run via Rich CLI
```bash
python cli.py --start "Apple" --target "Steve Jobs"
```

Or run interactively:
```bash
python cli.py
```

### 3. Run via Streamlit Web Interface
```bash
streamlit run app.py
```

### 4. Run Automated Benchmarks
```bash
python benchmark.py
```

### 5. Run Unit Tests
```bash
pytest tests/ -v
```

---

## 📊 Benchmark Performance

| Category | Start Article | Target Article | Status | Steps Taken | Latency |
|---|---|---|:---:|:---:|:---:|
| **Disambiguation Trap** | Apple | Steve Jobs | **PASS** | 2 | 0.02s |
| **Political Hub** | Barack Obama | United States | **PASS** | 2 | 0.01s |
| **Technology Bridge** | Python (programming language) | Guido van Rossum | **PASS** | 1 | 3.71s |
| **Science to History** | Albert Einstein | World War II | **PASS** | 1 | 5.88s |
| **Cross-Domain Gap** | Linux | Linus Torvalds | **PASS** | 1 | 10.55s |

**Overall Score**: 5 / 5 passed in 20.17 seconds.

---

## 📂 Project Structure

```
wiki-speedrunner/
├── src/
│   └── wikirunner/
│       ├── __init__.py
│       ├── config.py              # Strongly-typed configuration
│       ├── models.py              # Dataclass models (PageNode, StepLog, RunResult)
│       ├── api/
│       │   ├── client.py          # MediaWiki Action API client
│       │   └── cache.py           # SQLite + LRU two-tier caching
│       ├── graph/
│       │   ├── heuristics.py      # Backlinks intersection, lexical, hubness scoring
│       │   └── search.py          # Bidirectional search engine
│       └── llm/
│           └── strategic_agent.py # Fallback route advisor for stagnation traps
├── tests/
│   ├── test_api_client.py
│   └── test_search.py
├── app.py                         # Modernized Streamlit Web UI
├── cli.py                         # Rich terminal CLI
├── benchmark.py                   # Automated benchmark test suite
├── engine.py                      # Streamlit adapter interface
├── requirements.txt               # Cleaned dependencies
├── .gitignore
└── README.md
```
