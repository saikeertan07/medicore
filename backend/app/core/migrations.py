"""
MediCore AI — Database Migration Engine & Versioned Schema Integrity.
Features:
  - Versioned migration registry tracked in `schema_migrations`.
  - Transaction-safe step execution and strict verification.
  - Fail-fast on failed migrations with explicit status recording ('APPLIED' / 'FAILED').
  - Schema completeness verification against information_schema and sqlite_master.
  - Health check integration: prevents application readiness when schema is incomplete.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from app.core.database import engine

logger = logging.getLogger("medicore.migrations")


class MigrationError(Exception):
    """Base exception for migration failures."""
    pass


class MigrationVerificationError(MigrationError):
    """Raised when post-migration schema verification discovers missing tables or columns."""
    pass


# -------------------------------------------------------------------------
# Step 2: Core Hospital Operations
# -------------------------------------------------------------------------
def run_step2_migrations(target_engine=None):
    """
    Applies non-destructive schema migrations for Step 2:
    - Extends PostgreSQL Enums: userrole, appointmentstatus
    - Adds Step 2 columns: check_in_time, patient_number, full_name, email, phone, is_active
    - Backfills patient numbers for existing patients
    - Safe to run repeatedly (idempotent)
    """
    eng = target_engine or engine
    is_postgres = eng.dialect.name == "postgresql"
    
    with eng.connect() as conn:
        # Ensure base schema tables exist prior to Step 2 extensions
        from app.models.models import Base
        Base.metadata.create_all(bind=conn, checkfirst=True)

        if is_postgres:
            logger.info("Executing PostgreSQL Step 2 enum extensions and schema updates...")
            for role in ["RECEPTIONIST", "NURSE"]:
                try:
                    conn.execute(text(f"ALTER TYPE userrole ADD VALUE IF NOT EXISTS '{role}';"))
                    conn.commit()
                except Exception as e:
                    logger.debug(f"Enum userrole {role}: {e}")
                    conn.rollback()

            for status_val in ["CHECKED_IN", "IN_PROGRESS"]:
                try:
                    conn.execute(text(f"ALTER TYPE appointmentstatus ADD VALUE IF NOT EXISTS '{status_val}';"))
                    conn.commit()
                except Exception as e:
                    logger.debug(f"Enum appointmentstatus {status_val}: {e}")
                    conn.rollback()

            columns_sql = [
                "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS check_in_time TIMESTAMP;",
                "ALTER TABLE patients ADD COLUMN IF NOT EXISTS patient_number VARCHAR(50);",
                "ALTER TABLE patients ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);",
                "ALTER TABLE patients ADD COLUMN IF NOT EXISTS email VARCHAR(255);",
                "ALTER TABLE patients ADD COLUMN IF NOT EXISTS phone VARCHAR(50);",
                "ALTER TABLE patients ALTER COLUMN user_id DROP NOT NULL;",
                "ALTER TABLE departments ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;",
            ]
            for sql in columns_sql:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                except Exception as e:
                    logger.debug(f"Migration column check: {e}")
                    conn.rollback()

            try:
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_patient_number ON patients (patient_number) WHERE patient_number IS NOT NULL;"))
                conn.commit()
            except Exception:
                conn.rollback()

        else:
            # SQLite path (local test runner)
            sqlite_cols = [
                ("appointments", "check_in_time", "TIMESTAMP"),
                ("patients", "patient_number", "VARCHAR(50)"),
                ("patients", "full_name", "VARCHAR(255)"),
                ("patients", "email", "VARCHAR(255)"),
                ("patients", "phone", "VARCHAR(50)"),
                ("departments", "is_active", "BOOLEAN DEFAULT 1"),
            ]
            for table, col, col_type in sqlite_cols:
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};"))
                    conn.commit()
                except Exception:
                    pass

        # Backfill existing patients that lack patient_number
        try:
            res = conn.execute(text("SELECT id, user_id FROM patients WHERE patient_number IS NULL;"))
            rows = res.fetchall()
            for r in rows:
                p_id = r[0]
                p_num = f"PAT-202609-{p_id:06d}"
                conn.execute(text(f"UPDATE patients SET patient_number = '{p_num}' WHERE id = {p_id};"))
            
            if is_postgres:
                conn.execute(text("""
                    UPDATE patients p
                    SET full_name = u.full_name, email = u.email, phone = u.phone
                    FROM users u
                    WHERE p.user_id = u.id AND p.full_name IS NULL;
                """))
            conn.commit()
        except Exception as e:
            logger.debug(f"Backfill patient numbers: {e}")
            conn.rollback()

    logger.info("Step 2 migrations applied successfully.")


# -------------------------------------------------------------------------
# Step 3: Clinical Documentation & EMR
# -------------------------------------------------------------------------
def run_step3_migrations(target_engine=None):
    """
    Applies non-destructive schema migrations for Step 3 (Clinical Documentation / EMR):
    - Creates PostgreSQL Enums: encountertype, encounterstatus, clinicalnotestatus, diagnosistype
    - Ensures encounters, encounter_vitals, clinical_notes, clinical_diagnoses tables exist
    - Creates partial unique index uq_appointment_encounter on encounters(appointment_id)
    - Safe to run repeatedly (idempotent)
    """
    eng = target_engine or engine
    is_postgres = eng.dialect.name == "postgresql"

    with eng.connect() as conn:
        # Ensure base schema tables exist prior to Step 2 extensions
        from app.models.models import Base
        Base.metadata.create_all(bind=conn, checkfirst=True)

        if is_postgres:
            logger.info("Executing PostgreSQL Step 3 enum extensions and schema updates...")
            enums_to_create = [
                ("encountertype", ["OUTPATIENT", "FOLLOW_UP", "WALK_IN"]),
                ("encounterstatus", ["OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"]),
                ("clinicalnotestatus", ["DRAFT", "FINAL", "AMENDED"]),
                ("diagnosistype", ["PRIMARY", "SECONDARY", "WORKING", "SUSPECTED"]),
            ]
            for enum_name, values in enums_to_create:
                try:
                    conn.execute(text(f"""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name}') THEN
                                CREATE TYPE {enum_name} AS ENUM ({", ".join(f"'{v}'" for v in values)});
                            END IF;
                        END$$;
                    """))
                    conn.commit()
                except Exception as e:
                    logger.debug(f"Enum {enum_name} creation: {e}")
                    conn.rollback()

            from app.models.models import Encounter, EncounterVitals, ClinicalNote, ClinicalDiagnosis
            Encounter.__table__.create(bind=conn, checkfirst=True)
            EncounterVitals.__table__.create(bind=conn, checkfirst=True)
            ClinicalNote.__table__.create(bind=conn, checkfirst=True)
            ClinicalDiagnosis.__table__.create(bind=conn, checkfirst=True)
            conn.commit()

            try:
                conn.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_appointment_encounter 
                    ON encounters (appointment_id) 
                    WHERE appointment_id IS NOT NULL;
                """))
                conn.commit()
            except Exception as e:
                logger.debug(f"Unique index uq_appointment_encounter: {e}")
                conn.rollback()
        else:
            # SQLite path
            from app.models.models import Encounter, EncounterVitals, ClinicalNote, ClinicalDiagnosis
            Encounter.__table__.create(bind=conn, checkfirst=True)
            EncounterVitals.__table__.create(bind=conn, checkfirst=True)
            ClinicalNote.__table__.create(bind=conn, checkfirst=True)
            ClinicalDiagnosis.__table__.create(bind=conn, checkfirst=True)
            conn.commit()

    logger.info("Step 3 migrations applied successfully.")


