from datetime import date, timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    User, Patient, Doctor, Appointment, Department, Room, InventoryItem, 
    RoomStatus, InventoryStatus, AppointmentStatus, UserRole, StaffProfile
)
from app.services.appointment_service import get_hospital_now

router = APIRouter(prefix="/analytics", tags=["Hospital Analytics & Dashboard"])

@router.get("/dashboard")
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.STAFF, UserRole.DOCTOR, UserRole.RECEPTIONIST, UserRole.NURSE]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only hospital staff and administrators can access operational dashboards."
        )

    today = get_hospital_now().date()

    total_patients = db.query(Patient).count()
    total_doctors = db.query(Doctor).count()
    total_staff = db.query(User).filter(User.role.in_([UserRole.DOCTOR, UserRole.NURSE, UserRole.RECEPTIONIST, UserRole.ADMIN, UserRole.STAFF])).count()

    today_apps = db.query(Appointment).filter(Appointment.date == today).count()
    today_checked_in = db.query(Appointment).filter(Appointment.date == today, Appointment.status == AppointmentStatus.CHECKED_IN).count()
    today_in_progress = db.query(Appointment).filter(Appointment.date == today, Appointment.status == AppointmentStatus.IN_PROGRESS).count()
    today_confirmed = db.query(Appointment).filter(Appointment.date == today, Appointment.status == AppointmentStatus.CONFIRMED).count()
    today_completed = db.query(Appointment).filter(Appointment.date == today, Appointment.status == AppointmentStatus.COMPLETED).count()

    upcoming_apps = db.query(Appointment).filter(
        Appointment.date > today,
        Appointment.status.in_([AppointmentStatus.CONFIRMED, AppointmentStatus.SCHEDULED])
    ).count()
    completed_apps = db.query(Appointment).filter(Appointment.status == AppointmentStatus.COMPLETED).count()
    cancelled_apps = db.query(Appointment).filter(Appointment.status == AppointmentStatus.CANCELLED).count()

    available_rooms = db.query(Room).filter(Room.status == RoomStatus.AVAILABLE).count()
    total_rooms = db.query(Room).count()

    inventory_alerts = db.query(InventoryItem).filter(
        InventoryItem.status.in_([InventoryStatus.LOW_STOCK, InventoryStatus.CRITICAL])
    ).count()

    # Department distribution
    depts = db.query(Department).all()
    dept_usage = []
    for d in depts:
        count = db.query(Appointment).filter(Appointment.department_id == d.id).count()
        dept_usage.append({"name": d.name, "value": count})

    # Status distribution
    status_distribution = [
        {"name": "Completed", "value": completed_apps},
        {"name": "Confirmed", "value": db.query(Appointment).filter(Appointment.status == AppointmentStatus.CONFIRMED).count()},
        {"name": "Checked In", "value": db.query(Appointment).filter(Appointment.status == AppointmentStatus.CHECKED_IN).count()},
        {"name": "In Progress", "value": db.query(Appointment).filter(Appointment.status == AppointmentStatus.IN_PROGRESS).count()},
        {"name": "Cancelled", "value": cancelled_apps},
    ]

    # Appointment 7-day trend
    trends = []
    for i in range(6, -1, -1):
        d_val = today - timedelta(days=i)
        day_count = db.query(Appointment).filter(Appointment.date == d_val).count()
        trends.append({
            "date": d_val.strftime("%b %d"),
            "appointments": day_count
        })

    # Doctor workload top 5
    docs = db.query(Doctor).all()
    workload = []
    for doc in docs:
        c = db.query(Appointment).filter(Appointment.doctor_id == doc.id).count()
        workload.append({
            "doctor": doc.user.full_name if doc.user else f"Doctor {doc.id}",
            "department": doc.department.name if doc.department else "General",
            "appointments": c
        })
    workload.sort(key=lambda x: x["appointments"], reverse=True)

    # Scoped doctor metrics if user is a doctor
    doctor_metrics = {}
    if current_user.role == UserRole.DOCTOR and current_user.doctor_profile:
        doc_id = current_user.doctor_profile.id
        doctor_metrics = {
            "doctor_id": doc_id,
            "today_appointments": db.query(Appointment).filter(Appointment.doctor_id == doc_id, Appointment.date == today).count(),
            "checked_in_waiting": db.query(Appointment).filter(Appointment.doctor_id == doc_id, Appointment.date == today, Appointment.status == AppointmentStatus.CHECKED_IN).count(),
            "in_progress": db.query(Appointment).filter(Appointment.doctor_id == doc_id, Appointment.date == today, Appointment.status == AppointmentStatus.IN_PROGRESS).count(),
            "completed_today": db.query(Appointment).filter(Appointment.doctor_id == doc_id, Appointment.date == today, Appointment.status == AppointmentStatus.COMPLETED).count(),
            "upcoming_total": db.query(Appointment).filter(Appointment.doctor_id == doc_id, Appointment.date > today).count()
        }

    return {
        "summary": {
            "total_patients": total_patients,
            "total_doctors": total_doctors,
            "total_staff": total_staff,
            "today_appointments": today_apps,
            "today_checked_in": today_checked_in,
            "today_in_progress": today_in_progress,
            "today_confirmed": today_confirmed,
            "today_completed": today_completed,
            "upcoming_appointments": upcoming_apps,
            "completed_appointments": completed_apps,
            "cancelled_appointments": cancelled_apps,
            "available_rooms": available_rooms,
            "total_rooms": total_rooms,
            "inventory_alerts": inventory_alerts
        },
        "reception": {
            "today_total": today_apps,
            "today_checked_in": today_checked_in,
            "today_in_progress": today_in_progress,
            "today_pending_checkin": today_confirmed,
            "today_completed": today_completed,
            "total_registered_patients": total_patients
        },
        "nurse": {
            "triage_waiting": today_checked_in,
            "in_consultation": today_in_progress,
            "today_total": today_apps,
            "today_completed": today_completed
        },
        "doctor_specific": doctor_metrics,
        "department_usage": dept_usage,
        "status_distribution": status_distribution,
        "appointment_trends": trends,
        "doctor_workload": workload[:5]
    }
