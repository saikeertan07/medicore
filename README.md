# MediCore AI — AI Hospital Operating System (Step 1 Vertical Slice)

[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2014-black.svg?style=flat&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%200.110-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2016-336791.svg?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Container-Docker%20Compose-2496ED.svg?style=flat&logo=docker)](https://www.docker.com/)

**MediCore AI** is a full-stack hospital operating assistant designed to coordinate clinical scheduling, patient health navigation, physician rosters, and capacity telemetry. 

> [!NOTE]
> **Step 1 Scope**: This repository represents the completed and verified **Step 1 Vertical Slice**:
> **LOGIN → PATIENT AUTHENTICATION → PATIENT DASHBOARD → DOCTOR SEARCH → REAL DOCTOR AVAILABILITY → APPOINTMENT BOOKING → DATABASE CONFIRMATION → NOTIFICATION → AUDIT LOG**.

---

## 🏛️ System Architecture & Status

```
                  ┌────────────────────────────────────────┐
                  │          MediCore AI Web Client        │
                  │   Next.js 14 App Router + Tailwind CSS │
                  └───────────────────┬────────────────────┘
                                      │ REST APIs / Bearer JWT
                                      ▼
                  ┌────────────────────────────────────────┐
                  │           FastAPI Core Engine          │
                  │  • Strict Object-Level RBAC            │
                  │  • Request Correlation ID Middleware   │
                  │  • Shared Schedule Validation Engine   │
                  └─────┬──────────────┬─────────────┬─────┘
                        │              │             │
        ┌───────────────┘              │             └───────────────┐
        ▼                              ▼                             ▼
┌──────────────┐         ┌───────────────────────────┐         ┌──────────────┐
│  PostgreSQL  │         │     AI Agent Subsystem    │         │  Audit Trail │
│  (Authoritative)       │  • Doctor-Patient Bounded │         │  (Sanitized) │
│  • Partial Index       │    Relationship Check     │         │  • Sensitive │
│    uq_doctor_          │  • Configurable Model:    │         │    Field     │
│    active_slot         │    gemini-3.8-flash       │         │    Masking   │
└──────────────┘         └───────────────────────────┘         └──────────────┘
```

### ✅ Implemented Capabilities (Step 1)
- **Authoritative Database Tier**: PostgreSQL 16 is mandatory in production mode (`ENVIRONMENT=production`), failing loudly on connection error with zero silent fallback. Explicit SQLite mode is permitted strictly for local unit testing.
- **Database-Enforced Concurrency**: Partial unique index (`CREATE UNIQUE INDEX uq_doctor_active_slot ON appointments (doctor_id, date, start_time) WHERE status != 'CANCELLED'`). Catching database `IntegrityError` and rolling back returns `HTTP 409 Conflict` during race conditions.
- **Atomic Rescheduling**: Target slot is validated and claimed inside the transaction before the old slot is updated; rollback on conflict preserves the original appointment untouched.
- **Shared Scheduling Engine**: Identical slot validation (`validate_slot_and_schedule`) enforced across availability queries, bookings, and rescheduling (past-date rejection, working hours, grid alignment, slot duration, and doctor/department matching).
- **Object-Level RBAC**: Server-side verification ensures patients cannot book for or inspect other patients, and doctors cannot access appointments of other attending physicians.
- **Encounter-Bounded AI Security**: Complete removal of hardcoded patient IDs. Doctor AI clinical summaries require explicit patient identifiers and strictly verify an active or scheduled clinical encounter exists in the database before disclosing records.
- **Sanitized Audit Trails**: Automatically records all logins, bookings, cancellations, and reschedules with redacted secrets.

### 📋 Planned Capabilities (Future Steps)
- **Session Management**: Step 1 uses Bearer JWT tokens stored in `localStorage`. Production HttpOnly SameSite cookie session management and CSRF tokens are planned for future phases.
- **Advanced Autonomous AI**: Step 1 provides grounded structured tool execution and clinical summarization. Multi-step recursive function-calling loops and streaming are planned for future phases.
- **Compliance Certifications**: Formal third-party HIPAA BAA, SOC 2 Type II, and GDPR certifications are subject to formal enterprise audit processes.
- **Rate Limiting**: Distributed Redis token-bucket rate limiting across API endpoints.

---

## 🚀 Key Portals & Workflows

### 1. Public Portal (12 Pages)
- **Home (`/`)**: Overview, emergency banner, clinical stats, specialties, and testimonials.
- **Departments (`/departments`)**: Specialty directories with attending physician lists.
- **Doctors Directory (`/doctors`, `/doctors/[id]`)**: Searchable physician catalog with real-time availability.
- **Booking Wizard (`/appointments`)**: 5-step interactive wizard with real-time slot generation.
- **Emergency (`/emergency`)**, **Services (`/services`)**, **FAQ (`/faq`)**, **Contact (`/contact`)**, **Auth (`/login`, `/register`)**.

### 2. Patient Portal (9 Pages)
- **Dashboard (`/patient/dashboard`)**: Upcoming visits, vital stats, clinical documents.
- **Appointments (`/patient/appointments`)**: Slot management, atomic rescheduling, and cancellation.
- **Health Navigator AI (`/patient/ai`)**: Policy questions and specialty lookup with medical disclaimers.
- **Documents & Records (`/patient/documents`, `/patient/reports`, `/patient/prescriptions`, `/patient/profile`, `/patient/notifications`)**.

### 3. Doctor Portal (7 Pages)
- **Dashboard (`/doctor/dashboard`)**: Daily consultation queue.
- **Appointments (`/doctor/appointments`)**: Queue management and status transitions.
- **Clinical AI Assistant (`/doctor/ai`)**: Patient history digest (strictly bounded to assigned patients) and clinical protocol search.
- **Roster & Records (`/doctor/patients`, `/doctor/schedule`, `/doctor/documents`, `/doctor/reports`)**.

### 4. Admin Portal (11 Pages)
- **Executive Telemetry (`/admin/dashboard`, `/admin/analytics`)**: Real-time throughput and occupancy charts.
- **Identity & Compliance (`/admin/users`, `/admin/audit-logs`, `/admin/reports`)**: User provisioning and immutable audit trails.
- **Operations (`/admin/patients`, `/admin/doctors`, `/admin/departments`, `/admin/appointments`, `/admin/rooms`, `/admin/inventory`)**.

---

## 🧪 Demo Credentials

| Role | Email Address | Password | Landing Portal |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@medicore.ai` | `Admin@123` | `/admin/dashboard` |
| **Doctor (Cardiology)** | `doctor.chen@medicore.ai` | `Doctor@123` | `/doctor/dashboard` |
| **Doctor (Neurology)** | `doctor.rodriguez@medicore.ai` | `Doctor@123` | `/doctor/dashboard` |
| **Patient** | `patient.sarah@medicore.ai` | `Patient@123` | `/patient/dashboard` |
| **Patient** | `patient.michael@medicore.ai` | `Patient@123` | `/patient/dashboard` |

---

## ⚡ Quickstart Guide

### Option 1: Docker Compose

1. Copy environment template:
   ```bash
   cp .env.example .env
   ```
2. Launch database, backend, and frontend:
   ```bash
   docker compose up --build
   ```
3. Access services:
   - **Frontend UI**: [http://localhost:3000](http://localhost:3000)
   - **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Health Endpoint**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

### Option 2: Local Development Setup

#### 1. Backend (FastAPI)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Seed database
PYTHONPATH=. python -m seed.seed_data

# Start backend
uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend (Next.js 14)
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Verification & Acceptance Testing

### 1. SQLite Local Unit Tests
```bash
cd backend
PYTHONPATH=. ./venv/bin/pytest tests/test_auth.py tests/test_rbac.py tests/test_step1_acceptance.py tests/test_vertical_slice.py -v
```

### 2. PostgreSQL True Concurrency & Persistence Tests
```bash
cd backend
TEST_PG_URL="postgresql://medicore:medicore_secure_pass@localhost:5432/medicore_db" PYTHONPATH=. ./venv/bin/pytest tests/test_concurrency_pg.py -v
```
Verifies:
- Genuine multi-threaded race condition with `threading.Barrier` produces **exactly one 201 winner** and **all other attempts receive 409 Conflict**.
- Transactional rescheduling conflict rollback preserves the original appointment.
- Hard backend restart / connection pool recreation confirms data persistence in PostgreSQL.