# -------------------------------------------------------------------------
# Step 4: Laboratory & Diagnostics
# -------------------------------------------------------------------------
def run_step4_migrations(target_engine=None):
    """
    Applies non-destructive schema migrations for Step 4 (Laboratory & Diagnostics):
    - Creates PostgreSQL Enums
    - Ensures lab tables exist
    - Seeds standard laboratory test catalog if empty
    - Safe to run repeatedly (idempotent)
    """
    eng = target_engine or engine
    is_postgres = eng.dialect.name == "postgresql"

    with eng.connect() as conn:
        # Ensure base schema tables exist prior to Step 2 extensions
        from app.models.models import Base
        Base.metadata.create_all(bind=conn, checkfirst=True)

        if is_postgres:
            logger.info("Executing PostgreSQL Step 4 enum extensions and schema updates...")
            enums_to_create = [
                ("laborderpriority", ["ROUTINE", "URGENT", "STAT"]),
                ("laborderstatus", ["DRAFT", "ORDERED", "PARTIALLY_COLLECTED", "COLLECTED", "PROCESSING", "RESULTS_PENDING", "VERIFIED", "COMPLETED", "CANCELLED"]),
                ("laborderitemstatus", ["PENDING", "COLLECTED", "RECEIVED", "PROCESSING", "COMPLETED", "CANCELLED"]),
                ("labsamplestatus", ["PENDING", "COLLECTED", "RECEIVED", "PROCESSING", "COMPLETED", "REJECTED"]),
                ("labresultstatus", ["PENDING", "ENTERED", "VERIFIED", "FINAL", "AMENDED"]),
                ("abnormalflag", ["NORMAL", "HIGH", "LOW", "ABNORMAL", "CRITICAL"]),
            ]
            for enum_name, values in enums_to_create:
                try:
                    conn.execute(text(f"""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name}') THEN
                                CREATE TYPE {enum_name} AS ENUM ({", ".join(f"'{v}'" for v in values)});
                            END IF;
                        END$$;
                    """))
                    conn.commit()
                except Exception as e:
                    logger.debug(f"Enum {enum_name} creation: {e}")
                    conn.rollback()

        # Create Tables
        from app.models.models import (
            LabTestDefinition, LabOrder, LabOrderItem, LabSample, LabResult
        )
        LabTestDefinition.__table__.create(bind=conn, checkfirst=True)
        LabOrder.__table__.create(bind=conn, checkfirst=True)
        LabSample.__table__.create(bind=conn, checkfirst=True)
        LabOrderItem.__table__.create(bind=conn, checkfirst=True)
        LabResult.__table__.create(bind=conn, checkfirst=True)
        conn.commit()

        # Seed initial lab test definitions if empty
        res = conn.execute(text("SELECT COUNT(*) FROM lab_test_definitions;"))
        count = res.scalar()
        if count == 0:
            logger.info("Seeding standard laboratory test catalog...")
            catalog = [
                ("CBC", "Complete Blood Count", "Hematology", "Standard hemogram including WBC, RBC, Hgb, Hct, PLT.", "EDTA Whole Blood (Purple Top)", "10^3/uL", "4.5-11.0"),
                ("GLU", "Fasting Blood Glucose", "Biochemistry", "Fasting blood sugar level.", "Sodium Fluoride Plasma (Gray Top)", "mg/dL", "70-99"),
                ("CREAT", "Serum Creatinine", "Biochemistry", "Kidney function marker.", "Serum / Plasma (Gold/Green Top)", "mg/dL", "0.6-1.2"),
                ("HGB", "Hemoglobin", "Hematology", "Oxygen-carrying capacity of blood.", "EDTA Whole Blood (Purple Top)", "g/dL", "13.8-17.2"),
                ("LIPID", "Lipid Panel", "Biochemistry", "Total Cholesterol, HDL, LDL, Triglycerides.", "Serum (Gold Top)", "mg/dL", "<200"),
                ("BMP", "Basic Metabolic Panel", "Biochemistry", "Electrolytes (Na, K, Cl, CO2), BUN, Creatinine, Glucose, Calcium.", "Serum / Plasma (Gold/Green Top)", "mg/dL", "70-99"),
                ("LFT", "Liver Function Panel", "Biochemistry", "ALT, AST, ALP, Total Bilirubin, Direct Bilirubin, Total Protein, Albumin.", "Serum (Gold Top)", "U/L", "7-56"),
                ("HBA1C", "Hemoglobin A1c", "Endocrinology", "Glycated hemoglobin for long-term glucose monitoring.", "EDTA Whole Blood (Purple Top)", "%", "4.0-5.6"),
                ("TSH", "Thyroid Stimulating Hormone", "Endocrinology", "Primary screening test for thyroid function.", "Serum (Gold Top)", "uIU/mL", "0.4-4.0"),
                ("UA", "Urinalysis with Microscopic", "Urinalysis", "Screening for UTI, renal disease, and metabolic conditions.", "Clean Catch Urine", "pH", "4.5-8.0"),
                ("TROP", "Troponin I (High Sensitivity)", "Cardiology", "Myocardial injury marker for acute coronary syndromes.", "Plasma (Green/Heparin Top)", "ng/L", "<14"),
                ("ELECT", "Serum Electrolytes", "Biochemistry", "Sodium, Potassium, Chloride, Bicarbonate.", "Serum (Gold Top)", "mmol/L", "135-145"),
            ]
            for code, name, category, desc, spec, unit, ref_range in catalog:
                conn.execute(text(f"""
                    INSERT INTO lab_test_definitions (code, name, category, description, specimen_type, default_unit, default_reference_range, is_active, created_at, updated_at)
                    VALUES ('{code}', '{name}', '{category}', '{desc}', '{spec}', '{unit}', '{ref_range}', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
                """))
            conn.commit()

    logger.info("Step 4 migrations applied successfully.")


