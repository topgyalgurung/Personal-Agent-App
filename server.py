"""Local chat API and page. Listens on 127.0.0.1 only."""
import logging
import threading
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, StringConstraints

from agent_core import Session


logger = logging.getLogger(__name__)

HOST = "127.0.0.1"
PORT = 8000
PAGE = Path(__file__).parent / "frontend" / "index.html"

UNEXPECTED_ERROR = "Something went wrong. Check the terminal for details."


class ChatRequest(BaseModel):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def create_app(session=None):
    app = FastAPI(title="Personal Agent", docs_url=None, redoc_url=None)
    state = {"session": session}
    lock = threading.Lock()

    @app.get("/")
    def home():
        return FileResponse(PAGE)

    @app.post("/api/chat")
    def chat(request: ChatRequest):
        # One conversation, one request at a time.
        with lock:
            if state["session"] is None:
                state["session"] = Session()

            try:
                turn = state["session"].send(request.message)
            except Exception:
                logger.exception("Chat request failed")
                return {"text": "", "error": UNEXPECTED_ERROR, "tools": []}

        return {
            "text": turn.text,
            "error": turn.error,
            "tools": [record.name for record in turn.tool_calls],
        }

    return app


app = create_app()


def run():
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    run()
