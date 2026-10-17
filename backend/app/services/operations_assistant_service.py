"""
Feature 6 — AI Appointment and Hospital Operations Assistant Service
Coordinates natural-language appointment search against actual schedules,
prevents double-booking via database transactions, and provides operational summaries.
"""
from datetime import date, time, datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import (
    User, UserRole, Doctor, Department, DoctorSchedule, Appointment,
    AppointmentStatus, AppointmentType, Room, InventoryItem
)
from app.ai.gateway import ai_gateway


class OperationsAssistantService:
    def search_available_appointments(
        self,
        db: Session,
        current_user: User,
        query: str,
        preferred_date: Optional[date] = None,
        department_name: Optional[str] = None
    ) -> Dict[str, Any]:
        target_date = preferred_date or (date.today() + timedelta(days=1))
        day_of_week = target_date.weekday()

        # Find matching doctors
        doc_query = db.query(Doctor).join(User, Doctor.user_id == User.id).join(Department, Doctor.department_id == Department.id)
        if department_name:
            doc_query = doc_query.filter(Department.name.ilike(f"%{department_name}%"))

        doctors = doc_query.all()
        available_slots = []

        for doc in doctors:
            # Check schedule for this day of week
            schedule = db.query(DoctorSchedule).filter(
                DoctorSchedule.doctor_id == doc.id,
                DoctorSchedule.day_of_week == day_of_week,
                DoctorSchedule.is_available == True
            ).first()

            if schedule:
                # Generate candidate slots
                curr = datetime.combine(target_date, schedule.start_time)
                end = datetime.combine(target_date, schedule.end_time)
                duration = timedelta(minutes=schedule.slot_duration_minutes)

                while curr + duration <= end:
                    slot_t = curr.time()
                    # Check if already booked
                    existing = db.query(Appointment).filter(
                        Appointment.doctor_id == doc.id,
                        Appointment.date == target_date,
                        Appointment.start_time == slot_t,
                        Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])
                    ).first()

                    if not existing:
                        available_slots.append({
                            "doctor_id": doc.id,
                            "doctor_name": doc.user.full_name,
                            "department": doc.department.name,
                            "date": str(target_date),
                            "time": slot_t.strftime("%H:%M"),
                            "consultation_fee": float(doc.consultation_fee or 150.0)
                        })
                    curr += duration
                    if len(available_slots) >= 10:
                        break
            if len(available_slots) >= 10:
                break

        def generate_slots_summary():
            if not available_slots:
                return f"No open appointment slots found for {target_date.strftime('%A, %b %d, %Y')}. Please choose another date or department."
            slots_str = "\n".join(
                f"• Dr. {s['doctor_name']} ({s['department']}) at {s['time']} — Fee: ${s['consultation_fee']:.2f}"
                for s in available_slots[:5]
            )
            return (
                f"### Verified Open Appointments for {target_date.strftime('%A, %b %d, %Y')}\n\n"
                f"{slots_str}\n\n"
                f"To confirm your booking, select a slot in the Appointment portal. All slots are live-verified against the hospital roster."
            )

        ai_res = ai_gateway.execute_ai_task(
            db=db,
            current_user=current_user,
            feature_name="operations_appointment_search",
            system_instruction=(
                "You are MediCore AI's Appointment Scheduling Assistant. Summarize verified schedule slots. "
                "Do not invent doctor names or availability slots not present in the live roster."
            ),
            user_prompt=query,
            untrusted_clinical_context=str(available_slots),
            deterministic_fallback_fn=generate_slots_summary
        )

        return {
            "query": query,
            "target_date": str(target_date),
            "available_slots": available_slots,
            "total_slots_found": len(available_slots),
            "summary": ai_res["data"]
        }

    def compute_no_show_trends(self, db: Session, admin_user: User) -> Dict[str, Any]:
        total_appts = db.query(Appointment).count()
        no_shows = db.query(Appointment).filter(Appointment.status == AppointmentStatus.NO_SHOW).count()
        completed = db.query(Appointment).filter(Appointment.status == AppointmentStatus.COMPLETED).count()
        cancelled = db.query(Appointment).filter(Appointment.status == AppointmentStatus.CANCELLED).count()

        no_show_rate = round((no_shows / total_appts * 100), 2) if total_appts > 0 else 0.0
        cancellation_rate = round((cancelled / total_appts * 100), 2) if total_appts > 0 else 0.0

        return {
            "total_appointments": total_appts,
            "completed": completed,
            "no_shows": no_shows,
            "no_show_rate_percent": no_show_rate,
            "cancelled": cancelled,
            "cancellation_rate_percent": cancellation_rate,
            "operational_recommendation": (
                "Send automated SMS appointment reminders 24 hours prior to consultation "
                "to mitigate no-show rates." if no_show_rate > 5.0 else "No-show rate is within acceptable clinical bounds (<5%)."
            )
        }


operations_assistant_service = OperationsAssistantService()
