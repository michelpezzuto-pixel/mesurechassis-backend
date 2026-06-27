"""MesureEscalier — Application entry point.

Composed of modular routers (auth, projects, exports,
voice, stats, integration). Startup events seed demo users and
ensure MongoDB indexes.
"""
from __future__ import annotations

from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware

from core.db import client, db
from services.seed import seed_demo_users
from routers import auth as auth_router
from routers import projects as projects_router
from routers import exports as exports_router
from routers import voice as voice_router
from routers import stats as stats_router
from routers import integration as integration_router
from routers import stairs_v2 as stairs_v2_router
from services.migration_v2 import migrate_projects_to_stairs

app = FastAPI(title="MesureEscalier API", version="2.0")

# Single /api prefix for the whole public surface
api = APIRouter(prefix="/api")
api.include_router(auth_router.router)
api.include_router(projects_router.router)
api.include_router(exports_router.router)
api.include_router(voice_router.router)
api.include_router(stats_router.router)
api.include_router(integration_router.router)
api.include_router(stairs_v2_router.router)
from routers import poc as poc_router  # noqa: E402
api.include_router(poc_router.router)


@api.get("/")
async def root():
    return {"app": "MesureEscalier", "version": "2.0", "status": "ok"}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await db.users.create_index("email", unique=True)
    await db.projects.create_index("created_at")
    await db.measurements.create_index("project_id", unique=True)
    await seed_demo_users()
    # Migration v2 idempotente : transforme les anciens projets en stairs[]
    await migrate_projects_to_stairs()


@app.on_event("shutdown")
async def on_shutdown():
    client.close()
