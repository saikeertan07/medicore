from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_roles
from app.models.models import Room, RoomStatus, UserRole
from app.schemas.schemas import RoomOut

router = APIRouter(prefix="/rooms", tags=["Hospital Rooms"])

def room_to_out(r: Room) -> RoomOut:
    return RoomOut(
        id=r.id,
        room_number=r.room_number,
        department_id=r.department_id,
        department_name=r.department.name if r.department else None,
        room_type=r.room_type,
        status=r.status,
        bed_count=r.bed_count,
        floor=r.floor
    )

@router.get("", response_model=List[RoomOut])
def list_rooms(
    status: Optional[RoomStatus] = None,
    department_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Room)
    if status:
        query = query.filter(Room.status == status)
    if department_id:
        query = query.filter(Room.department_id == department_id)
    return [room_to_out(r) for r in query.all()]
