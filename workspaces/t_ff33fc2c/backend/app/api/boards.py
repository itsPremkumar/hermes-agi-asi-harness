from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.models.base import Board, BoardColumn
from app.schemas.board import BoardCreate, BoardOut, ColumnCreate, ColumnOut

router = APIRouter()


@router.post("/", response_model=BoardOut)
async def create_board(board_in: BoardCreate, db: AsyncSession = Depends(get_db)):
    board = Board(name=board_in.name, description=board_in.description)
    db.add(board)
    await db.commit()
    await db.refresh(board)
    return board


@router.get("/", response_model=List[BoardOut])
async def list_boards(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Board))
    return result.scalars().all()


@router.get("/{board_id}", response_model=BoardOut)
async def get_board(board_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Board).where(Board.id == board_id))
    board = result.scalar_one_or_none()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return board


@router.post("/{board_id}/columns", response_model=ColumnOut)
async def create_column(board_id: int, col_in: ColumnCreate, db: AsyncSession = Depends(get_db)):
    col = BoardColumn(
        board_id=board_id, name=col_in.name, position=col_in.position, wip_limit=col_in.wip_limit
    )
    db.add(col)
    await db.commit()
    await db.refresh(col)
    return col


@router.get("/{board_id}/columns", response_model=List[ColumnOut])
async def list_columns(board_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BoardColumn).where(BoardColumn.board_id == board_id))
    return result.scalars().all()
