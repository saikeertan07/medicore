"""
Total Parenteral Nutrition (TPN) & Electrolyte Safety Engine.
Implements:
1. Basal & Total Energy Expenditure (Harris-Benedict equation + clinical stress factors).
2. Macronutrient allocation:
   - Amino acids (protein): 1.0 - 2.5 g/kg/day based on catabolic stress.
   - Dextrose: Glucose Infusion Rate (GIR) monitoring (max 4-5 mg/kg/min to prevent hepatic steatosis).
   - Intravenous Lipid Emulsion (ILE 20%): 1 g/kg/day (not exceeding 60% total calories).
3. Daily electrolyte requirements & critical Calcium-Phosphate solubility curve safety check.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class TPNOrderRequest(BaseModel):
    patient_id: str
    weight_kg: float = Field(..., ge=1.0, le=300.0, description="Patient weight in kg")
    height_cm: float = Field(..., ge=30.0, le=250.0, description="Patient height in cm")
    age_years: int = Field(..., ge=0, le=120, description="Age in years")
    gender: str = Field(..., description="'male' or 'female'")
    clinical_condition: str = Field("uncomplicated_inpatient", description="'uncomplicated_inpatient', 'post_op', 'sepsis', 'severe_burns', 'critically_ill'")
    target_fluid_volume_ml: Optional[float] = Field(None, description="Total daily volume in mL (defaults to 30-35 mL/kg)")
    calcium_mEq: float = Field(10.0, ge=0.0, le=50.0, description="Daily Calcium mEq")
    phosphate_mmol: float = Field(30.0, ge=0.0, le=80.0, description="Daily Phosphate mmol")

class TPNNutritionService:
    STRESS_FACTORS = {
        "uncomplicated_inpatient": 1.1,
        "post_op": 1.25,
        "sepsis": 1.4,
        "critically_ill": 1.35,
        "severe_burns": 1.8
    }

    PROTEIN_REQUIREMENTS_G_KG = {
        "uncomplicated_inpatient": 1.0,
        "post_op": 1.3,
        "sepsis": 1.6,
        "critically_ill": 1.8,
        "severe_burns": 2.2
    }

    @classmethod
    def calculate_tpn_prescription(cls, req: TPNOrderRequest) -> Dict[str, Any]:
        # 1. Harris-Benedict Basal Energy Expenditure (BEE)
        gender_norm = req.gender.lower()
        if gender_norm == "male":
            bee = 66.5 + (13.75 * req.weight_kg) + (5.003 * req.height_cm) - (6.75 * req.age_years)
        else:
            bee = 655.1 + (9.563 * req.weight_kg) + (1.850 * req.height_cm) - (4.676 * req.age_years)

        stress_factor = cls.STRESS_FACTORS.get(req.clinical_condition, 1.2)
        total_target_calories = round(bee * stress_factor, 1)

        # 2. Fluid Volume
        daily_volume_ml = req.target_fluid_volume_ml or round(req.weight_kg * 30.0, 1)

        # 3. Protein (Amino Acids): 4 kcal/g
        protein_factor = cls.PROTEIN_REQUIREMENTS_G_KG.get(req.clinical_condition, 1.2)
        protein_grams = round(req.weight_kg * protein_factor, 1)
        protein_kcal = round(protein_grams * 4.0, 1)

        # 4. Lipids (20% lipid emulsion = 2.0 kcal/mL, approx 10 kcal/g): ~25-30% of total kcal
        target_lipid_kcal = round(total_target_calories * 0.25, 1)
        lipid_grams = round(target_lipid_kcal / 10.0, 1)
        lipid_volume_20pct_ml = round(lipid_grams * 5.0, 1) # 20% = 0.2g/ml

        # 5. Non-protein calories remainder for Dextrose (3.4 kcal/g hydrous dextrose monohydrate)
        remaining_kcal = max(0.0, total_target_calories - protein_kcal - target_lipid_kcal)
        dextrose_grams = round(remaining_kcal / 3.4, 1)
        
        # Glucose Infusion Rate (GIR): mg/kg/min over 24 hours (1440 min)
        gir_mg_kg_min = round((dextrose_grams * 1000.0) / (req.weight_kg * 1440.0), 2)
        gir_warning = None
        if gir_mg_kg_min > 5.0:
            gir_warning = f"High Glucose Infusion Rate ({gir_mg_kg_min} mg/kg/min > 5.0 mg/kg/min). Risk of hyperglycemia and hepatic steatosis."

        # 6. Electrolytes & Safety Checks
        # Calcium-Phosphate precipitation curve safety check:
        # Sum of [Ca mEq/L] + [PO4 mmol/L] must remain < 35 to prevent catastrophic precipitation
        volume_liters = daily_volume_ml / 1000.0
        ca_conc = req.calcium_mEq / volume_liters
        po4_conc = req.phosphate_mmol / volume_liters
        ca_po4_sum = round(ca_conc + po4_conc, 1)

        precipitation_risk = "SAFE"
        warnings = []
        if ca_po4_sum >= 35.0:
            precipitation_risk = "CRITICAL_DANGER_PRECIPITATION_RISK"
            warnings.append(f"Precipitation Warning: Combined Ca ({ca_conc:.1f} mEq/L) + Phosphate ({po4_conc:.1f} mmol/L) sum = {ca_po4_sum} (Threshold >= 35). High risk of microcrystalline emboli! Increase total bag volume or reduce Phosphate/Calcium.")

        if gir_warning:
            warnings.append(gir_warning)

        # Standard Recommended Electrolyte Additives
        sodium_mEq = round(req.weight_kg * 1.5, 1)
        potassium_mEq = round(req.weight_kg * 1.0, 1)
        magnesium_mEq = 10.0

        return {
            "patient_id": req.patient_id,
            "weight_kg": req.weight_kg,
            "clinical_condition": req.clinical_condition,
            "basal_energy_expenditure_kcal": round(bee, 1),
            "total_daily_caloric_target_kcal": total_target_calories,
            "daily_fluid_volume_ml": daily_volume_ml,
            "macronutrients": {
                "amino_acids": {
                    "grams": protein_grams,
                    "calories_kcal": protein_kcal,
                    "g_per_kg": protein_factor
                },
                "dextrose": {
                    "grams": dextrose_grams,
                    "calories_kcal": round(dextrose_grams * 3.4, 1),
                    "glucose_infusion_rate_mg_kg_min": gir_mg_kg_min
                },
                "lipids_20pct": {
                    "grams": lipid_grams,
                    "calories_kcal": target_lipid_kcal,
                    "volume_ml": lipid_volume_20pct_ml
                }
            },
            "electrolytes_prescribed": {
                "sodium_mEq": sodium_mEq,
                "potassium_mEq": potassium_mEq,
                "calcium_mEq": req.calcium_mEq,
                "phosphate_mmol": req.phosphate_mmol,
                "magnesium_mEq": magnesium_mEq
            },
            "calcium_phosphate_compatibility": {
                "calcium_mEq_per_liter": round(ca_conc, 1),
                "phosphate_mmol_per_liter": round(po4_conc, 1),
                "combined_sum": ca_po4_sum,
                "safety_threshold": "< 35.0",
                "precipitation_status": precipitation_risk
            },
            "safety_alerts": warnings
        }
