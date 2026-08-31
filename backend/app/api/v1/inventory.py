from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import InventoryItem, InventoryStatus
from app.schemas.schemas import InventoryOut

router = APIRouter(prefix="/inventory", tags=["Hospital Inventory"])

@router.get("", response_model=List[InventoryOut])
def list_inventory(
    category: Optional[str] = None,
    status: Optional[InventoryStatus] = None,
    db: Session = Depends(get_db)
):
    query = db.query(InventoryItem)
    if category:
        query = query.filter(InventoryItem.category.ilike(f"%{category}%"))
    if status:
        query = query.filter(InventoryItem.status == status)
    return query.all()
