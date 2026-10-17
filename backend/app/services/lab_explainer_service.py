"""
Feature 7 — AI Laboratory Report Explainer Service
Interprets verified diagnostic laboratory findings using authoritative reference ranges.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import User, UserRole, Patient, LabResult, LabTestDefinition, AbnormalFlag
from app.ai.gateway import ai_gateway


class LabReportExplainerService:
    def explain_lab_result(self, db: Session, current_user: User, lab_result_id: int) -> Dict[str, Any]:
        result = db.query(LabResult).filter(LabResult.id == lab_result_id).first()
        if not result:
            raise HTTPException(status_code=404, detail="Lab result not found.")

        # Check authorization
        if current_user.role == UserRole.PATIENT:
            if not current_user.patient_profile or result.patient_id != current_user.patient_profile.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Patients may only view their own lab results.")

        test_def = result.order_item.test_definition if result.order_item else None
        test_name = test_def.name if test_def else "Laboratory Investigation"
        test_code = test_def.code if test_def else "LAB"
        specimen = test_def.specimen_type if test_def else "Serum"
        ref_range = result.reference_range or (test_def.default_reference_range if test_def else "N/A")
        unit = result.unit or (test_def.default_unit if test_def else "")
        flag = result.abnormal_flag.value if result.abnormal_flag else "NORMAL"

        # Longitudinal previous result comparison
        previous_results = db.query(LabResult).join(LabResult.order_item).filter(
            LabResult.patient_id == result.patient_id,
            LabResult.id != result.id,
            LabResult.created_at < result.created_at
        ).order_by(LabResult.created_at.desc()).limit(3).all()

        history_trends = []
        for pr in previous_results:
            history_trends.append({
                "date": pr.created_at.strftime("%Y-%m-%d"),
                "value": f"{pr.value} {pr.unit or ''}".strip(),
                "flag": pr.abnormal_flag.value if pr.abnormal_flag else "NORMAL"
            })

        lab_data_context = (
            f"Test: {test_name} ({test_code})\n"
            f"Specimen: {specimen}\n"
            f"Measured Value: {result.value} {unit}\n"
            f"Reference Range: {ref_range}\n"
            f"Status Flag: {flag}\n"
            f"Historical Results: {history_trends}\n"
        )

        def generate_explanation():
            trend_str = f" Previous readings: {', '.join(h['value'] + ' on ' + h['date'] for h in history_trends)}." if history_trends else " No previous historical readings on file for baseline comparison."
            status_desc = "within the expected normal reference range" if flag == "NORMAL" else f"flagged as **{flag}** compared to standard reference intervals"

            return (
                f"### Understanding Your {test_name} Result\n\n"
                f"- **Your Measured Value**: **{result.value} {unit}**\n"
                f"- **Standard Reference Range**: {ref_range}\n"
                f"- **Evaluation**: Your result is {status_desc}.{trend_str}\n\n"
                f"**What This Test Measures**:\n"
                f"{test_def.description if test_def else 'Evaluates targeted biochemical markers in your body.'}\n\n"
                f"**Suggested Questions for Your Doctor**:\n"
                f"• Does this reading align with our treatment goals?\n"
                f"• Are any lifestyle or dietary adjustments recommended?\n"
                f"• When should we repeat this test to check progress?\n\n"
                f"---\n"
                f"⚠️ *Important Notice: This laboratory explanation is educational and does not constitute a clinical diagnosis. "
                f"Laboratory measurements must always be evaluated in context of your complete clinical picture by your physician.*"
            )

        ai_res = ai_gateway.execute_ai_task(
            db=db,
            current_user=current_user,
            feature_name="lab_report_explainer",
            system_instruction=(
                "You are MediCore AI's Laboratory Report Explainer. Explain the laboratory measurement, reference range, "
                "and what high/low flags mean in accessible language. "
                "Do not make medical diagnoses. Never suggest medication adjustments. "
                "Include recommended questions for their physician."
            ),
            user_prompt=f"Explain {test_name} result of {result.value} {unit}.",
            untrusted_clinical_context=lab_data_context,
            deterministic_fallback_fn=generate_explanation
        )

        return {
            "result_id": result.id,
            "test_name": test_name,
            "value": f"{result.value} {unit}".strip(),
            "reference_range": ref_range,
            "flag": flag,
            "explanation": ai_res["data"],
            "historical_trends": history_trends,
            "is_educational": True,
            "disclaimer": "Educational laboratory explanation only. Not a definitive medical diagnosis."
        }


lab_report_explainer_service = LabReportExplainerService()