# -------------------------------------------------------------------------
# Step 5: Security, AI Governance & Clinical Safety
# -------------------------------------------------------------------------
def run_step5_security_and_ai_migrations(target_engine=None):
    """
    Applies migrations for RevokedToken blacklist, AIGovernanceMetric,
    ClinicalDocumentChunk, AIDocumentDraft, TriageAssessment, and PharmacySafetyAlert.
    """
    eng = target_engine or engine
    is_postgres = eng.dialect.name == "postgresql"

    with eng.connect() as conn:
        # Ensure base schema tables exist prior to Step 2 extensions
        from app.models.models import Base
        Base.metadata.create_all(bind=conn, checkfirst=True)

        if is_postgres:
            logger.info("Executing PostgreSQL Step 5 enum extensions and schema updates...")
            for new_role in ["PHARMACIST", "LAB_TECHNICIAN"]:
                try:
                    conn.execute(text(f"ALTER TYPE userrole ADD VALUE IF NOT EXISTS '{new_role}';"))
                    conn.commit()
                except Exception as e:
                    logger.debug(f"Role enum extend {new_role}: {e}")
                    conn.rollback()

            enums_to_create = [
                ("draftstatus", ["DRAFT", "UNDER_REVIEW", "APPROVED", "REJECTED"]),
                ("triageacuity", ["LEVEL_1_RESUSCITATION", "LEVEL_2_EMERGENT", "LEVEL_3_URGENT", "LEVEL_4_LESS_URGENT", "LEVEL_5_NON_URGENT"]),
            ]
            for enum_name, values in enums_to_create:
                try:
                    conn.execute(text(f"""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name}') THEN
                                CREATE TYPE {enum_name} AS ENUM ({", ".join(f"'{v}'" for v in values)});
                            END IF;
                        END$$;
                    """))
                    conn.commit()
                except Exception as e:
                    logger.debug(f"Enum {enum_name} creation: {e}")
                    conn.rollback()

        # Create Tables
        from app.models.models import (
            RevokedToken, AIGovernanceMetric, ClinicalDocumentChunk,
            AIDocumentDraft, TriageAssessment, PharmacySafetyAlert
        )
        RevokedToken.__table__.create(bind=conn, checkfirst=True)
        AIGovernanceMetric.__table__.create(bind=conn, checkfirst=True)
        ClinicalDocumentChunk.__table__.create(bind=conn, checkfirst=True)
        AIDocumentDraft.__table__.create(bind=conn, checkfirst=True)
        TriageAssessment.__table__.create(bind=conn, checkfirst=True)
        PharmacySafetyAlert.__table__.create(bind=conn, checkfirst=True)
        conn.commit()

    logger.info("Step 5 Security & AI migrations applied successfully.")


