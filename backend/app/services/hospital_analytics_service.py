"""
Feature 10 — AI Hospital Analytics Service
Executes parameterized, pre-aggregated analytical queries to provide actionable operations intelligence.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import (
    User, UserRole, Appointment, Department, Room, 
    RoomStatus, InventoryItem, LabOrder, LabOrderStatus
)
from app.ai.gateway import ai_gateway


class HospitalAnalyticsService:
    def get_operational_analytics_summary(self, db: Session, admin_user: User) -> Dict[str, Any]:
        # 1. Department Demand
        dept_stats = db.query(
            Department.name,
            func.count(Appointment.id).label("total_appointments")
        ).join(Appointment, Department.id == Appointment.department_id, isouter=True)\
         .group_by(Department.name)\
         .order_by(func.count(Appointment.id).desc()).all()

        department_distribution = [{"department": name, "appointments": count} for name, count in dept_stats]

        # 2. Bed & Room Telemetry
        total_rooms = db.query(Room).count()
        available_rooms = db.query(Room).filter(Room.status == RoomStatus.AVAILABLE).count()
        occupied_rooms = db.query(Room).filter(Room.status == RoomStatus.OCCUPIED).count()
        maintenance_rooms = db.query(Room).filter(Room.status == RoomStatus.MAINTENANCE).count()
        occupancy_rate = round((occupied_rooms / total_rooms * 100), 1) if total_rooms > 0 else 0.0

        # 3. Lab Turnaround & Order Volume
        total_lab_orders = db.query(LabOrder).count()
        completed_labs = db.query(LabOrder).filter(LabOrder.status == LabOrderStatus.COMPLETED).count()
        pending_labs = db.query(LabOrder).filter(LabOrder.status.in_([LabOrderStatus.ORDERED, LabOrderStatus.COLLECTED, LabOrderStatus.PROCESSING])).count()

        # 4. Inventory Health
        total_inventory_items = db.query(InventoryItem).count()
        critical_inventory = db.query(InventoryItem).filter(InventoryItem.quantity <= InventoryItem.reorder_level).count()

        analytics_data = {
            "department_distribution": department_distribution,
            "bed_census": {
                "total_rooms": total_rooms,
                "available": available_rooms,
                "occupied": occupied_rooms,
                "maintenance": maintenance_rooms,
                "occupancy_rate_percent": occupancy_rate
            },
            "lab_operations": {
                "total_orders": total_lab_orders,
                "completed": completed_labs,
                "pending": pending_labs
            },
            "inventory_health": {
                "total_catalog_items": total_inventory_items,
                "items_at_or_below_reorder_level": critical_inventory
            }
        }

        def generate_executive_insights():
            top_dept = department_distribution[0]["department"] if department_distribution else "General Medicine"
            top_count = department_distribution[0]["appointments"] if department_distribution else 0
            return (
                f"### MediCore Executive Operations Briefing\n\n"
                f"- **Clinical Demand**: Highest consultation load is in **{top_dept}** ({top_count} bookings).\n"
                f"- **Bed Capacity**: Current hospital inpatient occupancy is at **{occupancy_rate}%** ({occupied_rooms}/{total_rooms} beds in active service).\n"
                f"- **Diagnostic Flow**: {completed_labs} of {total_lab_orders} laboratory orders finalized; {pending_labs} in processing.\n"
                f"- **Supply Chain**: {critical_inventory} inventory line-items currently flagged at or below safety reorder threshold.\n\n"
                f"**Recommendation**: Optimize nursing shift allocation to {top_dept} and trigger purchase requisition for critical stock items."
            )

        ai_res = ai_gateway.execute_ai_task(
            db=db,
            current_user=admin_user,
            feature_name="hospital_analytics_intelligence",
            system_instruction=(
                "You are MediCore AI's Hospital Analytics Intelligence Director. Analyze pre-computed hospital aggregate metrics. "
                "Synthesize operational efficiency, department bottlenecks, and capacity telemetry for executive administrators. "
                "Do not run arbitrary SQL. Base findings solely on the supplied summary metrics."
            ),
            user_prompt="Provide executive operations analysis and department workload briefing.",
            untrusted_clinical_context=str(analytics_data),
            deterministic_fallback_fn=generate_executive_insights
        )

        return {
            "metrics": analytics_data,
            "executive_summary": ai_res["data"],
            "generated_by": admin_user.full_name,
            "is_aggregate_only": True
        }


hospital_analytics_service = HospitalAnalyticsService()
