"""
HL7 FHIR R4 Interoperability & Resource Serialization Engine.
Converts MediCore clinical entities into standard HL7 FHIR R4 compliant resources
(Patient, Encounter, Observation with LOINC codes, and Bundles).
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from app.core.datetime_utils import utc_now

# Standard LOINC Codes for Clinical Vitals Observations
LOINC_CODES = {
    "heart_rate": {"code": "8867-4", "display": "Heart rate", "unit": "/min"},
    "respiration_rate": {"code": "9279-1", "display": "Respiratory rate", "unit": "/min"},
    "systolic_bp": {"code": "8480-6", "display": "Systolic blood pressure", "unit": "mmHg"},
    "spo2": {"code": "2708-6", "display": "Oxygen saturation in Arterial blood", "unit": "%"},
    "temperature": {"code": "8310-5", "display": "Body temperature", "unit": "Cel"}
}

class FHIRConverter:
    @staticmethod
    def to_fhir_patient(
        patient_id: int,
        mrn: str,
        first_name: str,
        last_name: str,
        dob: str,
        gender: str,
        phone: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Serializes patient data into standard FHIR R4 Patient resource."""
        telecoms = []
        if phone:
            telecoms.append({"system": "phone", "value": phone, "use": "mobile"})
        if email:
            telecoms.append({"system": "email", "value": email, "use": "home"})

        return {
            "resourceType": "Patient",
            "id": str(patient_id),
            "identifier": [
                {
                    "use": "usual",
                    "type": {
                        "coding": [
                            {"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR", "display": "Medical Record Number"}
                        ]
                    },
                    "system": "urn:oid:2.16.840.1.113883.4.1",
                    "value": mrn
                }
            ],
            "active": True,
            "name": [
                {
                    "use": "official",
                    "family": last_name,
                    "given": [first_name]
                }
            ],
            "telecom": telecoms,
            "gender": gender.lower() if gender.lower() in ["male", "female", "other", "unknown"] else "unknown",
            "birthDate": dob
        }

    @staticmethod
    def to_fhir_observation(
        observation_id: str,
        patient_id: int,
        vital_name: str,
        value: float,
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """Serializes a vital observation into standard FHIR R4 Observation with LOINC coding."""
        loinc = LOINC_CODES.get(vital_name, {"code": "unknown", "display": vital_name, "unit": "unit"})
        effective_time = timestamp or utc_now().isoformat() + "Z"

        return {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}
                    ]
                }
            ],
            "code": {
                "coding": [
                    {"system": "http://loinc.org", "code": loinc["code"], "display": loinc["display"]}
                ],
                "text": loinc["display"]
            },
            "subject": {"reference": f"Patient/{patient_id}"},
            "effectiveDateTime": effective_time,
            "valueQuantity": {
                "value": value,
                "unit": loinc["unit"],
                "system": "http://unitsofmeasure.org",
                "code": loinc["unit"]
            }
        }

    @classmethod
    def create_fhir_patient_bundle(
        cls,
        patient_resource: Dict[str, Any],
        observations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Assembles a FHIR R4 collection Bundle."""
        entries = [{"resource": patient_resource}]
        for obs in observations:
            entries.append({"resource": obs})

        return {
            "resourceType": "Bundle",
            "type": "collection",
            "timestamp": utc_now().isoformat() + "Z",
            "total": len(entries),
            "entry": entries
        }
