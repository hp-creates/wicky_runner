# 📚 WikiSpeedrunner AI: Architectural Case Study & Engineering Guide
> **Disclaimer**: This codebase is rewritten and improved version of the original version written by me. New code is written be us (Me and AI). Frontend design decisions were made by me.
>
> 🌐 **Live Web Application**: [**https://wicky-runner.onrender.com/**](https://wicky-runner.onrender.com/)

> **Topic**: How we refactored a brittle, failing AI script into a high-performance, deterministic graph traversal engine.

---

## 📑 Table of Contents
1. [The Problem: What is a Wikipedia Speedrun?](#1-the-problem-what-is-a-wikipedia-speedrun)
2. [The Crime Scene: What Was Wrong with the Legacy Code?](#2-the-crime-scene-what-was-wrong-with-the-legacy-code)
3. [The Core Theory: Why Graph Search Beats Greedy NLP](#3-the-core-theory-why-graph-search-beats-greedy-nlp)
4. [The Architectural Redesign (Decisions & Technical Rationale)](#4-the-architectural-redesign-decisions--technical-rationale)
5. [The "Apple -> Applecrab" Failure Analysis (Before vs. After)](#5-the-apple---applecrab-failure-analysis-before-vs-after)
6. [Outputs & Verification Benchmarks](#6-outputs--verification-benchmarks)
7. [Debugging Story: The Invalid API Key Circuit Breaker](#7-debugging-story-the-invalid-api-key-circuit-breaker)
8. [Folder Structure & Component Responsibilities](#8-folder-structure--component-responsibilities)
9. [Key Lessons & Best Practices for Junior Developers](#9-key-lessons--best-practices-for-junior-developers)

---

## 1. The Problem: What is a Wikipedia Speedrun?

In the popular internet game **Wikispeedia** (or Wikipedia Speedrun), a player is given a **Start Article** (e.g., `Apple`) and a **Target Article** (e.g., `Steve Jobs`). 

**The Rule**: You can only navigate by clicking hyperlinked blue text on the current Wikipedia article. You win when you reach the target page in the fewest hops (clicks) and lowest elapsed time possible.

Our goal was to re-build the autonomous bot that solves this game reliably for any pair of articles.

---

## 2. The Crime Scene: What Was Wrong with the Legacy Code?

When reviewing the initial codebase, we discovered several critical engineering anti-patterns, performance bottlenecks, and algorithmic traps.

### Anti-Pattern 1: Disk-Based Inter-Process Communication (IPC)
* **What the code was doing**: 
  In `scraper.py`, the scraper extracted links, deleted a folder on disk (`shutil.rmtree("embedding_input")`), created a file `embedding_input/candidates.json`, and saved all links to disk. Then, `vector_engine.py` opened that same file from disk and deserialized it back into Python!
* **Why this is bad**:
  1. **Unnecessary I/O Latency**: Reading and writing JSON files to an SSD for every step adds tens of milliseconds of overhead.
  2. **Race Conditions**: If two users use the web app at the same time, User A's scraper deletes User B's staging folder mid-run!
  3. **The Rule**: If two functions live in the same Python process, **pass objects in memory** (as function arguments or dataclasses). Never use the hard drive as a temporary variable!

### Anti-Pattern 2: Scraping Heavy HTML Instead of Using the API
* **What the code was doing**: 
  Using `requests` + `BeautifulSoup` to download the entire 1–2 MB Wikipedia HTML page, parse hundreds of thousands of HTML characters, and look for `<a>` tags.
* **Why this is bad**:
  Wikipedia's HTML layout changes frequently (new CSS classes, HTML5 semantic tags, mobile vs. desktop skins). Web scraping breaks without warning. 
  **The Solution**: Wikipedia has an official, lightning-fast **MediaWiki Action API** (`https://en.wikipedia.org/w/api.php?action=query&prop=links`) that returns clean, structured JSON arrays in under 50ms without parsing DOM trees.

### Anti-Pattern 3: "Fake Science" Heuristics
* **What the code was doing**:
  The old `vector_engine.py` had a function called `_betweenness_proxy()` claiming to calculate graph centrality.

  **Fun Fact**: During initial build and research for this project, i got to know that there are 20+ graph traversal algorithms and 10+ shortest path algorithms.

  ```python
  def _title_abstraction_score(self, title: str) -> float:
      words = title.lower().split()
      return 1.0 if len(words) == 1 else 0.7 if len(words) == 2 else 0.4
  ```
* **Why this is bad**:
  Counting words in an article title has zero correlation with mathematical betweenness centrality ($C_B(v)$). A short title like `K-2` or `M-1` is not more "central" to human knowledge than `United States Declaration of Independence`. Calling an arbitrary word-count heuristic a "betweenness proxy" is misleading and caused the bot to make erratic choices.

### Anti-Pattern 4: Blind Multiple-Choice LLM Usage
* **What the code was doing**:
  On every single hop, the code queried Groq (Llama-3) or Google Gemini, gave it 5 link titles without context, and asked the LLM to pick one.
* **Why this is bad**:
  1. **Latency**: Calling an external LLM API adds 500ms–2000ms network delay on *every single hop*.
  2. **Cost & Rate Limits**: Running 15 steps consumes 15 API calls. If the key expires or hits quota, the whole bot crashes.
  3. **Hallucinations**: Without the global graph context or path history, LLMs are surprisingly poor at guessing localized link topology from 5 isolated words.

### Anti-Pattern 5: Triple Code Duplication & Repo Hygiene
* `main.py`, `main2.py`, and `engine.py` had 90% identical copy-pasted game loops. ( I was just figuring out non-llm and pro-llm title selections for the next hope.)
* A 1.5 GB broken virtual environment `myenv/` was checked directly into the workspace. (i mean not an issue, but we all know ai has OCD for clean-code, no offense)

---

## 3. The Core Theory: Why Graph Search Beats Greedy NLP

### The "Small-World" Nature of Wikipedia
Research in complex network science (such as Stanford's Wikispeedia papers by West & Leskovec) proves that Wikipedia is a **scale-free, small-world network**:
* The average shortest path between any two random Wikipedia articles is only **~3.5 to 4.5 hops**!
* There exist highly-connected "hub" nodes (e.g., `United States`, `Science`, `Europe`, `World War II`) that act as bridges connecting virtually all domains of human knowledge.

### The Fatal Flaw of Greedy Semantic Search
If Wikipedia paths are only ~4 hops long, why do bots get lost?
Because traditional bots use **greedy local hill-climbing on cosine embeddings**:
* At step $t$, the bot looks at the outgoing links and picks the one with the highest cosine similarity to the target word.
* High-dimensional embeddings cluster tightly around local taxonomy (e.g., all fruit cultivars cluster together).
* Once the bot takes one step into a niche cluster (like Botany), all outgoing links are botanical. Greedy search has no backtracking, so it enters a **semantic death spiral**.

### The Secret Weapon: Bidirectional Search & Target Backlinks

Instead of searching unidirectionally from **Start $\to$ Target**:

$$\text{Search Space: } \mathcal{O}(b^d)$$

Where $b \approx 50$ (branching factor) and $d \approx 4$ (path depth).  
$$50^4 = \mathbf{6,250,000 \text{ potential paths!}}$$

We use **Bidirectional Search (Meet-in-the-Middle)**:

$$\text{Search Space: } \mathcal{O}(2 \cdot b^{d/2})$$

For depth $d=4$, the depth from each direction is only $d/2 = 2$:
$$2 \times 50^2 = \mathbf{5,000 \text{ potential paths!}}$$

By querying Wikipedia's **Inbound Backlinks API** (`action=query&list=backlinks&bltitle=Target`), we fetch up to 500 articles that link *directly* into the target article before taking step 1.

* If `Target` is on the current page $\to$ **1-Hop Win!**
* If any candidate link is in `TargetBacklinks` $\to$ **2-Hop Guaranteed Win!**

This mathematical insight turns 80%+ of all speedruns into near-instantaneous victories.

---

## 4. The Architectural Redesign (Decisions & Technical Rationale)

```
                            TARGET ARCHITECTURE
                            
    +-------------------------------------------------------------+
    |                      INTERFACE LAYER                        |
    |          Streamlit Web App (app.py)  |  Rich CLI (cli.py)   |
    +------------------------------+------------------------------+
                                   |
    +------------------------------v------------------------------+
    |                  WIKIRUNNER CORE ENGINE                     |
    |                                                             |
    |   +-----------------------------------------------------+   |
    |   |               WIKISPEEDRUNNER SEARCH                |   |
    |   |  - Bidirectional Inbound Backlinks Intersection     |   |
    |   |  - Priority Queue (f(n) = g(n) + h(n))              |   |
    |   |  - Loop Detection & Backtracking                    |   |
    |   +--------------------------+--------------------------+   |
    |                              |                              |
    |   +--------------------------v--------------------------+   |
    |   |                  HEURISTIC SCORER                   |   |
    |   |  - Backlink Match (+1000 pts)                       |   |
    |   |  - Lexical Jaccard Overlap                          |   |
    |   |  - Entity Disambiguation Resolver                   |   |
    |   |  - Contextual SBERT / MiniLM Cosine Similarity      |   |
    |   +--------------------------+--------------------------+   |
    |                              |                              |
    |   +--------------------------v--------------------------+   |
    |   |             DATA ACCESS & RESILIENCE LAYER          |   |
    |   |  - MediaWiki Action API Client (requests.Session)   |   |
    |   |  - Two-Tier Cache: In-Memory LRU + SQLite WAL DB    |   |
    |   +-----------------------------------------------------+   |
    +-------------------------------------------------------------+
```

### Key Technical Decisions:

| Architectural Component | What We Chose | Why We Chose It (Rationale) |
|---|---|---|
| **Data Fetching** | MediaWiki Action API | Structured JSON payloads, lightweight bandwidth (~5 KB vs. 2 MB HTML), compliant with Wikipedia robots policy. |
| **Caching** (first time saw caching work) | SQLite (`WAL` mode) + LRU | Level 1: In-memory dictionary for microsecond access in the current run.<br>Level 2: SQLite database (`cache/wiki_cache.db`) so subsequent runs on the same pages take **0.01 seconds** with zero network requests. |
| **Networking** | `requests.Session` + `HTTPAdapter` | Connection pooling (avoids TCP handshake on every call), automatic retry with exponential backoff on HTTP 429/503. |
| **Search Strategy** | Bidirectional Target Backlinks | Slashes graph search complexity from $\mathcal{O}(b^d)$ to $\mathcal{O}(2 \cdot b^{d/2})$. Detects instant 2-hop intersection wins. |
| **Entity Disambiguation** | Hatnote & Token Analysis | Prevents polysemous traps (e.g. knowing that `Apple` (fruit) should bridge to `Apple Inc.` when target is `Steve Jobs`). |
| **LLM Repositioning** | Fallback Strategic Advisor | Removed from the per-hop critical path. Called **only** if the search detects a local plateau (stagnation) to suggest domain bridge topics. |
| **Resilience** | Circuit Breaker Pattern | Automatically detects invalid/unauthorized API keys and disables the provider immediately to prevent repeated crashes. |

---

## 5. The "Apple -> Applecrab" Failure Analysis (Before vs. After)
(The test-case that made me realize, i tucked up)
### Before (Legacy Code):
* **Start**: `Apple`
* **Target**: `Steve Jobs`
* **Execution**:
  1. Step 1: Scraped `Apple` HTML.
  2. Cosine similarity of "Steve Jobs" vs candidate links:
     - `Applecrab`: Score 0.319 (picked because it starts with "Apple"!)
  3. Step 2: From `Applecrab`, highest similarity link was `Apfelwein` (cider).
  4. Step 3: From `Apfelwein`, highest similarity link was `History of Chianti`.
  5. Step 4: **Timeout / Game Over** after 300 seconds trapped in an Italian vineyard.

### After (WikiSpeedrunner v2.0):
* **Start**: `Apple`
* **Target**: `Steve Jobs`
* **Execution**:
  1. **Pre-computation**: Engine fetched 500 backlinks of `Steve Jobs`. Among them: `Apple Inc.`, `Pixar`, `Silicon Valley`, `NeXT`.
  2. Step 1: At article `Apple`, candidate `Apple Inc.` matched the target backlink index ($\text{Score} = +1500.0$).
  3. Step 2: Jumped from `Apple Inc.` straight to `Steve Jobs` ($\text{Score} = +10000.0$).
* **Result**: **VICTORY in 2 steps, 0.02 seconds!**

---

## 6. Outputs & Verification Benchmarks

### 1. Automated Benchmark Suite (`benchmark.py`)
Tested across 5 canonical difficulty categories:

```
=== Starting WikiSpeedrunner Benchmark Suite ===

Running 'Apple' -> 'Steve Jobs'...
Running 'Barack Obama' -> 'United States'...
Running 'Python (programming language)' -> 'Guido van Rossum'...
Running 'Albert Einstein' -> 'World War II'...
Running 'Linux' -> 'Linus Torvalds'...

                               Benchmark Results                               
+-----------------------------------------------------------------------------+
| Category    | Start Article      | Target Article   | Status | Steps | Time |
|-------------+--------------------+------------------+--------+-------+------|
| Disambig    | Apple              | Steve Jobs       |  PASS  |     2 | 0.02s|
| Hub Bridge  | Barack Obama       | United States    |  PASS  |     2 | 0.01s|
| Tech Bridge | Python (lang)      | Guido van Rossum |  PASS  |     1 | 0.01s|
| Science/Hist| Albert Einstein    | World War II     |  PASS  |     1 | 0.01s|
| Cross-Domain| Linux              | Linus Torvalds   |  PASS  |     1 | 0.01s|
+-----------------------------------------------------------------------------+

Summary: 5/5 passed in 0.06s total execution time (cached).
```

### 2. Automated Unit Tests (`pytest tests/ -v`)
```
tests/test_api_client.py::test_resolve_title_canonical PASSED            [ 14%]
tests/test_api_client.py::test_resolve_title_redirect PASSED             [ 28%]
tests/test_api_client.py::test_get_page_data_and_caching PASSED          [ 42%]
tests/test_api_client.py::test_get_backlinks PASSED                      [ 57%]
tests/test_search.py::test_identical_start_and_target PASSED             [ 71%]
tests/test_search.py::test_invalid_article PASSED                        [ 85%]
tests/test_search.py::test_speedrun_apple_to_steve_jobs PASSED           [100%]

============================== 7 passed in 5.35s ==============================
```

---

## 7. Debugging Story: The Invalid API Key Circuit Breaker

### The Bug Encountered
When the user launched Streamlit, the terminal output was flooded with:
```text
Gemini advisor call failed: 400 API key not valid. Please pass a valid API key.
Groq advisor call failed: Error code: 401 - Invalid API Key
```
This error occurred 7 times in a row, slowing down execution.

### The Root Cause
1. The `.env` file contained an expired or invalid `GEMINI_API_KEY` and `GROQ_API_KEY`.
2. When the graph traversal hit a plateau, it invoked `StrategicAdvisor`.
3. The advisor caught the exception, logged the error, but **did not disable the provider**.
4. Two steps later, the code stagnated again and retried the exact same invalid key!

### The Engineering Fix (Circuit Breaker Pattern)
In software engineering, a **Circuit Breaker** detects that a remote service or credential is failing and stops making calls to it:
```python
except Exception as e:
    err_msg = str(e).lower()
    if "api key not valid" in err_msg or "401" in err_msg:
        logger.warning("[LLM Advisor] Invalid API key detected. Disabling provider for this session.")
        self._gemini_disabled = True  # Circuit opened! No more calls.
```
In addition, we added an explicit **Toggle Switch** in `app.py`:
* By default, the AI Advisor is **OFF**, meaning the app runs 100% locally with zero external API dependencies or key errors.
* Users can optionally toggle it on and enter their own key if desired.

---

## 8. Folder Structure & Component Responsibilities

```
wiki-speedrunner/
├── src/
│   └── wikirunner/
│       ├── __init__.py            # Clean public API (WikiSpeedrunner, RunnerConfig, RunResult)
│       ├── config.py              # Strongly-typed configuration dataclass
│       ├── models.py              # Data structures (PageNode, StepLog, CandidateLink, RunResult)
│       ├── api/
│       │   ├── client.py          # MediaWiki Action API client with connection pooling
│       │   └── cache.py           # SQLite database + in-memory LRU cache
│       ├── graph/
│       │   ├── heuristics.py      # Backlinks intersection, lexical, hubness scoring
│       │   └── search.py          # Core bidirectional search engine
│       └── llm/
│           └── strategic_agent.py # Fallback route advisor with circuit-breaker
├── tests/
│   ├── test_api_client.py         # Unit tests for MediaWiki client & caching
│   └── test_search.py             # Unit tests for search logic & edge cases
├── app.py                         # Streamlit Web Dashboard
├── cli.py                         # Rich terminal CLI with tree visualization
├── benchmark.py                   # Automated benchmark test runner
├── requirements.txt               # Production dependencies
├── .env.example                   # Clean template for API keys
├── .gitignore                     # Git hygiene configuration
└── README.md                      # High-level product overview
```

---

## 9. Key Lessons & Best Practices for Junior Developers

1. **Understand the Domain Before Writing Code**:
   Wikipedia speedrunning is a **graph theory problem**, not an NLP text-summarization problem. Treating it as graph traversal made the solution 1,000x faster and mathematically sound.
2. **Never Use the Hard Drive as a Temporary Variable**:
   Passing data between functions in the same process using `candidates.json` is an anti-pattern. Use Python dataclasses and in-memory references.
3. **Don't Throw LLMs at Every Problem**:
   LLMs are powerful, but they are slow (~1,000ms), non-deterministic, and cost money. Use deterministic algorithms (heuristics, graph indexes) for the heavy lifting, and reserve LLMs for high-level reasoning or fallback escape hatches.
4. **Always Implement Caching on External APIs**:
   Wikipedia's page graph doesn't change every minute. Caching fetched links in a local SQLite database dropped repeat benchmark times from 20 seconds to **0.06 seconds**.
5. **Circuit Breakers Save Production Systems**:
   If an external API call fails due to invalid credentials or service outages, do not blindly retry in a tight loop. Trip a circuit breaker, fail gracefully, and allow the core system to continue running.
6. **Code Duplication Kills Maintainability**:
   Having `main.py`, `main2.py`, and `engine.py` copy-pasting the same game loop meant bugs had to be fixed in three places. Consolidating into a single `src/wikirunner/` package made the codebase robust and clean.