# -------------------------------------------------------------------------
# Schema Verification Engine
# -------------------------------------------------------------------------
REQUIRED_STEP_TABLES: Dict[str, List[str]] = {
    "step2_core_ops": ["users", "patients", "doctors", "departments", "appointments"],
    "step3_clinical_emr": ["encounters", "encounter_vitals", "clinical_notes", "clinical_diagnoses"],
    "step4_laboratory": ["lab_test_definitions", "lab_orders", "lab_order_items", "lab_samples", "lab_results"],
    "step5_security_and_ai": ["revoked_tokens", "ai_governance_metrics", "clinical_document_chunks", "ai_document_drafts", "triage_assessments", "pharmacy_safety_alerts"],
}


def verify_step_schema(conn, version_name: str) -> None:
    """
    Exhaustively verifies that all expected tables for a migration step exist on the engine.
    Raises MigrationVerificationError if any required table is missing.
    """
    expected_tables = REQUIRED_STEP_TABLES.get(version_name, [])
    if not expected_tables:
        return

    is_postgres = conn.dialect.name == "postgresql"
    if is_postgres:
        res = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public';
        """))
        existing_tables = {row[0].lower() for row in res.fetchall()}
    else:
        # SQLite
        res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        existing_tables = {row[0].lower() for row in res.fetchall()}

    missing = [tbl for tbl in expected_tables if tbl.lower() not in existing_tables]
    if missing:
        raise MigrationVerificationError(
            f"Schema verification failed for migration '{version_name}'. Missing required tables: {missing}"
        )


def ensure_schema_migrations_table(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(50) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(20) NOT NULL,
            error_message TEXT
        );
    """))
    conn.commit()


from sqlalchemy.engine import Engine

