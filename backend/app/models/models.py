import enum
from datetime import datetime, date, time
from app.core.datetime_utils import utc_now
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Time, 
    ForeignKey, Text, Numeric, Enum, JSON, Index, text
)
from sqlalchemy.orm import relationship
from app.core.database import Base

class UserRole(str, enum.Enum):
    PATIENT = "PATIENT"
    DOCTOR = "DOCTOR"
    NURSE = "NURSE"
    RECEPTIONIST = "RECEPTIONIST"
    STAFF = "STAFF"
    ADMIN = "ADMIN"
    PHARMACIST = "PHARMACIST"
    LAB_TECHNICIAN = "LAB_TECHNICIAN"

class DraftStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class TriageAcuity(str, enum.Enum):
    LEVEL_1_RESUSCITATION = "LEVEL_1_RESUSCITATION"
    LEVEL_2_EMERGENT = "LEVEL_2_EMERGENT"
    LEVEL_3_URGENT = "LEVEL_3_URGENT"
    LEVEL_4_LESS_URGENT = "LEVEL_4_LESS_URGENT"
    LEVEL_5_NON_URGENT = "LEVEL_5_NON_URGENT"

class AppointmentType(str, enum.Enum):
    IN_PERSON = "IN_PERSON"
    TELECONSULTATION = "TELECONSULTATION"

class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"

class DocumentStatus(str, enum.Enum):
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class RoomType(str, enum.Enum):
    ICU = "ICU"
    GENERAL = "GENERAL"
    OPD = "OPD"
    OPERATION_THEATER = "OPERATION_THEATER"
    PRIVATE = "PRIVATE"

class RoomStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    MAINTENANCE = "MAINTENANCE"

class InventoryStatus(str, enum.Enum):
    IN_STOCK = "IN_STOCK"
    LOW_STOCK = "LOW_STOCK"
    CRITICAL = "CRITICAL"

class EncounterType(str, enum.Enum):
    OUTPATIENT = "OUTPATIENT"
    FOLLOW_UP = "FOLLOW_UP"
    WALK_IN = "WALK_IN"

class EncounterStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class ClinicalNoteStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    FINAL = "FINAL"
    AMENDED = "AMENDED"

