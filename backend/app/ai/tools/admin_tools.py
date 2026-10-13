from datetime import date
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import User, Patient, Doctor, Appointment, Department, InventoryItem, Room, InventoryStatus, RoomStatus

def get_appointment_statistics(db: Session, current_user: User) -> Dict[str, Any]:
    today = date.today()
    total = db.query(Appointment).count()
    today_count = db.query(Appointment).filter(Appointment.date == today).count()
    completed = db.query(Appointment).filter(Appointment.status == "COMPLETED").count()
    cancelled = db.query(Appointment).filter(Appointment.status == "CANCELLED").count()
    confirmed = db.query(Appointment).filter(Appointment.status == "CONFIRMED").count()

    return {
        "total_appointments": total,
        "today_appointments": today_count,
        "completed": completed,
        "cancelled": cancelled,
        "confirmed": confirmed,
        "cancellation_rate_percent": round((cancelled / total * 100) if total > 0 else 0, 1)
    }

def get_department_statistics(db: Session, current_user: User) -> List[Dict[str, Any]]:
    depts = db.query(Department).all()
    results = []
    for d in depts:
        doc_count = db.query(Doctor).filter(Doctor.department_id == d.id).count()
        app_count = db.query(Appointment).filter(Appointment.department_id == d.id).count()
        results.append({
            "department_name": d.name,
            "code": d.code,
            "doctor_count": doc_count,
            "total_appointments": app_count
        })
    return results

def get_doctor_workload(db: Session, current_user: User) -> List[Dict[str, Any]]:
    docs = db.query(Doctor).all()
    workload = []
    for d in docs:
        total_apps = db.query(Appointment).filter(Appointment.doctor_id == d.id).count()
        workload.append({
            "doctor_name": d.user.full_name,
            "department": d.department.name,
            "appointments_assigned": total_apps,
            "rating": float(d.rating)
        })
    workload.sort(key=lambda x: x["appointments_assigned"], reverse=True)
    return workload[:10]

def get_inventory_alerts(db: Session, current_user: User) -> List[Dict[str, Any]]:
    items = db.query(InventoryItem).filter(
        (InventoryItem.status.in_([InventoryStatus.LOW_STOCK, InventoryStatus.CRITICAL])) |
        (InventoryItem.quantity <= InventoryItem.reorder_level)
    ).all()
    return [{
        "item_name": item.item_name,
        "category": item.category,
        "quantity": item.quantity,
        "reorder_level": item.reorder_level,
        "status": item.status.value,
        "supplier": item.supplier
    } for item in items]
