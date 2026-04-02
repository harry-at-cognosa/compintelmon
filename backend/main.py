"""
CompIntelMon Backend Entry Point.

Startup sequence:
1. Load config (.env)
2. Wait for database (sync, before event loop)
3. Wire up FastAPI app + routers
4. Mount SPA serving (after API routes)
5. Seed runs in lifespan (async, inside event loop)
"""
import os

from backend.config import DATABASE_SYNC_URL, FRONTEND_DIR_STATIC  # noqa: F401
from backend.db.session import wait_for_database

# Block until DB is available (sync — safe at module level)
wait_for_database()

# Import app and wire up routers
from backend.app import app  # noqa: E402
from backend.api import api_router  # noqa: E402

app.include_router(api_router)

# Mount frontend SPA serving AFTER API routes to avoid conflicts
from fastapi.staticfiles import StaticFiles  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402

_static_dir = FRONTEND_DIR_STATIC
_assets_dir = os.path.join(_static_dir, "assets")
_index_path = os.path.join(_static_dir, "index.html")

if os.path.isdir(_assets_dir):
    app.mount("/app/assets", StaticFiles(directory=_assets_dir), name="static-assets")


# Serve favicon at root (browsers request /favicon.ico by default)
_favicon_ico = os.path.join(_static_dir, "favicon.ico")
_favicon_svg = os.path.join(_static_dir, "favicon.svg")

if os.path.isfile(_favicon_ico):
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon_ico():
        return FileResponse(_favicon_ico, media_type="image/x-icon")

if os.path.isfile(_favicon_svg):
    @app.get("/favicon.svg", include_in_schema=False)
    async def favicon_svg():
        return FileResponse(_favicon_svg, media_type="image/svg+xml")


@app.get("/app/{full_path:path}")
async def serve_spa(full_path: str):
    """Catch-all: serve index.html for all /app/* routes (SPA routing)."""
    # Serve static files (favicon, apple-touch-icon) from the static dir
    static_file = os.path.join(_static_dir, full_path)
    if full_path and os.path.isfile(static_file) and not full_path.startswith("assets"):
        return FileResponse(static_file)
    if os.path.isfile(_index_path):
        return FileResponse(_index_path)
    return {"detail": "Frontend not built. Run: cd frontend && npm run build"}
