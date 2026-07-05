import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.routes import router

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Home Ledger", lifespan=lifespan)
app.include_router(router)

if os.path.isdir(os.path.join(STATIC_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")
    index_html = os.path.join(STATIC_DIR, "index.html")

    @app.get("/{full_path:path}")
    def spa(full_path: str):  # noqa: ARG001 — history-mode fallback
        return FileResponse(index_html)