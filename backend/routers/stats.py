"""Global statistics."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from core.db import db
from core.security import get_current_user, project_visible_to

router = APIRouter()


@router.get("/stats")
async def stats(user=Depends(get_current_user)):
    q = project_visible_to(user)
    total = await db.projects.count_documents(q)
    by_status = {}
    for s in ["brouillon", "a_mesurer", "a_verifier", "valide", "en_fabrication", "termine"]:
        by_status[s] = await db.projects.count_documents({**q, "status": s})

    project_ids = [p["id"] async for p in db.projects.find(q, {"id": 1, "_id": 0})]
    total_measurements = (
        await db.measurements.count_documents({"project_id": {"$in": project_ids}})
        if project_ids else 0
    )
    validated = (
        await db.measurements.count_documents({"project_id": {"$in": project_ids}, "validated": True})
        if project_ids else 0
    )

    avg_steps = None
    if total_measurements:
        cursor = db.measurements.find({"project_id": {"$in": project_ids}}, {"result.n_steps": 1, "_id": 0})
        steps = [m["result"]["n_steps"] async for m in cursor if m.get("result")]
        if steps:
            avg_steps = round(sum(steps) / len(steps), 1)

    team_size = None
    if user["role"] == "admin":
        team_size = await db.users.count_documents({})

    return {
        "total_projects": total,
        "by_status": by_status,
        "total_measurements": total_measurements,
        "validated_measurements": validated,
        "average_steps": avg_steps,
        "team_size": team_size,
    }
