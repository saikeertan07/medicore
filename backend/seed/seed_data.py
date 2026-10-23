import random
from datetime import datetime, date, time, timedelta
from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.models import (
    User, UserRole, Department, Doctor, DoctorSchedule, Patient, Appointment,
    AppointmentType, AppointmentStatus, MedicalDocument, DocumentStatus,
    MedicalReport, Prescription, PatientNote, HospitalService, HospitalPolicy,
    Room, RoomType, RoomStatus, InventoryItem, InventoryStatus, Notification, AuditLog,
    StaffProfile
)
from app.core.migrations import run_step2_migrations, run_step3_migrations, run_step4_migrations

def seed_database():
    db = SessionLocal()
    print("Clearing and recreating tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    run_step2_migrations(engine)
    run_step3_migrations(engine)
    run_step4_migrations(engine)
    print("Seeding MediCore AI database...")

    # 1. Departments (5)
    departments_data = [
        {"name": "Cardiology", "code": "CARD", "floor": "3rd Floor, Wing A", "icon": "Heart", "description": "Comprehensive cardiac diagnostics, advanced interventional cardiology, heart failure management, and preventive heart care."},
        {"name": "Neurology", "code": "NEUR", "floor": "4th Floor, Wing B", "icon": "Brain", "description": "Specialized diagnosis and treatment of brain, spinal cord, nerve, and neuromuscular disorders."},
        {"name": "Orthopedics", "code": "ORTH", "floor": "2nd Floor, Wing C", "icon": "Bone", "description": "State-of-the-art musculoskeletal care, joint replacement, sports injury rehab, and spine surgery."},
        {"name": "Pediatrics", "code": "PEDI", "floor": "1st Floor, Wing A", "icon": "Baby", "description": "Dedicated infant, child, and adolescent healthcare, developmental tracking, and pediatric acute medicine."},
        {"name": "Oncology", "code": "ONCO", "floor": "5th Floor, Cancer Center", "icon": "ShieldAlert", "description": "Holistic cancer diagnosis, chemotherapy, immunotherapy, and supportive oncological care."}
    ]

    dept_objs = []
    for d in departments_data:
        dept = Department(**d)
        db.add(dept)
        dept_objs.append(dept)
    db.commit()

    # 2. Demo Admin, Receptionist, and Nurse Accounts
    admin_user = User(
        email="admin@medicore.ai",
        hashed_password=get_password_hash("Admin@123"),
        full_name="Dr. Eleanor Vance",
        role=UserRole.ADMIN,
        phone="+1-555-0100",
        is_active=True
    )
    db.add(admin_user)

    receptionist_user = User(
        email="receptionist@medicore.ai",
        hashed_password=get_password_hash("Reception@123"),
        full_name="Clara Higgins",
        role=UserRole.RECEPTIONIST,
        phone="+1-555-0150",
        is_active=True
    )
    db.add(receptionist_user)

    nurse_user = User(
        email="nurse.sarah@medicore.ai",
        hashed_password=get_password_hash("Nurse@123"),
        full_name="Nurse Sarah Jenkins",
        role=UserRole.NURSE,
        phone="+1-555-0160",
        is_active=True
    )
    db.add(nurse_user)
    db.commit()

    receptionist_profile = StaffProfile(
        user_id=receptionist_user.id,
        department_id=dept_objs[0].id,
        job_title="Lead Front Desk Receptionist",
        shift="Morning",
        qualifications="Certified Medical Administrative Specialist",
        employee_id="REC-0001"
    )
    db.add(receptionist_profile)

    nurse_profile = StaffProfile(
        user_id=nurse_user.id,
        department_id=dept_objs[0].id,
        job_title="Lead Triage Nurse",
        shift="Morning",
        qualifications="BSN, RN, BLS/ACLS Certified",
        employee_id="NUR-0001"
    )
    db.add(nurse_profile)
    db.commit()

    # 3. Doctors (15 doctors, 3 per department)
    doctor_specs = [
        # Cardiology
        ("Dr. Marcus Chen", "doctor.chen@medicore.ai", "MD, FACC, Harvard Medical", "Cardiologist", 16, 250.00, "301-A", 4.95, "Specializing in complex coronary interventions and advanced echocardiography."),
        ("Dr. Olivia Martinez", "doctor.martinez@medicore.ai", "MD, Johns Hopkins", "Interventional Cardiologist", 12, 220.00, "302-A", 4.88, "Expert in valvular heart disease and rhythm management."),
        ("Dr. Liam Campbell", "doctor.campbell@medicore.ai", "MD, Mayo Clinic", "Cardiovascular Specialist", 9, 190.00, "303-A", 4.85, "Focused on lipidology, cardiac wellness, and hypertension."),
        # Neurology
        ("Dr. Sophia Patel", "doctor.patel@medicore.ai", "MD, Stanford Medicine", "Neurologist", 14, 240.00, "401-B", 4.92, "Specialist in neurodegenerative conditions, stroke recovery, and epilepsy."),
        ("Dr. Alexander Wright", "doctor.wright@medicore.ai", "MD, Columbia University", "Neurophysiologist", 11, 210.00, "402-B", 4.86, "Focusing on migraine disorders and neuromuscular diagnostics."),
        ("Dr. Emma Watson", "doctor.watson@medicore.ai", "MD, Oxford Medical", "Cognitive Neurologist", 8, 185.00, "403-B", 4.80, "Specialist in memory disorders, dementia, and cognitive neuroscience."),
        # Orthopedics
        ("Dr. David Kim", "doctor.kim@medicore.ai", "MD, UCSF Orthopedic", "Orthopedic Surgeon", 15, 260.00, "201-C", 4.96, "Pioneer in robotic total knee and hip replacement surgery."),
        ("Dr. Rachel Green", "doctor.green@medicore.ai", "MD, Duke University", "Sports Medicine Surgeon", 10, 200.00, "202-C", 4.89, "Treating ligament tears, shoulder arthroscopy, and athlete recovery."),
        ("Dr. James Wilson", "doctor.wilson@medicore.ai", "MD, Penn Medicine", "Spine Specialist", 13, 230.00, "203-C", 4.84, "Minimally invasive spine surgery and disc herniation relief."),
        # Pediatrics
        ("Dr. Maya Lin", "doctor.lin@medicore.ai", "MD, Boston Children's", "Chief Pediatrician", 17, 180.00, "101-A", 4.98, "Devoted to developmental pediatrics and newborn intensive care."),
        ("Dr. Ethan Brooks", "doctor.brooks@medicore.ai", "MD, Baylor College", "Pediatric Specialist", 7, 160.00, "102-A", 4.87, "Childhood asthma, allergy management, and adolescent medicine."),
        ("Dr. Grace Taylor", "doctor.taylor@medicore.ai", "MD, Vanderbilt University", "Pediatric Neurologist", 9, 190.00, "103-A", 4.90, "Pediatric seizure management and developmental milestones."),
        # Oncology
        ("Dr. Robert Sterling", "doctor.sterling@medicore.ai", "MD, Memorial Sloan Kettering", "Medical Oncologist", 20, 280.00, "501-O", 4.97, "Leading clinical trials in targeted therapy and immunotherapy."),
        ("Dr. Chloe Bennett", "doctor.bennett@medicore.ai", "MD, MD Anderson", "Hematologist-Oncologist", 12, 230.00, "502-O", 4.91, "Leukemia, lymphoma, and molecular oncology care."),
        ("Dr. Daniel Alvarez", "doctor.alvarez@medicore.ai", "MD, Northwestern", "Radiation Oncologist", 14, 240.00, "503-O", 4.89, "Precision stereotactic radiation and combined modality therapies.")
    ]

    doctor_objs = []
    for idx, (name, email, qual, spec, exp, fee, room, rating, bio) in enumerate(doctor_specs):
        dept_idx = idx // 3
        u = User(
            email=email,
            hashed_password=get_password_hash("Doctor@123"),
            full_name=name,
            role=UserRole.DOCTOR,
            phone=f"+1-555-020{idx:02d}",
            is_active=True
        )
        db.add(u)
        db.commit()

        doc = Doctor(
            user_id=u.id,
            department_id=dept_objs[dept_idx].id,
            specialization=spec,
            qualification=qual,
            experience_years=exp,
            consultation_fee=fee,
            bio=bio,
            room_number=room,
            rating=rating
        )
        db.add(doc)
        db.commit()
        doctor_objs.append(doc)

        # Create Mon-Sun doctor schedules (09:00 to 17:00, 30 min slots)
        for day in range(7):  # Mon-Sun
            sched = DoctorSchedule(
                doctor_id=doc.id,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(17, 0),
                slot_duration_minutes=30,
                is_available=True
            )
            db.add(sched)
        db.commit()

    # 4. Patients (50 patients)
    first_names = ["Sarah", "Michael", "Emily", "Jacob", "Jessica", "David", "Ashley", "Daniel", "Amanda", "James",
                   "Robert", "Jennifer", "William", "Elizabeth", "John", "Megan", "Joseph", "Lauren", "Christopher", "Nicole",
                   "Matthew", "Stephanie", "Anthony", "Samantha", "Donald", "Christine", "Paul", "Amber", "Mark", "Rachel",
                   "George", "Danielle", "Kenneth", "Courtney", "Steven", "Heather", "Edward", "Melissa", "Brian", "Rebecca",
                   "Ronald", "Michelle", "Kevin", "Tiffany", "Thomas", "Chelsea", "Charles", "Diana", "Andrew", "Natalie"]
    last_names = ["Jenkins", "Miller", "Davis", "Wilson", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris",
                  "Martin", "Thompson", "Garcia", "Martinez", "Robinson", "Clark", "Rodriguez", "Lewis", "Lee", "Walker",
                  "Hall", "Allen", "Young", "Hernandez", "King", "Wright", "Lopez", "Hill", "Scott", "Green",
                  "Adams", "Baker", "Gonzalez", "Nelson", "Carter", "Mitchell", "Perez", "Roberts", "Turner", "Phillips",
                  "Campbell", "Parker", "Evans", "Edwards", "Collins", "Stewart", "Sanchez", "Morris", "Rogers", "Reed"]
    blood_groups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

    patient_objs = []
    # Dedicated demo patient
    sarah_user = User(
        email="patient.sarah@medicore.ai",
        hashed_password=get_password_hash("Patient@123"),
        full_name="Sarah Jenkins",
        role=UserRole.PATIENT,
        phone="+1-555-0301",
        is_active=True
    )
    db.add(sarah_user)
    db.commit()

    sarah_patient = Patient(
        patient_number="PAT-202609-000001",
        user_id=sarah_user.id,
        date_of_birth=date(1991, 4, 18),
        gender="Female",
        blood_group="A+",
        emergency_contact="Mark Jenkins (Spouse) - +1-555-0309",
        address="742 Evergreen Terrace, Springfield, OR",
        medical_history_summary="Mild hypertension managed with Lisinopril 10mg daily. No known drug allergies.",
        insurance_provider="Blue Cross Blue Shield Premier",
        insurance_policy_number="BCBS-8892104-A"
    )
    db.add(sarah_patient)
    db.commit()
    patient_objs.append(sarah_patient)

    # Remaining 49 patients
    for i in range(1, 50):
        fn = first_names[i]
        ln = last_names[i]
        email = f"{fn.lower()}.{ln.lower()}{i}@example.com"
        u = User(
            email=email,
            hashed_password=get_password_hash("Patient@123"),
            full_name=f"{fn} {ln}",
            role=UserRole.PATIENT,
            phone=f"+1-555-03{i:02d}",
            is_active=True
        )
        db.add(u)
        db.commit()

        p = Patient(
            patient_number=f"PAT-202609-{i+1:06d}",
            user_id=u.id,
            date_of_birth=date(1965 + (i % 35), (i % 12) + 1, (i % 27) + 1),
            gender="Female" if i % 2 == 0 else "Male",
            blood_group=blood_groups[i % len(blood_groups)],
            emergency_contact=f"Family Member - +1-555-99{i:02d}",
            address=f"{100 + i} Medical Center Blvd, Suite {i}, Metro City",
            medical_history_summary="Routine annual checkups. Minor seasonal allergies." if i % 3 != 0 else "Managed Type 2 Diabetes, controlled on Metformin 500mg.",
            insurance_provider="Aetna Health" if i % 2 == 0 else "UnitedHealthcare",
            insurance_policy_number=f"POL-{100000 + i}"
        )
        db.add(p)
        patient_objs.append(p)
    db.commit()

    # 5. Appointments (100 appointments)
    # 40 past completed, 20 today, 40 upcoming
    today = date.today()
    reasons = [
        "Routine checkup and cardiovascular assessment",
        "Follow-up consultation regarding MRI scan results",
        "Recurring migraines and dizziness evaluation",
        "Chronic knee pain and joint mobility check",
        "Post-surgical follow-up and wound inspection",
        "Annual pediatric developmental exam",
        "Oncology consultation and treatment plan discussion",
        "Chest tightness during moderate exertion",
        "Hypertension medication titration check",
        "Preventive health screening"
    ]

    slots_pool = [
        (time(9, 0), time(9, 30)),
        (time(9, 30), time(10, 0)),
        (time(10, 0), time(10, 30)),
        (time(10, 30), time(11, 0)),
        (time(11, 0), time(11, 30)),
        (time(11, 30), time(12, 0)),
        (time(14, 0), time(14, 30)),
        (time(14, 30), time(15, 0)),
        (time(15, 0), time(15, 30)),
        (time(15, 30), time(16, 0)),
        (time(16, 0), time(16, 30)),
    ]

    # Use a set to track (doctor_id, date, start_time) to avoid duplicate slots
    booked_set = set()
    appointment_counter = 1

    # Sarah's appointments (today, past, upcoming)
    sarah_slots = [
        (today - timedelta(days=14), time(10, 0), time(10, 30), AppointmentStatus.COMPLETED, 0),
        (today, time(14, 0), time(14, 30), AppointmentStatus.CONFIRMED, 0),
        (today + timedelta(days=7), time(11, 0), time(11, 30), AppointmentStatus.CONFIRMED, 3),
    ]

    for app_date, st, et, status_val, doc_idx in sarah_slots:
        doc = doctor_objs[doc_idx]
        app = Appointment(
            appointment_number=f"MED-{app_date.strftime('%Y%m%d')}-{appointment_counter:04d}",
            patient_id=sarah_patient.id,
            doctor_id=doc.id,
            department_id=doc.department_id,
            date=app_date,
            start_time=st,
            end_time=et,
            type=AppointmentType.IN_PERSON,
            status=status_val,
            reason=reasons[0],
            notes="Demo patient appointment"
        )
        db.add(app)
        booked_set.add((doc.id, app_date, st))
        appointment_counter += 1

    # Remaining appointments up to 100
    dates_pool = [
        today - timedelta(days=d) for d in range(1, 30)
    ] + [today] + [
        today + timedelta(days=d) for d in range(1, 30)
    ]

    while len(booked_set) < 100:
        doc = random.choice(doctor_objs)
        pat = random.choice(patient_objs)
        d_val = random.choice(dates_pool)
        st, et = random.choice(slots_pool)

        if (doc.id, d_val, st) in booked_set:
            continue

        check_in_dt = None
        if d_val < today:
            stat = AppointmentStatus.COMPLETED if random.random() > 0.1 else AppointmentStatus.CANCELLED
        elif d_val == today:
            r = random.random()
            if r < 0.35:
                stat = AppointmentStatus.CHECKED_IN
                check_in_dt = datetime.combine(today, st)
            elif r < 0.60:
                stat = AppointmentStatus.IN_PROGRESS
                check_in_dt = datetime.combine(today, st)
            elif r < 0.85:
                stat = AppointmentStatus.CONFIRMED
            else:
                stat = AppointmentStatus.COMPLETED
                check_in_dt = datetime.combine(today, st)
        else:
            stat = AppointmentStatus.CONFIRMED if random.random() > 0.15 else AppointmentStatus.SCHEDULED

        app = Appointment(
            appointment_number=f"MED-{d_val.strftime('%Y%m%d')}-{appointment_counter:04d}",
            patient_id=pat.id,
            doctor_id=doc.id,
            department_id=doc.department_id,
            date=d_val,
            start_time=st,
            end_time=et,
            type=AppointmentType.IN_PERSON if random.random() > 0.3 else AppointmentType.TELECONSULTATION,
            status=stat,
            check_in_time=check_in_dt,
            reason=random.choice(reasons),
            notes="Generated clinical appointment record."
        )
        db.add(app)
        booked_set.add((doc.id, d_val, st))
        appointment_counter += 1
    db.commit()

    # 6. Medical Documents (20)
    doc_titles = [
        ("Comprehensive Metabolic Panel (CMP)", "pdf", 245000, "CMP report indicating normal electrolytes, fasting glucose 94 mg/dL, BUN 14, creatinine 0.9 mg/dL. Renal and liver profiles within healthy limits."),
        ("12-Lead Electrocardiogram (ECG)", "pdf", 312000, "Normal sinus rhythm at 68 bpm. PR interval 158 ms, QRS duration 86 ms, QTc 410 ms. No acute ST-T wave changes or ischemic patterns."),
        ("Echocardiogram Complete Study", "pdf", 1450000, "Left ventricular ejection fraction (LVEF) preserved at 62%. Normal left ventricular chamber dimensions. Trace mitral regurgitation."),
        ("Chest X-Ray (PA & Lateral)", "png", 4200000, "Clear lung fields bilaterally without consolidation, effusion, or pneumothorax. Cardiothoracic ratio within normal physiological limits."),
        ("Brain MRI with Contrast", "pdf", 2800000, "No acute intracranial hemorrhage, major territorial infarction, or mass effect. Mild age-appropriate white matter hyperintensities."),
        ("Lipid Panel & Biomarkers", "pdf", 185000, "Total cholesterol 178 mg/dL, Triglycerides 124 mg/dL, HDL 54 mg/dL, LDL 99 mg/dL. High-sensitivity CRP 0.8 mg/L (low cardiovascular risk)."),
        ("Hemoglobin A1c Glycemic Report", "pdf", 192000, "HbA1c level measured at 5.4% (standard non-diabetic reference range < 5.7%). Average estimated glucose 108 mg/dL."),
        ("Knee MRI (Right Joint)", "pdf", 3100000, "Mild degenerative thinning of the medial meniscus. Cruciate and collateral ligaments intact. Trace joint effusion noted."),
        ("CBC with Differential", "pdf", 160000, "WBC 6.8 x10^3/uL, RBC 4.7 x10^6/uL, Hemoglobin 14.2 g/dL, Hematocrit 42.1%, Platelets 260 x10^3/uL. Normal indices."),
        ("Holter Monitor 48-Hour Rhythm", "pdf", 890000, "Predominant sinus rhythm throughout 48-hour recording. Average heart rate 72 bpm. Rare isolated PVCs (<0.1% burden). No sustained arrhythmias.")
    ]

    for i in range(20):
        title, ext, sz, summary = doc_titles[i % len(doc_titles)]
        pat = sarah_patient if i < 3 else random.choice(patient_objs)
        med_doc = MedicalDocument(
            patient_id=pat.id,
            uploaded_by_id=pat.user_id,
            file_name=f"{title.replace(' ', '_').replace('(', '').replace(')', '')}_{1000+i}.{ext}",
            file_type=f"application/{ext}" if ext == "pdf" else f"image/{ext}",
            file_size=sz,
            file_path=f"uploads/doc_{1000+i}.{ext}",
            status=DocumentStatus.COMPLETED,
            summary=summary,
            extracted_data={
                "title": title,
                "confidence_score": 0.98,
                "reviewed_by_clinician": True,
                "disclaimer": "AI-generated clinical summary for healthcare provider review only. Not an autonomous diagnosis."
            },
            tags="Lab,Cardiology" if "ECG" in title or "CMP" in title else "Imaging,Radiology"
        )
        db.add(med_doc)
    db.commit()

    # 7. Hospital Services (10)
    services_data = [
        ("Comprehensive Cardiac Screening", 0, "Complete cardiac assessment with ECG, lipid panel, and doctor consultation.", 250.00, 45),
        ("Advanced Echocardiography (TTE)", 0, "Transthoracic ultrasound evaluating cardiac chamber structure and valve dynamics.", 450.00, 45),
        ("Brain & Spinal Diagnostic Consult", 1, "Specialist neurological evaluation with reflex and sensory nerve testing.", 220.00, 40),
        ("Sleep Study Polysomnography", 1, "Overnight diagnostic evaluation measuring sleep stages and respiratory patterns.", 850.00, 480),
        ("Total Joint Mobility Consultation", 2, "Orthopedic assessment with digital range-of-motion mapping and rehab planning.", 180.00, 30),
        ("Pediatric Annual Wellness Exam", 3, "Comprehensive growth, vaccination status, vision, and hearing screening.", 150.00, 30),
        ("Pediatric Allergy & Immunology Panel", 3, "Skin prick and blood antigen testing for common food and environmental triggers.", 320.00, 60),
        ("Oncological Multi-Disciplinary Review", 4, "Tumor board consultation formulating customized molecular treatment pathways.", 500.00, 60),
        ("Outpatient Minor Infusion Therapy", 4, "Hydration, electrolyte replacement, and monitored intravenous infusion.", 350.00, 120),
        ("Executive Preventive Health Checkup", 0, "Full-day executive screening encompassing cardiology, imaging, and biochemistry.", 1200.00, 240)
    ]
    for name, d_idx, desc, price, dur in services_data:
        srv = HospitalService(
            name=name,
            department_id=dept_objs[d_idx].id,
            description=desc,
            price=price,
            duration_minutes=dur,
            is_active=True
        )
        db.add(srv)
    db.commit()

    # 8. Hospital Policies for RAG (5)
    policies_data = [
        ("APPOINTMENT_POLICY", "Appointment Scheduling and Cancellation Policy", 
         "Appointments can be scheduled up to 90 days in advance through the MediCore portal. Cancellations or rescheduling requests must be submitted at least 24 hours prior to the scheduled consultation time. Late cancellations or no-shows may incur a $50 administrative fee. Same-day urgent slots are released at 08:00 AM daily."),
        ("VISITING_HOURS", "Inpatient and Intensive Care Visiting Hours", 
         "General inpatient visiting hours are from 09:00 AM to 08:00 PM daily. A maximum of two visitors are permitted per patient room at any one time. Intensive Care Unit (ICU) visiting hours are strictly restricted to 10:00 AM - 11:30 AM and 05:00 PM - 06:30 PM. Children under 12 years of age require prior nursing supervisor approval."),
        ("INSURANCE_BILLING", "Insurance Coverage and Co-Payment Guidelines", 
         "MediCore AI Hospital accepts major commercial insurance carriers including Blue Cross Blue Shield, Aetna, UnitedHealthcare, Cigna, and Medicare. In-network preventive screenings are covered at 100%. Patients must present insurance cards and valid photo identification upon arrival. Co-payments are collected at check-in."),
        ("EMERGENCY_TRIAGE", "Emergency Department Clinical Triage Guidelines", 
         "The Emergency Department is open 24 hours a day, 7 days a week. Patients are triaged utilizing the Emergency Severity Index (ESI Levels 1 through 5). Level 1 patients requiring immediate life-saving resuscitation are attended to instantaneously. If you are experiencing chest pain, difficulty breathing, or severe trauma, call 911 immediately."),
        ("TELEHEALTH_POLICY", "Teleconsultation Patient Instructions", 
         "Teleconsultations require a high-speed internet connection and a camera-enabled device. Patients must log in to the MediCore portal 5 minutes prior to their appointment. Teleconsultations are not suitable for medical emergencies, severe trauma, or acute neurological deficits.")
    ]
    for cat, title, content in policies_data:
        pol = HospitalPolicy(
            category=cat,
            title=title,
            content=content,
            effective_date=date(2025, 1, 1),
            is_published=True
        )
        db.add(pol)
    db.commit()

    # 9. Hospital Rooms (15)
    room_types = [RoomType.GENERAL, RoomType.PRIVATE, RoomType.ICU, RoomType.OPD, RoomType.OPERATION_THEATER]
    for r_num in range(101, 116):
        dept = random.choice(dept_objs)
        r_type = room_types[r_num % len(room_types)]
        stat = RoomStatus.AVAILABLE if r_num % 3 != 0 else RoomStatus.OCCUPIED
        room = Room(
            room_number=f"R-{r_num}",
            department_id=dept.id,
            room_type=r_type,
            status=stat,
            bed_count=1 if r_type in [RoomType.PRIVATE, RoomType.ICU, RoomType.OPERATION_THEATER] else 4,
            floor=f"Floor {r_num // 100}"
        )
        db.add(room)
    db.commit()

    # 10. Inventory Items (20)
    inventory_data = [
        ("Disposable Surgical Masks (Box of 50)", "PPE", 450, "Box", 100, InventoryStatus.IN_STOCK, "MedSupply Corp"),
        ("N95 Particulate Respirator (Box of 20)", "PPE", 80, "Box", 50, InventoryStatus.IN_STOCK, "3M Healthcare"),
        ("Nitrile Examination Gloves (M)", "PPE", 32, "Box", 50, InventoryStatus.LOW_STOCK, "SafeTouch Medical"),
        ("Nitrile Examination Gloves (L)", "PPE", 22, "Box", 50, InventoryStatus.LOW_STOCK, "SafeTouch Medical"),
        ("Sterile Disposable Syringes 5ml", "Consumables", 1200, "Units", 300, InventoryStatus.IN_STOCK, "BD Medical"),
        ("IV Cannula 20G (Pink)", "Consumables", 480, "Units", 150, InventoryStatus.IN_STOCK, "B. Braun"),
        ("Sodium Chloride 0.9% IV Infusion 500ml", "Pharmaceuticals", 320, "Bags", 100, InventoryStatus.IN_STOCK, "Baxter Healthcare"),
        ("Ringer's Lactate Solution 500ml", "Pharmaceuticals", 210, "Bags", 80, InventoryStatus.IN_STOCK, "Baxter Healthcare"),
        ("Lisinopril 10mg Tablets (Bottle of 100)", "Pharmaceuticals", 45, "Bottles", 20, InventoryStatus.IN_STOCK, "Teva Pharma"),
        ("Atorvastatin 20mg Tablets (Bottle of 100)", "Pharmaceuticals", 38, "Bottles", 20, InventoryStatus.IN_STOCK, "Pfizer Inc"),
        ("Metformin 500mg Tablets (Bottle of 100)", "Pharmaceuticals", 12, "Bottles", 25, InventoryStatus.LOW_STOCK, "Mylan Labs"),
        ("Epinephrine Auto-Injectors 0.3mg", "Emergency Meds", 14, "Units", 15, InventoryStatus.LOW_STOCK, "Viatris"),
        ("Defibrillator Pediatric Electrode Pads", "Emergency Equipment", 6, "Sets", 10, InventoryStatus.CRITICAL, "Philips Healthcare"),
        ("Adult ECG Limb Electrodes (Pack of 100)", "Diagnostics", 85, "Packs", 30, InventoryStatus.IN_STOCK, "ConMed"),
        ("Antiseptic Betadine Povidone-Iodine 500ml", "Surgical Supplies", 40, "Bottles", 15, InventoryStatus.IN_STOCK, "Purdue Pharma"),
        ("Surgical Scalpel Blades #10 (Box of 100)", "Surgical Supplies", 18, "Boxes", 10, InventoryStatus.IN_STOCK, "Swann-Morton"),
        ("Vicryl 3-0 Absorbable Sutures", "Surgical Supplies", 28, "Boxes", 20, InventoryStatus.IN_STOCK, "Ethicon"),
        ("Digital Infrared Thermometer", "Diagnostics", 24, "Units", 10, InventoryStatus.IN_STOCK, "Welch Allyn"),
        ("Pulse Oximeter Fingertip Sensors", "Diagnostics", 19, "Units", 12, InventoryStatus.IN_STOCK, "Nonin Medical"),
        ("Biohazard Disposal Waste Bags (Roll of 50)", "Disposal", 55, "Rolls", 25, InventoryStatus.IN_STOCK, "Medline Industries")
    ]
    for name, cat, qty, unit, reorder, stat, sup in inventory_data:
        inv = InventoryItem(
            item_name=name,
            category=cat,
            quantity=qty,
            unit=unit,
            reorder_level=reorder,
            status=stat,
            supplier=sup
        )
        db.add(inv)
    db.commit()

    # 11. Notifications for Sarah & Doctors
    notif1 = Notification(
        user_id=sarah_user.id,
        title="Welcome to MediCore AI",
        message="Your patient portal account has been activated. You can now schedule appointments and consult our medical assistant.",
        type="SYSTEM",
        is_read=True
    )
    notif2 = Notification(
        user_id=sarah_user.id,
        title="Consultation Reminder",
        message="You have a scheduled consultation with Dr. Marcus Chen today at 14:00.",
        type="APPOINTMENT",
        is_read=False,
        link="/patient/appointments"
    )
    db.add_all([notif1, notif2])
    db.commit()

    # 12. Initial Audit Log Entry
    audit_init = AuditLog(
        user_id=admin_user.id,
        action="DATABASE_SEED",
        resource_type="System",
        resource_id="0",
        details={"departments": 5, "doctors": 15, "patients": 50, "appointments": 100},
        ip_address="127.0.0.1"
    )
    db.add(audit_init)
    db.commit()

    db.close()
    print("✓ Successfully seeded 5 departments, 15 doctors, 50 patients, 100 appointments, 20 documents, 10 services, 20 inventory items, and policies.")
    print("Demo Accounts:")
    print(" - Admin:   admin@medicore.ai / Admin@123")
    print(" - Doctor:  doctor.chen@medicore.ai / Doctor@123")
    print(" - Patient: patient.sarah@medicore.ai / Patient@123")

if __name__ == "__main__":
    seed_database()
