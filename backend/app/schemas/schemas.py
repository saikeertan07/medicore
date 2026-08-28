from datetime import datetime, date, time
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.models import (
    UserRole, AppointmentType, AppointmentStatus, DocumentStatus, RoomType, RoomStatus, InventoryStatus,
    EncounterType, EncounterStatus, ClinicalNoteStatus, DiagnosisType,
    LabOrderPriority, LabOrderStatus, LabOrderItemStatus, LabSampleStatus, LabResultStatus, AbnormalFlag
)

# User & Auth Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: UserRole = UserRole.PATIENT

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    role: UserRole
    user_id: int
    full_name: str
    patient_id: Optional[int] = None
    doctor_id: Optional[int] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LogoutResponse(BaseModel):
    message: str = "Successfully logged out. Session revoked."

class UserOut(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    patient_id: Optional[int] = None
    doctor_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

# Department Schemas
class DepartmentBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    floor: Optional[str] = None
    icon: Optional[str] = "Activity"
    is_active: bool = True

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    floor: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None

class DepartmentStatusUpdate(BaseModel):
    is_active: bool

class DepartmentOut(DepartmentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Doctor & Schedule Schemas
class DoctorScheduleBase(BaseModel):
    day_of_week: int
    start_time: time
    end_time: time
    slot_duration_minutes: int = 30
    is_available: bool = True

class DoctorScheduleOut(DoctorScheduleBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class DoctorOut(BaseModel):
    id: int
    user_id: int
    full_name: str
    email: str
    department_id: int
    department_name: Optional[str] = None
    specialization: str
    qualification: str
    experience_years: int
    consultation_fee: float
    bio: Optional[str] = None
    room_number: Optional[str] = None
    rating: float
    schedules: List[DoctorScheduleOut] = []

    model_config = ConfigDict(from_attributes=True)

# Patient Schemas
class PatientCreate(BaseModel):
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    emergency_contact: Optional[str] = None
    address: Optional[str] = None
    medical_history_summary: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None

class PatientUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    emergency_contact: Optional[str] = None
    address: Optional[str] = None
    medical_history_summary: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None

class PatientProfileUpdate(BaseModel):
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    emergency_contact: Optional[str] = None
    address: Optional[str] = None
    medical_history_summary: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None

class PatientOut(BaseModel):
    id: int
    patient_number: Optional[str] = None
    user_id: Optional[int] = None
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    emergency_contact: Optional[str] = None
    address: Optional[str] = None
    medical_history_summary: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Staff Schemas
class StaffBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    department_id: Optional[int] = None
    job_title: Optional[str] = None
    shift: Optional[str] = None
    qualifications: Optional[str] = None

class StaffCreate(StaffBase):
    password: str
    specialization: Optional[str] = None
    consultation_fee: Optional[float] = 150.00
    experience_years: Optional[int] = 5
    room_number: Optional[str] = None
    bio: Optional[str] = None

class StaffUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[int] = None
    job_title: Optional[str] = None
    shift: Optional[str] = None
    qualifications: Optional[str] = None
    is_active: Optional[bool] = None
    specialization: Optional[str] = None
    consultation_fee: Optional[float] = None
    room_number: Optional[str] = None

class StaffStatusUpdate(BaseModel):
    is_active: bool

class StaffOut(BaseModel):
    id: int
    email: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    job_title: Optional[str] = None
    shift: Optional[str] = None
    qualifications: Optional[str] = None
    employee_id: Optional[str] = None
    doctor_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Appointment Schemas
class TimeSlot(BaseModel):
    start_time: time
    end_time: time
    is_available: bool

class AvailableSlotsOut(BaseModel):
    doctor_id: int
    date: date
    slots: List[TimeSlot]

class AppointmentCreate(BaseModel):
    patient_id: Optional[int] = None
    doctor_id: int
    department_id: int
    date: date
    start_time: time
    end_time: time
    type: AppointmentType = AppointmentType.IN_PERSON
    reason: str
    notes: Optional[str] = None

class AppointmentReschedule(BaseModel):
    new_date: date
    new_start_time: time
    new_end_time: time
    reason: Optional[str] = None

class AppointmentCancel(BaseModel):
    cancellation_reason: Optional[str] = None

class AppointmentCheckIn(BaseModel):
    notes: Optional[str] = None

class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus
    notes: Optional[str] = None

class AppointmentOut(BaseModel):
    id: int
    appointment_number: str
    patient_id: int
    patient_name: Optional[str] = None
    doctor_id: int
    doctor_name: Optional[str] = None
    doctor_specialization: Optional[str] = None
    department_id: int
    department_name: Optional[str] = None
    date: date
    start_time: time
    end_time: time
    type: AppointmentType
    status: AppointmentStatus
    check_in_time: Optional[datetime] = None
    reason: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Notification Schemas
class NotificationOut(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    type: str
    is_read: bool
    link: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Audit Log Schemas
class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Medical Document Schemas
class MedicalDocumentOut(BaseModel):
    id: int
    patient_id: int
    patient_name: Optional[str] = None
    file_name: str
    file_type: str
    file_size: int
    status: DocumentStatus
    summary: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    tags: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Medical Report & Prescription Schemas
class MedicalReportOut(BaseModel):
    id: int
    patient_id: int
    patient_name: Optional[str] = None
    doctor_id: int
    doctor_name: Optional[str] = None
    appointment_id: Optional[int] = None
    title: str
    diagnosis: str
    treatment_plan: str
    follow_up_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MedicationItem(BaseModel):
    name: str = Field(..., min_length=1)
    dosage: str = Field(..., min_length=1)
    frequency: str = Field(..., min_length=1)
    duration: Optional[str] = "7 days"
    instructions: Optional[str] = None
    refills: Optional[int] = 0

class PrescriptionCreate(BaseModel):
    patient_id: int
    appointment_id: Optional[int] = None
    medications: List[MedicationItem]
    instructions: Optional[str] = None

class PrescriptionOut(BaseModel):
    id: int
    patient_id: int
    patient_name: Optional[str] = None
    doctor_id: int
    doctor_name: Optional[str] = None
    appointment_id: Optional[int] = None
    medications: List[Dict[str, Any]]
    instructions: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# Room & Inventory Schemas
class RoomOut(BaseModel):
    id: int
    room_number: str
    department_id: int
    department_name: Optional[str] = None
    room_type: RoomType
    status: RoomStatus
    bed_count: int
    floor: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class InventoryOut(BaseModel):
    id: int
    item_name: str
    category: str
    quantity: int
    unit: str
    reorder_level: int
    status: InventoryStatus
    supplier: Optional[str] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# AI Chat Schemas
class AIChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None

class AIChatResponse(BaseModel):
    conversation_id: int
    message: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    sources: Optional[List[Dict[str, Any]]] = None

# Step 3 Clinical Documentation / EMR Schemas

class EncounterCreate(BaseModel):
    patient_id: int
    appointment_id: Optional[int] = None
    attending_doctor_id: int
    department_id: int
    encounter_type: EncounterType = EncounterType.OUTPATIENT

class EncounterStatusUpdate(BaseModel):
    status: EncounterStatus

class EncounterOut(BaseModel):
    id: int
    encounter_number: str
    patient_id: int
    patient_name: Optional[str] = None
    appointment_id: Optional[int] = None
    appointment_number: Optional[str] = None
    attending_doctor_id: int
    doctor_name: Optional[str] = None
    department_id: int
    department_name: Optional[str] = None
    encounter_type: EncounterType
    status: EncounterStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class VitalsCreate(BaseModel):
    temperature_c: Optional[float] = Field(None, ge=30.0, le=45.0, description="Body temperature in Celsius (30.0 - 45.0)")
    heart_rate: Optional[int] = Field(None, ge=30, le=300, description="Heart rate in bpm (30 - 300)")
    respiratory_rate: Optional[int] = Field(None, ge=5, le=100, description="Respiratory rate in breaths/min (5 - 100)")
    systolic_bp: Optional[int] = Field(None, ge=50, le=300, description="Systolic blood pressure in mmHg (50 - 300)")
    diastolic_bp: Optional[int] = Field(None, ge=30, le=200, description="Diastolic blood pressure in mmHg (30 - 200)")
    oxygen_saturation: Optional[float] = Field(None, ge=50.0, le=100.0, description="SpO2 percentage (50.0 - 100.0)")
    height_cm: Optional[float] = Field(None, gt=20.0, le=300.0, description="Height in centimeters (20.0 - 300.0)")
    weight_kg: Optional[float] = Field(None, gt=1.0, le=500.0, description="Weight in kilograms (1.0 - 500.0)")
    pain_score: Optional[int] = Field(None, ge=0, le=10, description="Pain score (0 - 10)")
    notes: Optional[str] = None

class VitalsUpdate(VitalsCreate):
    pass

class VitalsOut(BaseModel):
    id: int
    encounter_id: int
    patient_id: int
    recorded_by_id: int
    recorded_by_name: Optional[str] = None
    temperature_c: Optional[float] = None
    heart_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    oxygen_saturation: Optional[float] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    pain_score: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ClinicalNoteCreate(BaseModel):
    chief_complaint: Optional[str] = None
    history_of_present_illness: Optional[str] = None
    symptoms: Optional[str] = None
    medical_history_notes: Optional[str] = None
    examination_findings: Optional[str] = None
    vitals_summary: Optional[str] = None
    observations: Optional[str] = None
    clinical_assessment: Optional[str] = None
    differential_diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    patient_instructions: Optional[str] = None
    follow_up_instructions: Optional[str] = None
    follow_up_date: Optional[date] = None
    recommendations: Optional[str] = None

class ClinicalNoteUpdate(ClinicalNoteCreate):
    pass

class ClinicalNoteAmend(ClinicalNoteCreate):
    amendment_reason: str = Field(..., min_length=3, description="Required clinical reason for amending a finalized note")

class ClinicalNoteOut(BaseModel):
    id: int
    encounter_id: int
    patient_id: int
    doctor_id: int
    doctor_name: Optional[str] = None
    author_id: int
    author_name: Optional[str] = None
    status: ClinicalNoteStatus
    version: int
    parent_note_id: Optional[int] = None
    chief_complaint: Optional[str] = None
    history_of_present_illness: Optional[str] = None
    symptoms: Optional[str] = None
    medical_history_notes: Optional[str] = None
    examination_findings: Optional[str] = None
    vitals_summary: Optional[str] = None
    observations: Optional[str] = None
    clinical_assessment: Optional[str] = None
    differential_diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    patient_instructions: Optional[str] = None
    follow_up_instructions: Optional[str] = None
    follow_up_date: Optional[date] = None
    recommendations: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    finalized_at: Optional[datetime] = None
    amended_at: Optional[datetime] = None
    amendment_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class DiagnosisCreate(BaseModel):
    name: str = Field(..., min_length=2, description="Name or description of diagnosis")
    code: Optional[str] = None
    code_system: Optional[str] = None
    type: DiagnosisType = DiagnosisType.PRIMARY
    notes: Optional[str] = None

class DiagnosisOut(BaseModel):
    id: int
    encounter_id: int
    patient_id: int
    doctor_id: int
    doctor_name: Optional[str] = None
    name: str
    code: Optional[str] = None
    code_system: Optional[str] = None
    type: DiagnosisType
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ClinicalTimelineEntry(BaseModel):
    date: datetime
    entry_type: str
    encounter_id: int
    encounter_number: str
    doctor_name: Optional[str] = None
    department_name: Optional[str] = None
    summary: Optional[str] = None
    details: Dict[str, Any] = {}

# Step 4 Laboratory & Diagnostics Schemas

class LabTestDefinitionOut(BaseModel):
    id: int
    code: str
    name: str
    category: Optional[str] = None
    specimen_type: str
    default_unit: Optional[str] = None
    reference_range: Optional[str] = None
    description: Optional[str] = None
    turnaround_hours: Optional[int] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LabOrderItemCreate(BaseModel):
    test_id: int
    notes: Optional[str] = None

class LabOrderCreate(BaseModel):
    patient_id: int
    encounter_id: Optional[int] = None
    priority: LabOrderPriority = LabOrderPriority.ROUTINE
    clinical_indication: Optional[str] = None
    notes: Optional[str] = None
    items: List[LabOrderItemCreate] = Field(..., min_length=1)

class LabOrderCancel(BaseModel):
    reason: str = Field(..., min_length=3)

class LabSampleOut(BaseModel):
    id: int
    accession_number: str
    order_id: int
    specimen_type: str
    status: LabSampleStatus
    collected_at: Optional[datetime] = None
    collected_by_id: Optional[int] = None
    collected_by_name: Optional[str] = None
    received_at: Optional[datetime] = None
    received_by_id: Optional[int] = None
    received_by_name: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejected_by_id: Optional[int] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LabResultOut(BaseModel):
    id: int
    order_item_id: int
    patient_id: int
    test_id: int
    test_name: Optional[str] = None
    test_code: Optional[str] = None
    value: str
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    abnormal_flag: AbnormalFlag
    status: LabResultStatus
    comments: Optional[str] = None
    parent_result_id: Optional[int] = None
    entered_by_id: int
    entered_by_name: Optional[str] = None
    entered_at: datetime
    verified_by_id: Optional[int] = None
    verified_by_name: Optional[str] = None
    verified_at: Optional[datetime] = None
    amendment_reason: Optional[str] = None
    amended_by_id: Optional[int] = None
    amended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LabOrderItemOut(BaseModel):
    id: int
    order_id: int
    test_id: int
    test_name: Optional[str] = None
    test_code: Optional[str] = None
    sample_id: Optional[int] = None
    sample_accession: Optional[str] = None
    status: LabOrderItemStatus
    notes: Optional[str] = None
    result: Optional[LabResultOut] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LabOrderOut(BaseModel):
    id: int
    order_number: str
    patient_id: int
    patient_name: Optional[str] = None
    ordering_doctor_id: int
    doctor_name: Optional[str] = None
    encounter_id: Optional[int] = None
    encounter_number: Optional[str] = None
    status: LabOrderStatus
    priority: LabOrderPriority
    clinical_indication: Optional[str] = None
    notes: Optional[str] = None
    ordered_at: datetime
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    items: List[LabOrderItemOut] = []
    samples: List[LabSampleOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SampleCollectIn(BaseModel):
    specimen_type: str
    item_ids: List[int] = Field(..., min_length=1)

class SampleReceiveIn(BaseModel):
    notes: Optional[str] = None

class SampleRejectIn(BaseModel):
    rejection_reason: str = Field(..., min_length=3)

class ResultEntryIn(BaseModel):
    value: str = Field(..., min_length=1)
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    abnormal_flag: AbnormalFlag = AbnormalFlag.NORMAL
    comments: Optional[str] = None

class ResultVerifyIn(BaseModel):
    comments: Optional[str] = None

class ResultAmendIn(BaseModel):
    value: str = Field(..., min_length=1)
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    abnormal_flag: AbnormalFlag = AbnormalFlag.NORMAL
    amendment_reason: str = Field(..., min_length=5)
    comments: Optional[str] = None