class DiagnosisType(str, enum.Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    WORKING = "WORKING"
    SUSPECTED = "SUSPECTED"

class LabOrderPriority(str, enum.Enum):
    ROUTINE = "ROUTINE"
    URGENT = "URGENT"
    STAT = "STAT"

class LabOrderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ORDERED = "ORDERED"
    PARTIALLY_COLLECTED = "PARTIALLY_COLLECTED"
    COLLECTED = "COLLECTED"
    PROCESSING = "PROCESSING"
    RESULTS_PENDING = "RESULTS_PENDING"
    VERIFIED = "VERIFIED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class LabOrderItemStatus(str, enum.Enum):
    PENDING = "PENDING"
    COLLECTED = "COLLECTED"
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class LabSampleStatus(str, enum.Enum):
    PENDING = "PENDING"
    COLLECTED = "COLLECTED"
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"

class LabResultStatus(str, enum.Enum):
    PENDING = "PENDING"
    ENTERED = "ENTERED"
    VERIFIED = "VERIFIED"
    FINAL = "FINAL"
    AMENDED = "AMENDED"

class AbnormalFlag(str, enum.Enum):
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    LOW = "LOW"
    ABNORMAL = "ABNORMAL"
    CRITICAL = "CRITICAL"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.PATIENT, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    phone = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    patient_profile = relationship("Patient", back_populates="user", uselist=False, cascade="all, delete-orphan")
    doctor_profile = relationship("Doctor", back_populates="user", uselist=False, cascade="all, delete-orphan")
    staff_profile = relationship("StaffProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    ai_conversations = relationship("AIConversation", back_populates="user", cascade="all, delete-orphan")

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    head_doctor_id = Column(Integer, nullable=True)
    floor = Column(String(50), nullable=True)
    icon = Column(String(50), default="Activity")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    doctors = relationship("Doctor", back_populates="department")
    staff_members = relationship("StaffProfile", back_populates="department")
    services = relationship("HospitalService", back_populates="department")
    rooms = relationship("Room", back_populates="department")
    appointments = relationship("Appointment", back_populates="department")
    encounters = relationship("Encounter", back_populates="department")

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_number = Column(String(50), unique=True, index=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=True)
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    blood_group = Column(String(10), nullable=True)
    emergency_contact = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    medical_history_summary = Column(Text, nullable=True)
    insurance_provider = Column(String(100), nullable=True)
    insurance_policy_number = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="patient_profile")
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    medical_documents = relationship("MedicalDocument", back_populates="patient", cascade="all, delete-orphan")
    medical_reports = relationship("MedicalReport", back_populates="patient", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="patient", cascade="all, delete-orphan")
    notes = relationship("PatientNote", back_populates="patient", cascade="all, delete-orphan")
    encounters = relationship("Encounter", back_populates="patient", cascade="all, delete-orphan")
    lab_orders = relationship("LabOrder", back_populates="patient")
    lab_results = relationship("LabResult", back_populates="patient")

    @property
    def display_name(self) -> str:
        if self.user and self.user.full_name:
            return self.user.full_name
        return self.full_name or "Unknown Patient"

    @property
    def display_email(self) -> str | None:
        if self.user and self.user.email:
            return self.user.email
        return self.email

    @property
    def display_phone(self) -> str | None:
        if self.user and self.user.phone:
            return self.user.phone
        return self.phone

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    specialization = Column(String(150), nullable=False)
    qualification = Column(String(150), nullable=False)
    experience_years = Column(Integer, default=5)
    consultation_fee = Column(Numeric(10, 2), default=150.00)
    bio = Column(Text, nullable=True)
    room_number = Column(String(50), nullable=True)
    rating = Column(Numeric(3, 2), default=4.9)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="doctor_profile")
    department = relationship("Department", back_populates="doctors")
    schedules = relationship("DoctorSchedule", back_populates="doctor", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="doctor")
    reports = relationship("MedicalReport", back_populates="doctor")
    prescriptions = relationship("Prescription", back_populates="doctor")
    notes = relationship("PatientNote", back_populates="doctor")
    encounters = relationship("Encounter", back_populates="attending_doctor")
    lab_orders = relationship("LabOrder", back_populates="ordered_by_doctor")

class DoctorSchedule(Base):
    __tablename__ = "doctor_schedules"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    slot_duration_minutes = Column(Integer, default=30, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    doctor = relationship("Doctor", back_populates="schedules")

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    appointment_number = Column(String(50), unique=True, index=True, nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    type = Column(Enum(AppointmentType), default=AppointmentType.IN_PERSON, nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.CONFIRMED, nullable=False, index=True)
    check_in_time = Column(DateTime, nullable=True)
    reason = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    department = relationship("Department", back_populates="appointments")
    report = relationship("MedicalReport", back_populates="appointment", uselist=False)
    prescription = relationship("Prescription", back_populates="appointment", uselist=False)
    encounter = relationship("Encounter", back_populates="appointment", uselist=False)

    __table_args__ = (
        Index("idx_appointments_doc_date", "doctor_id", "date"),
        Index("idx_appointments_patient_date", "patient_id", "date"),
        # Partial unique index ensuring only ACTIVE appointments reserve a slot
        Index(
            "uq_doctor_active_slot",
            "doctor_id", "date", "start_time",
            unique=True,
            postgresql_where=text("status != 'CANCELLED'"),
            sqlite_where=text("status != 'CANCELLED'")
        ),
    )

class MedicalDocument(Base):
    __tablename__ = "medical_documents"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    file_path = Column(String(500), nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADING, nullable=False)
    extracted_data = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)
    tags = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="medical_documents")

    __table_args__ = (
        Index("idx_documents_patient", "patient_id"),
    )

