import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.database import init_db
from app.router import ai, tasks
from fastapi.responses import FileResponse, Response

# Lifespan manager replaces the deprecated on_event("startup") pattern
# It guarantees that resources are cleanly initialized and freed during lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    # initialize SQLite schemas on server startup
    init_db()
    yield
    # place DB pool cleanups or connection closes here if required

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan
)

# Set up parameterised CORS origins to prevent unauthorized cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom security headers middleware providing defensive depth
@app.middleware("http")
async def apply_defensive_headers(request: Request, call_next):
    response = await call_next(request)
    
    # 1. Anti-clickjacking: prevent site from being rendered within frames/iframes
    response.headers["X-Frame-Options"] = "DENY"
    
    # 2. Prevent MIME type sniffing: enforce browser compliance with declared Content-Type headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # 3. Enable legacy browser XSS filters
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # 4. Strict Transport Security: enforce HTTPS in browsers for 1 year
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # 5. Content Security Policy (CSP): lock down asset origin execution targets
    # Allow fonts from google api, scripts from local site, styles from local site + font api
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:;"
    )
    
    return response

# Register feature routers
app.include_router(tasks.router)
app.include_router(ai.router)

# Mount the static directory to serve HTML/CSS/JS frontend assets
# Absolute path calculations prevent runtime path issues when started from different directories
static_dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir_path, exist_ok=True)

# Mount at root "/" as the final route so API endpoints resolve first
@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    """Serve a lightweight SVG favicon for browsers requesting /favicon.ico."""
    svg_path = os.path.join(static_dir_path, "favicon.svg")
    if not os.path.exists(svg_path):
        # return an empty 204 if missing to avoid noise in logs
        return Response(status_code=204)
    return FileResponse(svg_path, media_type="image/svg+xml")

app.mount("/", StaticFiles(directory=static_dir_path, html=True), name="static")
