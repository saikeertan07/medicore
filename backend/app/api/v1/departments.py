from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Department, Doctor, User, UserRole
from app.schemas.schemas import DepartmentOut, DepartmentCreate, DepartmentUpdate, DepartmentStatusUpdate, DoctorOut
from app.core.security import require_roles, get_current_user
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/departments", tags=["Departments"])

@router.get("", response_model=List[DepartmentOut])
def get_departments(
    active_only: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Department)
    if active_only is not None:
        query = query.filter(Department.is_active == active_only)
    return query.order_by(Department.name.asc()).all()

@router.get("/{dept_id}", response_model=DepartmentOut)
def get_department(dept_id: int, db: Session = Depends(get_db)):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")
    return dept

@router.post("", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(
    dept_in: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    existing = db.query(Department).filter(
        (Department.name == dept_in.name) | (Department.code == dept_in.code)
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department name or code already exists.")

    dept = Department(**dept_in.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)

    record_audit_log(
        db=db,
        action="DEPARTMENT_CREATE",
        resource_type="Department",
        resource_id=str(dept.id),
        user_id=current_user.id,
        details={"name": dept.name, "code": dept.code}
    )

    return dept

@router.put("/{dept_id}", response_model=DepartmentOut)
def update_department(
    dept_id: int,
    dept_in: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")

    update_data = dept_in.model_dump(exclude_unset=True)
    if "name" in update_data or "code" in update_data:
        conflict = db.query(Department).filter(
            Department.id != dept_id,
            ((Department.name == update_data.get("name")) | (Department.code == update_data.get("code")))
        ).first()
        if conflict:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department name or code already exists.")

    for k, v in update_data.items():
        setattr(dept, k, v)

    db.commit()
    db.refresh(dept)

    record_audit_log(
        db=db,
        action="DEPARTMENT_UPDATE",
        resource_type="Department",
        resource_id=str(dept.id),
        user_id=current_user.id,
        details={"updated_fields": list(update_data.keys())}
    )

    return dept

@router.patch("/{dept_id}/status", response_model=DepartmentOut)
def update_department_status(
    dept_id: int,
    status_in: DepartmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")

    dept.is_active = status_in.is_active
    db.commit()
    db.refresh(dept)

    record_audit_log(
        db=db,
        action="DEPARTMENT_STATUS_UPDATE",
        resource_type="Department",
        resource_id=str(dept.id),
        user_id=current_user.id,
        details={"is_active": dept.is_active}
    )

    return dept

@router.get("/{dept_id}/doctors", response_model=List[DoctorOut])
def get_department_doctors(
    dept_id: int,
    db: Session = Depends(get_db)
):
    from app.api.v1.doctors import doctor_to_out
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")

    doctors = db.query(Doctor).join(User, Doctor.user_id == User.id).filter(
        Doctor.department_id == dept_id,
        User.is_active == True
    ).all()
    return [doctor_to_out(d) for d in doctors]