class MedicalReport(Base):
    __tablename__ = "medical_reports"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    title = Column(String(200), nullable=False)
    diagnosis = Column(Text, nullable=False)
    treatment_plan = Column(Text, nullable=False)
    follow_up_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="medical_reports")
    doctor = relationship("Doctor", back_populates="reports")
    appointment = relationship("Appointment", back_populates="report")

    __table_args__ = (
        Index("idx_medical_reports_patient", "patient_id"),
    )

class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    medications = Column(JSON, nullable=False)  # list of {name, dosage, frequency, duration, instructions}
    instructions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="prescriptions")
    doctor = relationship("Doctor", back_populates="prescriptions")
    appointment = relationship("Appointment", back_populates="prescription")

    @property
    def medication_name(self) -> str:
        if isinstance(self.medications, list) and len(self.medications) > 0:
            first = self.medications[0]
            if isinstance(first, dict):
                return first.get("name", "")
            return str(first)
        return ""

    @property
    def dosage(self) -> str:
        if isinstance(self.medications, list) and len(self.medications) > 0:
            first = self.medications[0]
            if isinstance(first, dict):
                return first.get("dosage", "")
        return ""

    @property
    def frequency(self) -> str:
        if isinstance(self.medications, list) and len(self.medications) > 0:
            first = self.medications[0]
            if isinstance(first, dict):
                return first.get("frequency", "")
        return ""

    __table_args__ = (
        Index("idx_prescriptions_patient", "patient_id"),
    )

class PatientNote(Base):
    __tablename__ = "patient_notes"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    note = Column(Text, nullable=False)
    is_private = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="notes")
    doctor = relationship("Doctor", back_populates="notes")

class HospitalService(Base):
    __tablename__ = "hospital_services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    duration_minutes = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    department = relationship("Department", back_populates="services")

class HospitalPolicy(Base):
    __tablename__ = "hospital_policies"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    effective_date = Column(Date, nullable=True)
    is_published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_number = Column(String(50), unique=True, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    room_type = Column(Enum(RoomType), default=RoomType.GENERAL, nullable=False)
    status = Column(Enum(RoomStatus), default=RoomStatus.AVAILABLE, nullable=False)
    bed_count = Column(Integer, default=1)
    floor = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    department = relationship("Department", back_populates="rooms")

class InventoryItem(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    unit = Column(String(50), nullable=False)
    reorder_level = Column(Integer, default=10, nullable=False)
    status = Column(Enum(InventoryStatus), default=InventoryStatus.IN_STOCK, nullable=False)
    supplier = Column(String(200), nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="INFO")  # APPOINTMENT, REMINDER, DOCUMENT, SYSTEM
    is_read = Column(Boolean, default=False, nullable=False)
    link = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("idx_notifications_user_unread", "user_id", "is_read"),
    )

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_logs_user_created", "user_id", "created_at"),
    )

class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_context = Column(Enum(UserRole), nullable=False)
    title = Column(String(200), default="New Conversation")
    created_at = Column(DateTime, default=utc_now, nullable=False)

    user = relationship("User", back_populates="ai_conversations")
    messages = relationship("AIMessage", back_populates="conversation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_ai_conversations_user", "user_id", "created_at"),
    )

class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String(50), nullable=False)  # USER, ASSISTANT, TOOL
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, nullable=True)
    tool_results = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    conversation = relationship("AIConversation", back_populates="messages")

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding_meta = Column(JSON, nullable=True)

    document = relationship("KnowledgeDocument", back_populates="chunks")

    __table_args__ = (
        Index("idx_knowledge_chunks_doc", "document_id"),
    )

class StaffProfile(Base):
    __tablename__ = "staff_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    employee_id = Column(String(50), unique=True, index=True, nullable=True)
    job_title = Column(String(100), nullable=True)
    shift = Column(String(50), nullable=True)
    qualifications = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="staff_profile")
    department = relationship("Department", back_populates="staff_members")

