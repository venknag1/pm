from pathlib import Path
import os
import json

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from dotenv import load_dotenv
import openai

load_dotenv()

app = FastAPI(title="PM MVP Backend")

public_dir = Path(__file__).resolve().parent / "public"


@app.get("/api/health")
def health():
    return {"status": "ok"}


class AIRequest(BaseModel):
    prompt: str
    board: dict | None = None


@app.post("/api/ai")
async def ai_endpoint(req: AIRequest):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai.api_key = api_key

    # Build messages; include board JSON as system context if provided
    messages = []
    if req.board is not None:
        try:
            board_json = json.dumps(req.board)
        except Exception:
            board_json = str(req.board)
        messages.append({"role": "system", "content": f"Current Kanban board JSON: {board_json}"})
    messages.append({"role": "user", "content": req.prompt})

    try:
        resp = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=512,
            temperature=0.2,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI request failed: {e}")

    # Extract assistant message text
    try:
        assistant_msg = resp.choices[0].message.content
    except Exception:
        assistant_msg = getattr(resp, 'text', str(resp))

    return {"message": assistant_msg}


app.mount("/", StaticFiles(directory=public_dir, html=True), name="public")
