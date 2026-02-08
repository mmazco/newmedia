"""
FastAPI backend for Follow the Money.
Serves the web UI and runs conversations via API.
"""
import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Follow the Money")

# Ensure directories exist (needed for Railway where gitignored dirs are missing)
os.makedirs("audio_output", exist_ok=True)
os.makedirs("demo/audio", exist_ok=True)

# Serve static files
app.mount("/demo", StaticFiles(directory="demo"), name="demo")
app.mount("/audio_output", StaticFiles(directory="audio_output"), name="audio_output")
app.mount("/static", StaticFiles(directory="web"), name="static")


@app.get("/")
async def index():
    return FileResponse("web/index.html")


@app.get("/api/publications")
async def get_publications():
    """Return the list of publications."""
    with open("data/publications.json") as f:
        data = json.load(f)
    pubs = []
    for p in data["publications"]:
        rating = p.get("ground_news_rating", {})
        pubs.append({
            "id": p["id"],
            "name": p["name"],
            "owner": p["owner"],
            "bias": rating.get("bias", "Unknown"),
            "factuality": rating.get("factuality", "Unknown"),
            "category": rating.get("ownership_category", "Unknown"),
        })
    return pubs


@app.get("/api/demo/{pub_id}")
async def get_demo_conversation(pub_id: str):
    """Return a pre-baked demo conversation if available."""
    path = f"demo/{pub_id}_conversation.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="No demo available for this publication")
    with open(path) as f:
        return json.load(f)


@app.post("/api/investigate/{pub_id}")
async def investigate(pub_id: str):
    """Run a new conversation about a publication (live generation)."""
    from src.orchestrator import load_publications, run_conversation
    from src.cartesia_client import generate_conversation_audio

    data = load_publications()
    pub = next((p for p in data["publications"] if p["id"] == pub_id), None)
    if not pub:
        raise HTTPException(status_code=404, detail=f"Publication '{pub_id}' not found")

    # Run conversation with web search
    conversation = run_conversation(pub, num_exchanges=2, use_web_search=True)

    # Generate audio
    output_dir = f"demo/audio/{pub_id}"
    results = generate_conversation_audio(conversation, output_dir=output_dir)

    # Build response
    turns = []
    for r in results:
        turns.append({
            "agent": r["agent"],
            "text": r["text"],
            "audio_path": r["audio_path"],
        })

    # Save for future demo use
    output = {
        "publication": pub["name"],
        "owner": pub["owner"],
        "turns": turns,
    }
    with open(f"demo/{pub_id}_conversation.json", "w") as f:
        json.dump(output, f, indent=2)

    return output


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
