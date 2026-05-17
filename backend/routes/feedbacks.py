"""Routes feedbacks (utilisateur + admin)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends

from db import db
from deps import auth_user, require_admin
from models import Feedback, FeedbackCreate

router = APIRouter()


@router.post("/feedbacks", response_model=Feedback)
async def create_feedback(payload: FeedbackCreate, user=Depends(auth_user)):
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "user_email": user["email"],
        "page_context": payload.page_context,
        "user_comment": payload.user_comment,
        "screenshot_data": payload.screenshot_data,
        "encoded_data_snapshot": payload.encoded_data_snapshot,
        "company_id": user.get("company_id", "default"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.feedbacks.insert_one(doc)
    doc.pop("_id", None)
    return Feedback(**doc)


@router.get("/feedbacks", response_model=List[Feedback])
async def list_feedbacks(user=Depends(require_admin)):
    docs = (
        await db.feedbacks.find(
            {"company_id": user.get("company_id", "default")}, {"_id": 0}
        )
        .sort("created_at", -1)
        .to_list(500)
    )
    return [Feedback(**d) for d in docs]


@router.delete("/feedbacks/{feedback_id}")
async def delete_feedback(feedback_id: str, user=Depends(require_admin)):
    await db.feedbacks.delete_one(
        {"id": feedback_id, "company_id": user.get("company_id", "default")}
    )
    return {"ok": True}
