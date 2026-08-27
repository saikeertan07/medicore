import time
import uuid
import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import engine, Base
import app.models  # Ensure models are loaded
from app.core.migrations import run_all_migrations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("medicore")

# Run database migrations with version tracking
try:
    run_all_migrations(engine)
except Exception as e:
    if settings.ENVIRONMENT == "production":
        logger.critical(f"FATAL: Database migration failed in production: {e}")
        raise RuntimeError(f"FATAL: Application startup aborted. Database migration failed: {e}") from e
    else:
        logger.warning(f"Database migration note (development mode): {e}")

# In development and testing, ensure all metadata tables exist
if settings.ENVIRONMENT != "production":
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="MediCore AI - Next-Generation AI Hospital Operating System",
    version="1.0.0",
    docs_url=f"{settings.API_V1_STR}/docs",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID, Latency Tracking, Body Size Limit & Security Headers Middleware
@app.middleware("http")
async def security_and_context_middleware(request: Request, call_next):
    # Enforce Request Size Limit (max 25MB for document uploads, 2MB for standard JSON)
    content_length = request.headers.get("Content-Length")
    if content_length:
        try:
            length = int(content_length)
            max_limit = 25 * 1024 * 1024 if "/upload" in request.url.path else 2 * 1024 * 1024
            if length > max_limit:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"detail": "Payload exceeds maximum allowable size limit."}
                )
        except ValueError:
            pass

    incoming_id = request.headers.get("X-Request-ID")
    request_id = incoming_id.strip() if (incoming_id and len(incoming_id) <= 64) else str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    
    # Defense-in-depth Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "style-src 'self' 'unsafe-inline'; "
        "frame-ancestors 'none';"
    )
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    logger.info(
        f"[{request_id}] {request.method} {request.url.path} "
        f"- Status: {response.status_code} - Time: {process_time:.2f}ms"
    )
    return response

# Global Exception Handlers
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.warning(f"Database Integrity Conflict: {exc}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "A resource conflict occurred. The selected slot or unique resource is already taken."}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact hospital support."}
    )

# Include All API Routers
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.departments import router as departments_router
from app.api.v1.doctors import router as doctors_router
from app.api.v1.patients import router as patients_router
from app.api.v1.appointments import router as appointments_router
from app.api.v1.documents import router as documents_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.rooms import router as rooms_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.ai_chat import router as ai_chat_router
from app.api.v1.staff import router as staff_router
from app.api.v1.encounters import router as encounters_router
from app.api.v1.lab import router as lab_router
from app.api.v1.triage import router as triage_router
from app.api.v1.prescriptions import router as prescriptions_router
from app.api.v1.pharmacy import router as pharmacy_router
from app.api.v1.clinical_scribe import router as scribe_router
from app.api.v1.fhir import router as fhir_router
from app.api.v1.audit_vault import router as audit_vault_router
from app.api.v1.bed_telemetry import router as bed_telemetry_router
from app.api.v1.sbar_handover import router as sbar_handover_router
from app.api.v1.sepsis import router as sepsis_router
from app.api.v1.radiology import router as radiology_router
from app.api.v1.code_blue import router as code_blue_router
from app.api.v1.blood_bank import router as blood_bank_router
from app.api.v1.chemo_safety import router as chemo_safety_router
from app.api.v1.pediatric import router as pediatric_router
from app.api.v1.discharge import router as discharge_router
from app.api.v1.surgical_clearance import router as surgical_clearance_router
from app.api.v1.anesthesia_airway import router as anesthesia_airway_router
from app.api.v1.tpn_nutrition import router as tpn_nutrition_router
from app.api.v1.ai_features import router as ai_features_router

app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(departments_router, prefix=settings.API_V1_STR)
app.include_router(doctors_router, prefix=settings.API_V1_STR)
app.include_router(patients_router, prefix=settings.API_V1_STR)
app.include_router(appointments_router, prefix=settings.API_V1_STR)
app.include_router(encounters_router, prefix=settings.API_V1_STR)
app.include_router(lab_router, prefix=f"{settings.API_V1_STR}/lab")
app.include_router(triage_router, prefix=settings.API_V1_STR)
app.include_router(prescriptions_router, prefix=settings.API_V1_STR)
app.include_router(pharmacy_router, prefix=settings.API_V1_STR)
app.include_router(scribe_router, prefix=settings.API_V1_STR)
app.include_router(fhir_router, prefix=settings.API_V1_STR)
app.include_router(audit_vault_router, prefix=settings.API_V1_STR)
app.include_router(bed_telemetry_router, prefix=settings.API_V1_STR)
app.include_router(sbar_handover_router, prefix=settings.API_V1_STR)
app.include_router(sepsis_router, prefix=settings.API_V1_STR)
app.include_router(radiology_router, prefix=settings.API_V1_STR)
app.include_router(code_blue_router, prefix=settings.API_V1_STR)
app.include_router(blood_bank_router, prefix=settings.API_V1_STR)
app.include_router(chemo_safety_router, prefix=settings.API_V1_STR)
app.include_router(pediatric_router, prefix=settings.API_V1_STR)
app.include_router(discharge_router, prefix=settings.API_V1_STR)
app.include_router(surgical_clearance_router, prefix=settings.API_V1_STR)
app.include_router(anesthesia_airway_router, prefix=settings.API_V1_STR)
app.include_router(tpn_nutrition_router, prefix=settings.API_V1_STR)
app.include_router(staff_router, prefix=settings.API_V1_STR)
app.include_router(documents_router, prefix=settings.API_V1_STR)
app.include_router(notifications_router, prefix=settings.API_V1_STR)
app.include_router(audit_logs_router, prefix=settings.API_V1_STR)
app.include_router(rooms_router, prefix=settings.API_V1_STR)
app.include_router(inventory_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(ai_chat_router, prefix=settings.API_V1_STR)
app.include_router(ai_features_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "project": "MediCore AI",
        "message": "AI Hospital Operating System API is live",
        "health_check": f"{settings.API_V1_STR}/health",
        "docs": f"{settings.API_V1_STR}/docs"
    }
