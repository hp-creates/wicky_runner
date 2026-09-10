# ⚡ WikiSpeedrunner AI (v2.1)

> High-Performance Bidirectional Informed Graph Traversal Engine & Wikipedia Route Navigator.
> Autonomously discovers the shortest, fastest acyclic path between any two Wikipedia articles using graph heuristics, backlinks intersection, and optional LLM guidance.

> 📖 **Engineering Retrospective**: Read the in-depth architectural breakdown, refactoring lessons, and algorithmic proofs in [**ARCHITECTURE_CASE_STUDY.md**](ARCHITECTURE_CASE_STUDY.md).

---

## 🌟 Key Features

- **Authentic Wikipedia Vector UI**: Styled after English Wikipedia's official Vector interface with search inputs, collapsible sidebar, table of contents, verified hyperlink tables, and summary Infobox.
- **Litmaps Constellation Graph**: Minimalist, high-contrast topological canvas rendering floating nodes, geometric directed edges, traveling energy pulses, and candidate branches with **strictly zero cycles**.
- **Bidirectional Backlinks Search (Meet-in-the-Middle)**: Pre-indexes target article backlinks to convert exponential $\mathcal{O}(b^d)$ searches into rapid $\le 2$-hop instant convergence.
- **100% Verified Links**: Validates that every intermediate hop exists directly within the rendered body of the preceding Wikipedia article before committing.
- **Two-Tier SQLite + LRU Cache**: Persistent link cache for sub-50ms repeat evaluations.
- **Dual Interfaces**: Modern React + Vite frontend backed by FastAPI, plus rich terminal CLI and Streamlit interfaces.

---

## 🚀 Quick Start

### 1. Backend Setup

Ensure Python 3.10+ is installed:

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

---

### 2. Running the Modern Wikipedia Web App (Recommended)

The modern application consists of a **FastAPI backend** and a **React (Vite) frontend**:

#### Terminal 1 — Start FastAPI Server:
```bash
python -m uvicorn server:app --port 8000 --reload
```
The REST API will be active at `http://127.0.0.1:8000`.

#### Terminal 2 — Start React Vite Frontend:
```bash
cd frontend
npm install
npm run dev
```
Open your browser at **`http://localhost:5173`**.

---

### 3. Running via Rich CLI
You can also run speedruns directly from your terminal:

```bash
# Interactive mode
python cli.py

# Direct argument mode
python cli.py --start "Apple" --target "Steve Jobs"
```

---

### 4. Running via Streamlit (Legacy UI)
```bash
streamlit run app.py
```

---

### 5. Running Tests & Benchmarks

```bash
# Run unit tests (7+ pytest test cases)
pytest tests/ -v

# Run automated speedrun benchmark suite
python benchmark.py
```

---

## 📊 Benchmark Performance

| Category | Start Article | Target Article | Status | Hops | Latency |
|---|---|---|:---:|:---:|:---:|
| **Disambiguation Trap** | Apple | Steve Jobs | **PASS** | 2 | 0.02s |
| **Political Hub** | Barack Obama | United States | **PASS** | 2 | 0.01s |
| **Technology Bridge** | Python (programming language) | Guido van Rossum | **PASS** | 1 | 0.03s |
| **Science to History** | Albert Einstein | World War II | **PASS** | 1 | 0.05s |
| **Cross-Domain Gap** | Linux | Linus Torvalds | **PASS** | 1 | 0.04s |

---

## 📂 Project Structure

```
wiki-speedrunner/
├── src/
│   └── wikirunner/
│       ├── __init__.py
│       ├── config.py              # Strongly-typed configuration & API keys
│       ├── models.py              # Dataclass models (PageNode, StepLog, RunResult)
│       ├── api/
│       │   ├── client.py          # MediaWiki Action API client (connection pooling, retries)
│       │   └── cache.py           # SQLite + LRU two-tier link cache
│       ├── graph/
│       │   ├── heuristics.py      # Backlinks intersection, hubness, and title similarity scoring
│       │   └── search.py          # Bidirectional search engine with body link verification
│       └── llm/
│           └── strategic_agent.py # Gemini fallback advisor for local minima stagnation
├── frontend/                      # Modern React + Vite Web Application
│   ├── src/
│   │   ├── components/
│   │   │   ├── FloatingGraph.jsx  # Litmaps-style HTML5 Canvas constellation graph
│   │   │   └── DecisionDrawer.jsx # Slide-out candidate evaluation log
│   │   ├── App.jsx                # Wikipedia Vector shell, search bar, infobox, tabs
│   │   ├── index.css              # Wikimedia design system & typography tokens
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── tests/
│   ├── test_api_client.py
│   └── test_search.py
├── server.py                      # FastAPI REST API (serves /api/speedrun & static frontend)
├── cli.py                         # Rich terminal CLI
├── benchmark.py                   # Automated benchmark test suite
├── app.py                         # Streamlit web UI
├── ARCHITECTURE_CASE_STUDY.md     # In-depth architectural case study & engineering guide
├── requirements.txt               # Backend Python dependencies
├── .gitignore
└── README.md
```

---

## 📄 License & Attribution

- Built with love 💛 using the MediaWiki Action API.
- Content displayed from Wikipedia is licensed under [Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
