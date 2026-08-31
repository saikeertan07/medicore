from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Doctor, User
from app.schemas.schemas import DoctorOut

router = APIRouter(prefix="/doctors", tags=["Doctors"])

def doctor_to_out(doctor: Doctor) -> DoctorOut:
    return DoctorOut(
        id=doctor.id,
        user_id=doctor.user_id,
        full_name=doctor.user.full_name,
        email=doctor.user.email,
        department_id=doctor.department_id,
        department_name=doctor.department.name if doctor.department else None,
        specialization=doctor.specialization,
        qualification=doctor.qualification,
        experience_years=doctor.experience_years,
        consultation_fee=float(doctor.consultation_fee),
        bio=doctor.bio,
        room_number=doctor.room_number,
        rating=float(doctor.rating),
        schedules=[s for s in doctor.schedules]
    )

@router.get("", response_model=List[DoctorOut])
def get_doctors(
    department_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Doctor).join(User, Doctor.user_id == User.id)
    if department_id:
        query = query.filter(Doctor.department_id == department_id)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            (User.full_name.ilike(pattern)) |
            (Doctor.specialization.ilike(pattern))
        )
    doctors = query.all()
    return [doctor_to_out(d) for d in doctors]

@router.get("/{doctor_id}", response_model=DoctorOut)
def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found.")
    return doctor_to_out(doctor)
