import csv
import json
import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.base import Task, Board, BoardColumn, Sprint, TaskStatus
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

router = APIRouter()


@router.get("/csv")
async def export_csv(
    board_id: int = None,
    sprint_id: int = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Task)
    if sprint_id:
        query = query.where(Task.sprint_id == sprint_id)
    elif board_id:
        cols = await db.execute(select(BoardColumn.id).where(BoardColumn.board_id == board_id))
        col_ids = [c for c in cols.scalars().all()]
        if col_ids:
            query = query.where(Task.column_id.in_(col_ids))
    result = await db.execute(query)
    tasks = result.scalars().all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "title", "status", "priority", "story_points", "column_id", "sprint_id", "created_at"])
    for t in tasks:
        writer.writerow([t.id, t.title, t.status.value, t.priority.value, t.story_points, t.column_id, t.sprint_id, t.created_at.isoformat() if t.created_at else ""])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=taskforge-export.csv"},
    )


@router.get("/json")
async def export_json(
    board_id: int = None,
    sprint_id: int = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Task)
    if sprint_id:
        query = query.where(Task.sprint_id == sprint_id)
    elif board_id:
        cols = await db.execute(select(BoardColumn.id).where(BoardColumn.board_id == board_id))
        col_ids = [c for c in cols.scalars().all()]
        if col_ids:
            query = query.where(Task.column_id.in_(col_ids))
    result = await db.execute(query)
    tasks = result.scalars().all()
    data = [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "status": t.status.value,
            "priority": t.priority.value,
            "story_points": t.story_points,
            "column_id": t.column_id,
            "sprint_id": t.sprint_id,
            "assignee_id": t.assignee_id,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "cycle_time": t.cycle_time,
            "lead_time": t.lead_time,
        }
        for t in tasks
    ]
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=taskforge-export.json"},
    )


@router.get("/pdf")
async def export_pdf(board_id: int, db: AsyncSession = Depends(get_db)):
    board = await db.get(Board, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    cols = await db.execute(select(BoardColumn).where(BoardColumn.board_id == board_id).order_by(BoardColumn.position))
    columns = cols.scalars().all()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    styles = getSampleStyleSheet()
    elements = []
    elements.append(Paragraph(f"TaskForge — {board.name}", styles["Title"]))
    if board.description:
        elements.append(Paragraph(board.description, styles["Normal"]))
    elements.append(Spacer(1, 12))
    table_data = [["Title", "Status", "Priority", "SP", "Column"]]
    for col in columns:
        tasks = await db.execute(select(Task).where(Task.column_id == col.id).order_by(Task.position))
        for t in tasks.scalars().all():
            table_data.append([
                t.title[:40],
                t.status.value,
                t.priority.value,
                str(t.story_points or ""),
                col.name,
            ])
    if len(table_data) == 1:
        table_data.append(["(no tasks)", "", "", "", ""])
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=taskforge-board-{board_id}.pdf"},
    )