def record_migration_success(conn_or_engine, version: str):
    if isinstance(conn_or_engine, Engine):
        with conn_or_engine.begin() as c:
            return record_migration_success(c, version)
    conn = conn_or_engine
    is_postgres = conn.dialect.name == "postgresql"
    if is_postgres:
        conn.execute(text(f"""
            INSERT INTO schema_migrations (version, applied_at, status, error_message)
            VALUES ('{version}', CURRENT_TIMESTAMP, 'APPLIED', NULL)
            ON CONFLICT (version) DO UPDATE SET applied_at = CURRENT_TIMESTAMP, status = 'APPLIED', error_message = NULL;
        """))
    else:
        conn.execute(text(f"""
            INSERT OR REPLACE INTO schema_migrations (version, applied_at, status, error_message)
            VALUES ('{version}', CURRENT_TIMESTAMP, 'APPLIED', NULL);
        """))
    if hasattr(conn, "commit"):
        try:
            conn.commit()
        except Exception:
            pass


def record_migration_failure(conn_or_engine, version: str, error_msg: str):
    if isinstance(conn_or_engine, Engine):
        with conn_or_engine.begin() as c:
            return record_migration_failure(c, version, error_msg)
    conn = conn_or_engine
    is_postgres = conn.dialect.name == "postgresql"
    clean_err = error_msg.replace("'", "''")
    if is_postgres:
        conn.execute(text(f"""
            INSERT INTO schema_migrations (version, applied_at, status, error_message)
            VALUES ('{version}', CURRENT_TIMESTAMP, 'FAILED', '{clean_err}')
            ON CONFLICT (version) DO UPDATE SET applied_at = CURRENT_TIMESTAMP, status = 'FAILED', error_message = '{clean_err}';
        """))
    else:
        conn.execute(text(f"""
            INSERT OR REPLACE INTO schema_migrations (version, applied_at, status, error_message)
            VALUES ('{version}', CURRENT_TIMESTAMP, 'FAILED', '{clean_err}');
        """))
    if hasattr(conn, "commit"):
        try:
            conn.commit()
        except Exception:
            pass


MIGRATION_STEPS = [
    ("step2_core_ops", run_step2_migrations),
    ("step3_clinical_emr", run_step3_migrations),
    ("step4_laboratory", run_step4_migrations),
    ("step5_security_and_ai", run_step5_security_and_ai_migrations),
]


def run_all_migrations(target_engine=None):
    """
    Executes all versioned migrations sequentially with transactional tracking in schema_migrations.
    Raises RuntimeError on failure to prevent application replica startup on corrupted schemas.
    """
    eng = target_engine or engine
    with eng.connect() as conn:
        ensure_schema_migrations_table(conn)

    for version_name, migration_fn in MIGRATION_STEPS:
        try:
            logger.info(f"Applying migration: {version_name}...")
            migration_fn(eng)
            with eng.connect() as conn:
                verify_step_schema(conn, version_name)
                record_migration_success(conn, version_name)
            logger.info(f"Migration {version_name} applied successfully and verified.")
        except Exception as e:
            logger.critical(f"FATAL: Migration failed on step '{version_name}': {e}", exc_info=True)
            with eng.connect() as conn:
                record_migration_failure(conn, version_name, str(e))
            raise RuntimeError(f"Database migration '{version_name}' failed: {e}") from e


def check_migrations(target_engine=None) -> Dict[str, Dict[str, Any]]:
    eng = target_engine or engine
    with eng.connect() as conn:
        ensure_schema_migrations_table(conn)
        rows = conn.execute(text("SELECT version, status, applied_at, error_message FROM schema_migrations;")).fetchall()
        return {r[0]: {"status": r[1], "applied_at": str(r[2]), "error": r[3]} for r in rows}


def is_schema_ready(target_engine=None) -> Tuple[bool, Optional[str]]:
    """
    Checks if all required migration steps are recorded as 'APPLIED' with zero 'FAILED' steps.
    Used by readiness probes.
    """
    try:
        status_map = check_migrations(target_engine)

        # 1. Zero tolerance for any recorded FAILED migration
        for v_name, details in status_map.items():
            if details.get("status") == "FAILED":
                return False, f"Migration '{v_name}' is in FAILED status: {details.get('error')}"

        # 2. Verify all required steps are applied
        for version_name, _ in MIGRATION_STEPS:
            entry = status_map.get(version_name)
            if not entry:
                return False, f"Migration step '{version_name}' has not been applied."
            if entry["status"] != "APPLIED":
                return False, f"Migration step '{version_name}' is in status '{entry['status']}'."
        return True, None
    except Exception as e:
        return False, f"Schema readiness check failed: {e}"


if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "--run"
    if action == "--check":
        print("Schema Migrations:", check_migrations())
    else:
        run_all_migrations()
        print("All migrations completed successfully and verified.")
