"""
Pediatric and Neonatal Emergency Safety Engine.
Implements:
1. APGAR Scoring (1-min and 5-min post-delivery resuscitation assessment).
2. Broselow Pediatric Emergency Resuscitation & Weight-Based Dosing Engine
   (Color-coded zones, weight estimation, Epinephrine, Defibrillation J/kg,
   ETT sizes, and fluid bolus guidelines following PALS/AAP protocols).
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class APGARAssessment(BaseModel):
    time_minutes: int = Field(..., ge=1, le=10, description="1 or 5 minutes post-delivery")
    appearance: int = Field(..., ge=0, le=2, description="0=blue/pale, 1=acrocyanotic, 2=completely pink")
    pulse: int = Field(..., ge=0, le=2, description="0=absent, 1=<100 bpm, 2=>=100 bpm")
    grimace: int = Field(..., ge=0, le=2, description="0=floppy/no response, 1=grimace/weak cry, 2=vigorous cry/pull away")
    activity: int = Field(..., ge=0, le=2, description="0=limp/flaccid, 1=some flexion, 2=active motion")
    respiration: int = Field(..., ge=0, le=2, description="0=absent, 1=slow/irregular/weak cry, 2=good vigorous cry")

class PediatricEmergencyRequest(BaseModel):
    patient_id: str
    age_months: Optional[int] = None
    length_cm: Optional[float] = None
    actual_weight_kg: Optional[float] = None
    indication: Optional[str] = "Cardiac Arrest / Anaphylaxis / Resuscitation"

class PediatricSafetyService:
    BROSELOW_ZONES = [
        {"color": "Grey", "min_len": 0, "max_len": 59.9, "est_weight_kg": 4.0, "ett_uncuffed": 2.5, "ett_cuffed": 3.0},
        {"color": "Pink", "min_len": 60, "max_len": 67.9, "est_weight_kg": 6.5, "ett_uncuffed": 3.0, "ett_cuffed": 3.0},
        {"color": "Red", "min_len": 68, "max_len": 75.9, "est_weight_kg": 8.5, "ett_uncuffed": 3.5, "ett_cuffed": 3.0},
        {"color": "Purple", "min_len": 76, "max_len": 84.9, "est_weight_kg": 10.5, "ett_uncuffed": 4.0, "ett_cuffed": 3.5},
        {"color": "Yellow", "min_len": 85, "max_len": 96.9, "est_weight_kg": 13.0, "ett_uncuffed": 4.5, "ett_cuffed": 4.0},
        {"color": "White", "min_len": 97, "max_len": 109.9, "est_weight_kg": 16.5, "ett_uncuffed": 5.0, "ett_cuffed": 4.5},
        {"color": "Blue", "min_len": 110, "max_len": 121.9, "est_weight_kg": 21.0, "ett_uncuffed": 5.5, "ett_cuffed": 5.0},
        {"color": "Orange", "min_len": 122, "max_len": 132.9, "est_weight_kg": 26.5, "ett_uncuffed": 6.0, "ett_cuffed": 5.5},
        {"color": "Green", "min_len": 133, "max_len": 145.0, "est_weight_kg": 33.0, "ett_uncuffed": 6.5, "ett_cuffed": 6.0},
    ]

    @classmethod
    def calculate_apgar(cls, data: APGARAssessment) -> Dict[str, Any]:
        total_score = data.appearance + data.pulse + data.grimace + data.activity + data.respiration
        
        if total_score >= 7:
            status = "Normal / Low Risk"
            urgency = "ROUTINE"
            recommendations = [
                "Routine newborn care: dry, maintain warmth, clear airway if indicated, skin-to-skin."
            ]
        elif 4 <= total_score <= 6:
            status = "Moderately Abnormal"
            urgency = "URGENT"
            recommendations = [
                "Requires immediate stimulation, tactical positioning, and supplemental oxygen or positive pressure ventilation (PPV).",
                "Re-evaluate vitals continuously and re-score APGAR at 5 and 10 minutes."
            ]
        else:
            status = "Critically Depressed"
            urgency = "STAT_CRITICAL"
            recommendations = [
                "IMMEDIATE RESUSCITATION REQUIRED (NRP protocol).",
                "Initiate PPV with room air/blended O2 immediately.",
                "If HR < 60 bpm after 30s effective PPV, initiate chest compressions (3:1 ratio) and prepare umbilical catheterization for epinephrine."
            ]
            
        return {
            "time_minutes": data.time_minutes,
            "apgar_score": total_score,
            "max_score": 10,
            "status": status,
            "urgency": urgency,
            "breakdown": {
                "appearance": data.appearance,
                "pulse": data.pulse,
                "grimace": data.grimace,
                "activity": data.activity,
                "respiration": data.respiration
            },
            "clinical_recommendations": recommendations
        }

    @classmethod
    def calculate_pediatric_dosing(cls, req: PediatricEmergencyRequest) -> Dict[str, Any]:
        weight = req.actual_weight_kg
        broselow_zone = None

        if weight is None and req.length_cm is not None:
            # Map length to Broselow zone
            for zone in cls.BROSELOW_ZONES:
                if zone["min_len"] <= req.length_cm <= zone["max_len"]:
                    broselow_zone = zone["color"]
                    weight = zone["est_weight_kg"]
                    ett_uncuffed = zone["ett_uncuffed"]
                    ett_cuffed = zone["ett_cuffed"]
                    break
            if weight is None:
                # If length > 145 cm, assign green or adult defaults
                broselow_zone = "Green / Adult Transition"
                weight = 36.0
                ett_uncuffed = 7.0
                ett_cuffed = 6.5
        elif weight is not None:
            # Match closest zone by weight
            for zone in cls.BROSELOW_ZONES:
                if weight <= zone["est_weight_kg"] + 2.0:
                    broselow_zone = zone["color"]
                    ett_uncuffed = zone["ett_uncuffed"]
                    ett_cuffed = zone["ett_cuffed"]
                    break
            if not broselow_zone:
                broselow_zone = "Green / Adult Transition"
                ett_uncuffed = 7.0
                ett_cuffed = 6.5
        else:
            # Fallback estimation based on age in months if provided
            if req.age_months is not None:
                if req.age_months <= 12:
                    weight = (req.age_months + 9) / 2.0
                else:
                    age_years = req.age_months / 12.0
                    weight = 2 * (age_years + 4)
                broselow_zone = "Age-Estimated"
                ett_uncuffed = round(4.0 + (req.age_months / 48.0), 1)
                ett_cuffed = round(ett_uncuffed - 0.5, 1)
            else:
                weight = 10.0  # default toddler baseline
                broselow_zone = "Default Purple Zone (10kg)"
                ett_uncuffed = 4.0
                ett_cuffed = 3.5

        # PALS dosing calculations
        # Epinephrine Cardiac Arrest IV/IO: 0.01 mg/kg (0.1 mL/kg of 0.1 mg/mL 1:10,000 solution) max 1 mg
        epi_arrest_mg = round(min(0.01 * weight, 1.0), 3)
        epi_arrest_ml_1_10k = round(epi_arrest_mg * 10.0, 2)

        # Epinephrine Anaphylaxis IM: 0.01 mg/kg (0.01 mL/kg of 1 mg/mL 1:1,000 solution) max 0.3 mg (or 0.5 mg for older)
        epi_anaph_mg = round(min(0.01 * weight, 0.3 if weight < 30 else 0.5), 3)

        # Defibrillation: Initial 2 J/kg, Subsequent 4 J/kg, max 10 J/kg or 200 J
        defib_initial_joules = int(round(min(2 * weight, 200)))
        defib_subsequent_joules = int(round(min(4 * weight, 200)))

        # Synchronized Cardioversion: Initial 0.5-1 J/kg, second 2 J/kg
        cardioversion_initial_joules = int(round(min(1.0 * weight, 100)))
        cardioversion_second_joules = int(round(min(2.0 * weight, 200)))

        # Fluid Bolus (Isotonic saline): 20 mL/kg over 10-20 min (10 mL/kg for cardiogenic shock / DKA)
        fluid_bolus_ml = int(round(min(20 * weight, 1000)))

        # Normal vital sign ranges for weight/age
        if weight < 10:
            expected_hr = "100 - 160 bpm"
            expected_rr = "30 - 50 /min"
            min_systolic_bp = round(60 + (2 * (weight / 3.0)), 0)
        elif weight < 20:
            expected_hr = "90 - 140 bpm"
            expected_rr = "22 - 34 /min"
            min_systolic_bp = round(70 + (2 * (weight / 5.0)), 0)
        else:
            expected_hr = "70 - 110 bpm"
            expected_rr = "16 - 24 /min"
            min_systolic_bp = 90

        return {
            "patient_id": req.patient_id,
            "calculated_weight_kg": round(weight, 1),
            "broselow_tape_zone": broselow_zone,
            "airway_equipment": {
                "ett_uncuffed_mm": ett_uncuffed,
                "ett_cuffed_mm": ett_cuffed,
                "ett_depth_lip_cm": round(ett_uncuffed * 3, 1),
                "suction_catheter_fr": int(ett_uncuffed * 2),
                "laryngoscope_blade": "Miller 1" if weight < 10 else ("Wis-Hipple / Miller 2" if weight < 20 else "Mac 2 or 3")
            },
            "emergency_medications": {
                "epinephrine_cardiac_arrest_iv_io": {
                    "dose_mg": epi_arrest_mg,
                    "volume_ml": epi_arrest_ml_1_10k,
                    "concentration": "0.1 mg/mL (1:10,000)",
                    "route": "IV/IO every 3-5 min"
                },
                "epinephrine_anaphylaxis_im": {
                    "dose_mg": epi_anaph_mg,
                    "volume_ml": epi_anaph_mg,
                    "concentration": "1.0 mg/mL (1:1,000)",
                    "route": "IM anterolateral thigh"
                },
                "amiodarone_cardiac_arrest": {
                    "dose_mg": round(min(5 * weight, 300), 1),
                    "indication": "Refractory VF / pulseless VT (max single dose 300 mg)"
                },
                "atropine": {
                    "dose_mg": round(max(0.1, min(0.02 * weight, 0.5)), 2),
                    "indication": "Symptomatic bradycardia"
                }
            },
            "electrical_therapy": {
                "defibrillation_initial": f"{defib_initial_joules} Joules (2 J/kg)",
                "defibrillation_subsequent": f"{defib_subsequent_joules} Joules (4 J/kg)",
                "cardioversion_initial": f"{cardioversion_initial_joules} Joules (1 J/kg)",
                "cardioversion_second": f"{cardioversion_second_joules} Joules (2 J/kg)"
            },
            "fluid_resuscitation": {
                "bolus_volume_ml": fluid_bolus_ml,
                "fluid_type": "0.9% Normal Saline or Plasmalyte",
                "infusion_rate": "Rapid push over 5-20 min"
            },
            "vital_sign_reference": {
                "expected_hr": expected_hr,
                "expected_rr": expected_rr,
                "hypotension_threshold_systolic": f"<{int(min_systolic_bp)} mmHg"
            }
        }
