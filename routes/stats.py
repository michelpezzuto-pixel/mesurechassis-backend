"""Routes statistiques (admin uniquement)."""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from db import CONVERTED_STATUSES, VALID_STATUSES, db
from deps import require_admin

router = APIRouter()


@router.get("/stats/company")
async def stats_company(user=Depends(require_admin)):
    company = user.get("company_id", "default")
    pipe_status = [
        {"$match": {"company_id": company}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    by_status: dict[str, int] = {s: 0 for s in VALID_STATUSES}
    async for d in db.chantiers.aggregate(pipe_status):
        if d["_id"]:
            by_status[d["_id"]] = d["count"]
    total = sum(by_status.values())
    closure_rate = (
        round((by_status["cloture"] / total) * 100, 1) if total else 0.0
    )

    company_chantier_ids = await db.chantiers.distinct(
        "id", {"company_id": company}
    )
    chantier_to_tech: dict[str, Optional[str]] = {}
    async for c in db.chantiers.find(
        {"company_id": company}, {"_id": 0, "id": 1, "assigned_to": 1}
    ):
        chantier_to_tech[c["id"]] = c.get("assigned_to")

    by_tech: dict[str, dict] = {}
    total_mesures = 0
    total_alerts = 0
    async for m in db.mesures.find(
        {"chantier_id": {"$in": company_chantier_ids}},
        {"_id": 0, "chantier_id": 1, "alerts": 1},
    ):
        total_mesures += 1
        alerts = len(m.get("alerts") or [])
        total_alerts += alerts
        tech = chantier_to_tech.get(m["chantier_id"]) or "unassigned"
        slot = by_tech.setdefault(tech, {"mesures": 0, "alerts": 0})
        slot["mesures"] += 1
        slot["alerts"] += alerts

    tech_users: dict[str, dict] = {}
    async for u in db.users.find(
        {"company_id": company},
        {"_id": 0, "id": 1, "name": 1, "role": 1},
    ):
        tech_users[u["id"]] = u

    tech_breakdown = []
    for tid, stats in by_tech.items():
        info = tech_users.get(tid)
        tech_breakdown.append(
            {
                "user_id": tid,
                "name": info["name"] if info else "Non affecté",
                "role": info["role"] if info else "—",
                "mesures": stats["mesures"],
                "alerts": stats["alerts"],
            }
        )
    tech_breakdown.sort(key=lambda x: x["mesures"], reverse=True)
    return {
        "total_chantiers": total,
        "by_status": by_status,
        "closure_rate": closure_rate,
        "total_mesures": total_mesures,
        "total_alerts": total_alerts,
        "by_technician": tech_breakdown,
    }


@router.get("/stats/commercials")
async def stats_commercials(user=Depends(require_admin)):
    company = user.get("company_id", "default")
    commercials = await db.users.find(
        {"company_id": company, "role": "commercial"},
        {"_id": 0, "id": 1, "name": 1, "email": 1},
    ).to_list(500)
    rows = []
    total_created = 0
    total_converted = 0
    for u in commercials:
        created = await db.chantiers.count_documents(
            {"company_id": company, "created_by": u["id"]}
        )
        converted = await db.chantiers.count_documents(
            {
                "company_id": company,
                "created_by": u["id"],
                "status": {"$in": list(CONVERTED_STATUSES)},
            }
        )
        rate = round((converted / created) * 100, 1) if created else 0.0
        rows.append(
            {
                "user_id": u["id"],
                "name": u["name"],
                "email": u["email"],
                "created": created,
                "converted": converted,
                "conversion_rate": rate,
            }
        )
        total_created += created
        total_converted += converted
    rows.sort(key=lambda r: r["conversion_rate"], reverse=True)
    global_rate = (
        round((total_converted / total_created) * 100, 1)
        if total_created
        else 0.0
    )
    return {
        "commercials": rows,
        "total_created": total_created,
        "total_converted": total_converted,
        "global_conversion_rate": global_rate,
    }


@router.get("/stats/commercials/export.pdf")
async def stats_commercials_pdf(user=Depends(require_admin)):
    data = await stats_commercials(user)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, title="Rapport Performance Commerciaux"
    )
    styles = getSampleStyleSheet()
    story: list[Any] = []
    story.append(
        Paragraph(
            "<b>MesureChâssis</b> — Rapport Performance Commerciaux",
            styles["Title"],
        )
    )
    story.append(Spacer(1, 14))
    story.append(
        Paragraph(
            f"<b>Société :</b> {user.get('company_id', 'default')}",
            styles["Normal"],
        )
    )
    story.append(
        Paragraph(
            f"<b>Date :</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            f"<b>Total chantiers créés :</b> {data['total_created']}  ·  "
            f"<b>Convertis :</b> {data['total_converted']}  ·  "
            f"<b>Taux global :</b> {data['global_conversion_rate']}%",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 18))
    rows = [["Commercial", "Email", "Créés", "Convertis", "Conversion %"]]
    for r in data["commercials"]:
        rows.append(
            [
                r["name"],
                r["email"],
                str(r["created"]),
                str(r["converted"]),
                f"{r['conversion_rate']}%",
            ]
        )
    tbl = Table(rows, colWidths=[110, 170, 60, 70, 80])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FF5A00")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    story.append(tbl)
    doc.build(story)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                'attachment; filename="rapport-performance-commerciaux.pdf"'
            )
        },
    )