class Encounter(Base):
    __tablename__ = "encounters"

    id = Column(Integer, primary_key=True, index=True)
    encounter_number = Column(String(50), unique=True, index=True, nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True, index=True)
    attending_doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    encounter_type = Column(Enum(EncounterType), default=EncounterType.OUTPATIENT, nullable=False)
    status = Column(Enum(EncounterStatus), default=EncounterStatus.OPEN, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    patient = relationship("Patient", back_populates="encounters")
    appointment = relationship("Appointment", back_populates="encounter")
    attending_doctor = relationship("Doctor", back_populates="encounters")
    department = relationship("Department", back_populates="encounters")
    vitals = relationship("EncounterVitals", back_populates="encounter", cascade="all, delete-orphan")
    clinical_notes = relationship("ClinicalNote", back_populates="encounter", cascade="all, delete-orphan")
    diagnoses = relationship("ClinicalDiagnosis", back_populates="encounter", cascade="all, delete-orphan")
    lab_orders = relationship("LabOrder", back_populates="encounter")

    __table_args__ = (
        Index(
            "uq_appointment_encounter",
            "appointment_id",
            unique=True,
            postgresql_where=text("appointment_id IS NOT NULL"),
            sqlite_where=text("appointment_id IS NOT NULL")
        ),
        Index("idx_encounters_patient_date", "patient_id", "created_at"),
        Index("idx_encounters_doctor_date", "attending_doctor_id", "created_at"),
    )

class EncounterVitals(Base):
    __tablename__ = "encounter_vitals"

    id = Column(Integer, primary_key=True, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    recorded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    temperature_c = Column(Numeric(4, 1), nullable=True)
    heart_rate = Column(Integer, nullable=True)
    respiratory_rate = Column(Integer, nullable=True)
    systolic_bp = Column(Integer, nullable=True)
    diastolic_bp = Column(Integer, nullable=True)
    oxygen_saturation = Column(Numeric(4, 1), nullable=True)
    height_cm = Column(Numeric(5, 1), nullable=True)
    weight_kg = Column(Numeric(5, 1), nullable=True)
    bmi = Column(Numeric(4, 1), nullable=True)
    pain_score = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    encounter = relationship("Encounter", back_populates="vitals")
    patient = relationship("Patient")
    recorded_by = relationship("User")

    __table_args__ = (
        Index("idx_vitals_encounter", "encounter_id"),
        Index("idx_vitals_patient_created", "patient_id", "created_at"),
    )

class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id = Column(Integer, primary_key=True, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(ClinicalNoteStatus), default=ClinicalNoteStatus.DRAFT, nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    parent_note_id = Column(Integer, ForeignKey("clinical_notes.id", ondelete="SET NULL"), nullable=True)

    # Subjective
    chief_complaint = Column(Text, nullable=True)
    history_of_present_illness = Column(Text, nullable=True)
    symptoms = Column(Text, nullable=True)
    medical_history_notes = Column(Text, nullable=True)

    # Objective
    examination_findings = Column(Text, nullable=True)
    vitals_summary = Column(Text, nullable=True)
    observations = Column(Text, nullable=True)

    # Assessment
    clinical_assessment = Column(Text, nullable=True)
    differential_diagnosis = Column(Text, nullable=True)

    # Plan
    treatment_plan = Column(Text, nullable=True)
    patient_instructions = Column(Text, nullable=True)
    follow_up_instructions = Column(Text, nullable=True)
    follow_up_date = Column(Date, nullable=True)
    recommendations = Column(Text, nullable=True)

    # Timestamps & Metadata
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    finalized_at = Column(DateTime, nullable=True)
    amended_at = Column(DateTime, nullable=True)
    amendment_reason = Column(Text, nullable=True)

    encounter = relationship("Encounter", back_populates="clinical_notes")
    patient = relationship("Patient")
    doctor = relationship("Doctor")
    author = relationship("User", foreign_keys=[author_id])
    parent_note = relationship("ClinicalNote", remote_side=[id])

    __table_args__ = (
        Index("idx_clinical_notes_encounter", "encounter_id"),
        Index("idx_clinical_notes_patient_created", "patient_id", "created_at"),
        Index("idx_clinical_notes_status", "status"),
    )

class ClinicalDiagnosis(Base):
    __tablename__ = "clinical_diagnoses"

    id = Column(Integer, primary_key=True, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True)
    code_system = Column(String(50), nullable=True)
    type = Column(Enum(DiagnosisType), default=DiagnosisType.PRIMARY, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    encounter = relationship("Encounter", back_populates="diagnoses")
    patient = relationship("Patient")
    doctor = relationship("Doctor")

    __table_args__ = (
        Index("idx_clinical_diagnoses_encounter", "encounter_id"),
        Index("idx_clinical_diagnoses_patient", "patient_id"),
    )

# =========================================================================
# STEP 4: LABORATORY & DIAGNOSTICS MODELS
# =========================================================================

class LabTestDefinition(Base):
    __tablename__ = "lab_test_definitions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    specimen_type = Column(String(100), nullable=False)
    category = Column(String(100), nullable=False)
    default_unit = Column(String(50), nullable=True)
    default_reference_range = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    order_items = relationship("LabOrderItem", back_populates="test_definition")

    __table_args__ = (
        Index("idx_lab_tests_category", "category"),
        Index("idx_lab_tests_active", "is_active"),
    )

class LabOrder(Base):
    __tablename__ = "lab_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False)
    encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    ordered_by_doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    priority = Column(Enum(LabOrderPriority), default=LabOrderPriority.ROUTINE, nullable=False)
    status = Column(Enum(LabOrderStatus), default=LabOrderStatus.ORDERED, nullable=False, index=True)
    clinical_indication = Column(Text, nullable=True)
    ordered_at = Column(DateTime, default=utc_now, nullable=False)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    encounter = relationship("Encounter", back_populates="lab_orders")
    patient = relationship("Patient", back_populates="lab_orders")
    ordered_by_doctor = relationship("Doctor", back_populates="lab_orders")
    department = relationship("Department")
    items = relationship("LabOrderItem", back_populates="lab_order", cascade="all, delete-orphan")
    samples = relationship("LabSample", back_populates="lab_order", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_lab_orders_patient_date", "patient_id", "ordered_at"),
        Index("idx_lab_orders_doctor_date", "ordered_by_doctor_id", "ordered_at"),
        Index("idx_lab_orders_status", "status"),
    )

class LabSample(Base):
    __tablename__ = "lab_samples"

    id = Column(Integer, primary_key=True, index=True)
    accession_number = Column(String(50), unique=True, index=True, nullable=False)
    lab_order_id = Column(Integer, ForeignKey("lab_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    sample_type = Column(String(100), nullable=False)
    collected_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    collected_at = Column(DateTime, nullable=True)
    received_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    received_at = Column(DateTime, nullable=True)
    status = Column(Enum(LabSampleStatus), default=LabSampleStatus.PENDING, nullable=False, index=True)
    rejection_reason = Column(Text, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejected_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    lab_order = relationship("LabOrder", back_populates="samples")
    patient = relationship("Patient")
    collected_by = relationship("User", foreign_keys=[collected_by_id])
    received_by = relationship("User", foreign_keys=[received_by_id])
    rejected_by = relationship("User", foreign_keys=[rejected_by_id])
    order_items = relationship("LabOrderItem", back_populates="sample")

    __table_args__ = (
        Index("idx_lab_samples_status", "status"),
        Index("idx_lab_samples_patient", "patient_id"),
    )

class LabOrderItem(Base):
    __tablename__ = "lab_order_items"

    id = Column(Integer, primary_key=True, index=True)
    lab_order_id = Column(Integer, ForeignKey("lab_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    test_definition_id = Column(Integer, ForeignKey("lab_test_definitions.id"), nullable=False, index=True)
    sample_id = Column(Integer, ForeignKey("lab_samples.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(Enum(LabOrderItemStatus), default=LabOrderItemStatus.PENDING, nullable=False, index=True)
    specimen_type = Column(String(100), nullable=True)
    instructions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    lab_order = relationship("LabOrder", back_populates="items")
    test_definition = relationship("LabTestDefinition", back_populates="order_items")
    sample = relationship("LabSample", back_populates="order_items")
    results = relationship("LabResult", back_populates="order_item")

    __table_args__ = (
        Index("idx_lab_order_items_order", "lab_order_id"),
        Index("idx_lab_order_items_status", "status"),
    )

class LabResult(Base):
    __tablename__ = "lab_results"

    id = Column(Integer, primary_key=True, index=True)
    lab_order_item_id = Column(Integer, ForeignKey("lab_order_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    entered_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(Enum(LabResultStatus), default=LabResultStatus.ENTERED, nullable=False, index=True)
    value = Column(Text, nullable=False)
    numeric_value = Column(Numeric(10, 3), nullable=True)
    unit = Column(String(50), nullable=True)
    reference_range = Column(String(100), nullable=True)
    abnormal_flag = Column(Enum(AbnormalFlag), default=AbnormalFlag.NORMAL, nullable=True)
    comments = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    parent_result_id = Column(Integer, ForeignKey("lab_results.id"), nullable=True)
    amendment_reason = Column(Text, nullable=True)
    entered_at = Column(DateTime, default=utc_now, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    amended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    order_item = relationship("LabOrderItem", back_populates="results")
    patient = relationship("Patient", back_populates="lab_results")
    entered_by = relationship("User", foreign_keys=[entered_by_id])
    verified_by = relationship("User", foreign_keys=[verified_by_id])
    parent_result = relationship("LabResult", remote_side=[id])

    __table_args__ = (
        Index("idx_lab_results_patient_date", "patient_id", "created_at"),
        Index("idx_lab_results_item", "lab_order_item_id"),
        Index("idx_lab_results_status", "status"),
    )

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    revoked_at = Column(DateTime, default=utc_now, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User")

class AIGovernanceMetric(Base):
    __tablename__ = "ai_governance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    feature_name = Column(String(100), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Numeric(10, 6), default=0.0)
    latency_ms = Column(Numeric(10, 2), default=0.0)
    status_code = Column(Integer, default=200)
    flagged_security = Column(Boolean, default=False)
    security_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    user = relationship("User")

class ClinicalDocumentChunk(Base):
    __tablename__ = "clinical_document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("medical_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    section_title = Column(String(150), nullable=True)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    document = relationship("MedicalDocument")
    patient = relationship("Patient")

    __table_args__ = (
        Index("idx_clinical_chunks_patient", "patient_id"),
        Index("idx_clinical_chunks_doc_chunk", "document_id", "chunk_index"),
    )

class AIDocumentDraft(Base):
    __tablename__ = "ai_document_drafts"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True, index=True)
    draft_type = Column(String(50), nullable=False)  # SOAP_NOTE, DISCHARGE_SUMMARY, REFERRAL_LETTER, CLINICAL_HANDOFF
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    structured_data = Column(JSON, nullable=True)
    status = Column(Enum(DraftStatus), default=DraftStatus.DRAFT, nullable=False, index=True)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    patient = relationship("Patient")
    doctor = relationship("Doctor")
    approved_by = relationship("User", foreign_keys=[approved_by_id])

class TriageAssessment(Base):
    __tablename__ = "triage_assessments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True, index=True)
    assessed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    news2_score = Column(Integer, nullable=False)
    acuity_level = Column(Enum(TriageAcuity), nullable=False, index=True)
    chief_complaint = Column(Text, nullable=False)
    vitals_snapshot = Column(JSON, nullable=True)
    clinical_flags = Column(JSON, nullable=True)
    escalation_reason = Column(Text, nullable=True)
    is_clinician_approved = Column(Boolean, default=False)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    patient = relationship("Patient")
    encounter = relationship("Encounter")
    assessed_by = relationship("User", foreign_keys=[assessed_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])

class PharmacySafetyAlert(Base):
    __tablename__ = "pharmacy_safety_alerts"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    alert_type = Column(String(50), nullable=False)  # DRUG_INTERACTION, ALLERGY_CONFLICT, DUPLICATE_THERAPY, DOSAGE_WARNING
    severity = Column(String(20), nullable=False)    # CRITICAL, HIGH, MODERATE, LOW
    medication_names = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False)
    clinician_override_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    patient = relationship("Patient")
    prescription = relationship("Prescription")

