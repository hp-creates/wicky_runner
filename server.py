"""
FastAPI Server for WikiSpeedrunner Floating Graph Frontend (Litmaps Style).
Provides REST APIs for speedrun navigation, graph node layout, and challenge pairs.
"""

import sys
import os
import math
from typing import Optional, List, Dict
# pyrefly: ignore [missing-import]
from pydantic import BaseModel

# Ensure src is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from wikirunner import WikiSpeedrunner, RunnerConfig

app = FastAPI(title="WikiSpeedrunner API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CURATED_PAIRS = [
    {"start": "Apple", "target": "Steve Jobs", "category": "Tech Titans"},
    {"start": "Barack Obama", "target": "United States", "category": "World Politics"},
    {"start": "Nintendo", "target": "Samurai", "category": "Gaming to History"},
    {"start": "Pizza", "target": "Ancient Rome", "category": "Culinary Journey"},
    {"start": "Python (programming language)", "target": "Guido van Rossum", "category": "Code Origins"},
    {"start": "Albert Einstein", "target": "World War II", "category": "Science to History"},
    {"start": "Linux", "target": "Linus Torvalds", "category": "Open Source Legend"},
    {"start": "Mona Lisa", "target": "Leonardo da Vinci", "category": "Art Masterpiece"},
    {"start": "Beatles", "target": "London", "category": "Music & Culture"},
]


class SpeedrunRequest(BaseModel):
    start: str
    target: str
    enable_llm: bool = False
    gemini_key: Optional[str] = None


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "2.0.0", "name": "WikiSpeedrunner API"}


@app.get("/api/random-pairs")
def get_random_pairs():
    return CURATED_PAIRS


@app.post("/api/speedrun")
def execute_speedrun(req: SpeedrunRequest):
    start = req.start.strip()
    target = req.target.strip()

    if not start or not target:
        raise HTTPException(status_code=400, detail="Start and target articles cannot be empty.")

    config = RunnerConfig(
        enable_llm_advisor=req.enable_llm,
        gemini_api_key=req.gemini_key.strip() if req.gemini_key and req.gemini_key.strip() else os.getenv("GEMINI_API_KEY", "")
    )
    runner = WikiSpeedrunner(config)
    result = runner.run(start, target)

    path_titles = result.path_titles if result.path_titles else result.path
    num_path_nodes = len(path_titles)

    # Build Graph Topology (Litmaps style constellation)
    nodes: List[Dict] = []
    edges: List[Dict] = []
    seen_nodes = set()

    # Layout dimensions for canvas coordinate space (centered around 0,0)
    # Path nodes form an organic backbone arc/wave across the center
    for i, title in enumerate(path_titles):
        is_start = (i == 0)
        is_target = (i == num_path_nodes - 1)
        node_id = f"path_{i}_{title}"

        # Balanced horizontal constellation wave
        norm = i / max(1, num_path_nodes - 1)
        x = (norm - 0.5) * 600
        # Gentle alternating celestial arc
        y = math.sin(norm * math.pi * 1.2 - 0.3) * 70 + ((i % 2) * 36 - 18)

        node_data = {
            "id": node_id,
            "title": title,
            "url": f"/wiki/{title.replace(' ', '_')}",
            "is_path": True,
            "is_start": is_start,
            "is_target": is_target,
            "hop_index": i,
            "x": round(x, 1),
            "y": round(y, 1),
            "type": "start" if is_start else ("target" if is_target else "hop"),
            "label": f"0{i + 1} // {title.upper()}" if i < 9 else f"{i + 1} // {title.upper()}"
        }
        nodes.append(node_data)
        seen_nodes.add(title.lower())

        if i > 0:
            prev_id = f"path_{i-1}_{path_titles[i-1]}"
            edges.append({
                "source": prev_id,
                "target": node_id,
                "is_path": True,
                "weight": 2.5
            })

    # Add evaluated candidate branch nodes (subtle constellation nodes, exactly like in the user's image)
    for step_entry in result.log:
        step_idx = step_entry.get("step", 1) - 1
        curr_title = step_entry.get("current_title", "")
        curr_node_id = f"path_{step_idx}_{curr_title}" if step_idx < len(path_titles) else None

        top_cands = step_entry.get("top_candidates", [])
        # Pick top 2 non-chosen candidates to form constellation branches
        branch_count = 0
        for c in top_cands:
            c_title = c.get("title", "")
            if not c_title or c_title.lower() in seen_nodes:
                continue

            seen_nodes.add(c_title.lower())
            cand_id = f"cand_{step_idx}_{c_title}"

            # Place candidate node slightly offset from current step node
            base_node = next((n for n in nodes if n["title"].lower() == curr_title.lower()), None)
            base_x = base_node["x"] if base_node else 0
            base_y = base_node["y"] if base_node else 0

            branch_angle = (branch_count * 1.2 - 0.6) + (step_idx * 0.4)
            cand_dist = 110 + (branch_count * 30)
            cand_x = base_x + math.cos(branch_angle) * cand_dist
            cand_y = base_y + math.sin(branch_angle) * cand_dist

            nodes.append({
                "id": cand_id,
                "title": c_title,
                "url": c.get("url", f"/wiki/{c_title.replace(' ', '_')}"),
                "is_path": False,
                "is_start": False,
                "is_target": False,
                "score": round(c.get("score", 0.0), 2),
                "x": round(cand_x, 1),
                "y": round(cand_y, 1),
                "type": "candidate",
                "label": c_title.upper()
            })

            if curr_node_id:
                edges.append({
                    "source": curr_node_id,
                    "target": cand_id,
                    "is_path": False,
                    "weight": 1.0
                })

            branch_count += 1
            if branch_count >= 2:
                break

    data = result.to_dict()
    data["graph"] = {
        "nodes": nodes,
        "edges": edges
    }
    return data


# Serve frontend static assets if built
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
