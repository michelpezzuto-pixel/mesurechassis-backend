"""MesureChâssis backend — point d'entrée FastAPI.

Tous les modèles, dépendances, et routes vivent désormais dans des
modules dédiés (db.py, models.py, deps.py, utils.py, routes/, seed.py).
"""
from __future__ import annotations

from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware

from db import client as mongo_client
from routes import auth as auth_routes
from routes import chantiers as chantiers_routes
from routes import company as company_routes
from routes import exports as exports_routes
from routes import feedbacks as feedbacks_routes
from routes import mesures as mesures_routes
from routes import stats as stats_routes
from seed import seed_data

# --- App & routers -------------------------------------------------------
app = FastAPI(title="MesureChâssis API")
api = APIRouter(prefix="/api")

# Tous les routeurs domaine sont montés sous /api
api.include_router(auth_routes.router)
api.include_router(chantiers_routes.router)
api.include_router(mesures_routes.router)
api.include_router(feedbacks_routes.router)
api.include_router(company_routes.router)
api.include_router(stats_routes.router)
api.include_router(exports_routes.router)

app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup() -> None:
    await seed_data()


@app.on_event("shutdown")
async def _shutdown() -> None:
    mongo_client.close()
