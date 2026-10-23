"""
Clinical Prompt Library & Roadmap for Enterprise Hospital Upgrade
"""

HOSPITAL_MISSION_SYSTEM_PROMPT = """You are the Chief Medical Information Officer (CMIO) and Principal Hospital Systems Architect.
You are tasked with upgrading MediCore AI into an enterprise-grade Hospital Operating System that a large medical center safely and fully depends upon for 24/7/365 inpatient, outpatient, and emergency operations.

CRITICAL HOSPITAL STANDARDS:
1. Zero Patient Risk: All AI features must include strict physician validation, clinical disclaimer guardrails, and audit logging.
2. Clinical Standards: Follow HL7 FHIR R4, ICD-10, ESI (Emergency Severity Index), and NEWS2 (National Early Warning Score).
3. Resilience: 100% test coverage for concurrency, race conditions, atomic state changes, and rollback on error.
4. HIPAA/PHI Protection: Zero PHI leakage, role-based encryption, tamper-evident audit trails.

You are participating in an ongoing continuous upgrade session. Always build upon previous iterations without breaking existing verified endpoints.
"""

HOSPITAL_UPGRADE_ROADMAP = [
    {
        "module": "emergency_triage_news2",
        "title": "Phase 1: Emergency Triage AI & NEWS2 Clinical Deterioration Engine",
        "description": "Implement automated Emergency Severity Index (ESI 1-5) AI triage, vital sign risk calculation (NEWS2 score), and immediate nurse alert triggers for critical patients.",
        "target_files": [
            "backend/app/services/triage_service.py",
            "backend/app/api/v1/triage.py",
            "backend/tests/test_triage_news2.py",
            "frontend/src/app/nurse/triage/page.tsx"
        ]
    },
    {
        "module": "drug_interaction_safety",
        "title": "Phase 2: Real-Time Drug-Drug & Allergy Interaction Safety AI",
        "description": "Implement clinical medication safety checker: automatically inspects new prescriptions against patient allergies, existing medications, renal function, and flagged contraindications.",
        "target_files": [
            "backend/app/services/pharmacy_service.py",
            "backend/app/api/v1/pharmacy.py",
            "backend/tests/test_pharmacy_safety.py"
        ]
    },
    {
        "module": "ambient_soap_scribe",
        "title": "Phase 3: Ambient Clinical AI Scribe & Automated SOAP Note Generator",
        "description": "Implement automated transcription to structured SOAP note (Subjective, Objective, Assessment, Plan) with ICD-10 diagnostic coding suggestions and physician sign-off workflow.",
        "target_files": [
            "backend/app/services/ambient_scribe_service.py",
            "backend/app/api/v1/clinical_scribe.py",
            "backend/tests/test_ambient_scribe.py"
        ]
    },
    {
        "module": "hl7_fhir_interop",
        "title": "Phase 4: HL7 FHIR R4 Interoperability & External EHR Data Exchange",
        "description": "Implement bidirectional FHIR R4 compliance (Patient, Encounter, Observation, DiagnosticReport) to connect seamlessly with national EHR systems and lab machines.",
        "target_files": [
            "backend/app/services/fhir_service.py",
            "backend/app/api/v1/fhir.py",
            "backend/tests/test_fhir_interop.py"
        ]
    },
    {
        "module": "tamper_evident_audit_vault",
        "title": "Phase 5: Tamper-Evident SHA-256 Audit Vault & HIPAA Compliance Telemetry",
        "description": "Cryptographically secure audit trails using hash chaining so no historical record can be altered or erased; emergency access break-glass protocol.",
        "target_files": [
            "backend/app/services/audit_vault_service.py",
            "backend/app/api/v1/audit_vault.py",
            "backend/tests/test_audit_vault.py"
        ]
    },
    {
        "module": "icu_telemetry_bed_optimizer",
        "title": "Phase 6: Real-time ICU Telemetry & Predictive Bed Allocation AI",
        "description": "Predictive bed census management, ICU discharge readiness scoring, and smart routing for emergency incoming ambulances.",
        "target_files": [
            "backend/app/services/bed_telemetry_service.py",
            "backend/app/api/v1/bed_telemetry.py",
            "backend/tests/test_bed_telemetry.py"
        ]
    }
]

def generate_iteration_prompt(iteration: int, project_summary: str, current_milestone: dict) -> str:
    """Generates the prompt for the next upgrade cycle."""
    return f"""
CONTINUOUS VIBE CODING LOOP - ITERATION #{iteration}
ACTIVE MILESTONE: {current_milestone['title']}

HOSPITAL OPERATING CONTEXT:
The hospital relies 100% on MediCore for daily life-critical clinical operations.
Current repository status:
{project_summary}

MISSION OBJECTIVE:
Implement {current_milestone['description']}

OUTPUT FORMAT REQUIREMENTS:
Provide production-ready, syntax-valid Python and TypeScript code.
For each file to be created or modified, format clearly using standard file code blocks:
```filepath:path/to/file.py
# Complete code here
```

Every code file must include:
1. Complete types, docstrings, and error handling.
2. Seamless integration with existing FastAPI schemas and SQLAlchemy models.
3. Unit & integration tests in pytest verifying the new clinical functionality.
"""
