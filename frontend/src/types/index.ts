export type UserRole = 'PATIENT' | 'DOCTOR' | 'STAFF' | 'ADMIN' | 'RECEPTIONIST' | 'NURSE';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  phone?: string;
  patient_id?: number;
  doctor_id?: number;
  is_active: boolean;
  created_at: string;
}

export interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface Department {
  id: number;
  name: string;
  code: string;
  description?: string;
  floor?: string;
  icon?: string;
  is_active?: boolean;
}

export interface DoctorSchedule {
  id: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
  slot_duration_minutes: number;
  is_available: boolean;
}

export interface Doctor {
  id: number;
  user_id: number;
  full_name: string;
  email: string;
  department_id: number;
  department_name?: string;
  specialization: string;
  qualification: string;
  experience_years: number;
  consultation_fee: number;
  bio?: string;
  room_number?: string;
  rating: number;
  schedules?: DoctorSchedule[];
}

export interface TimeSlot {
  start_time: string;
  end_time: string;
  is_available: boolean;
}

export interface Patient {
  id: number;
  patient_number?: string;
  user_id?: number;
  full_name: string;
  email?: string;
  phone?: string;
  date_of_birth?: string;
  gender?: string;
  blood_group?: string;
  emergency_contact?: string;
  address?: string;
  medical_history_summary?: string;
  insurance_provider?: string;
  insurance_policy_number?: string;
  created_at: string;
}

export interface StaffMember {
  id: number;
  email: string;
  full_name: string;
  phone?: string;
  role: UserRole;
  is_active: boolean;
  department_id?: number;
  department_name?: string;
  job_title?: string;
  shift?: string;
  qualifications?: string;
  employee_id?: string;
  doctor_id?: number;
  created_at: string;
}

export interface Appointment {
  id: number;
  appointment_number: string;
  patient_id: number;
  patient_name?: string;
  doctor_id: number;
  doctor_name?: string;
  doctor_specialization?: string;
  department_id: number;
  department_name?: string;
  date: string;
  start_time: string;
  end_time: string;
  type: 'IN_PERSON' | 'TELECONSULTATION';
  status: 'SCHEDULED' | 'CONFIRMED' | 'CHECKED_IN' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED' | 'NO_SHOW';
  check_in_time?: string;
  reason: string;
  notes?: string;
  created_at: string;
}

export interface MedicalDocument {
  id: number;
  patient_id: number;
  patient_name?: string;
  file_name: string;
  file_type: string;
  file_size: number;
  status: 'UPLOADING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  summary?: string;
  extracted_data?: Record<string, any>;
  tags?: string;
  created_at: string;
}

export interface NotificationItem {
  id: number;
  user_id: number;
  title: string;
  message: string;
  type: string;
  is_read: boolean;
  link?: string;
  created_at: string;
}

export interface AuditLogItem {
  id: number;
  user_id?: number;
  user_email?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  details?: Record<string, any>;
  ip_address?: string;
  created_at: string;
}

export interface DashboardMetrics {
  summary: {
    total_patients: number;
    total_doctors: number;
    today_appointments: number;
    upcoming_appointments: number;
    completed_appointments: number;
    cancelled_appointments: number;
    available_rooms: number;
    total_rooms: number;
    inventory_alerts: number;
  };
  department_usage: { name: string; value: number }[];
  status_distribution: { name: string; value: number }[];
  appointment_trends: { date: string; appointments: number }[];
  doctor_workload: { doctor: string; department: string; appointments: number }[];
}

export interface AIChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  tool_calls?: any[];
  sources?: any[];
  created_at: string;
}

// Step 3 Clinical Documentation / EMR Types
export type EncounterType = 'OUTPATIENT' | 'FOLLOW_UP' | 'WALK_IN';
export type EncounterStatus = 'OPEN' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
export type ClinicalNoteStatus = 'DRAFT' | 'FINAL' | 'AMENDED';
export type DiagnosisType = 'PRIMARY' | 'SECONDARY' | 'WORKING' | 'SUSPECTED';

export interface Encounter {
  id: number;
  encounter_number: string;
  patient_id: number;
  patient_name?: string;
  appointment_id?: number;
  appointment_number?: string;
  attending_doctor_id: number;
  doctor_name?: string;
  department_id: number;
  department_name?: string;
  encounter_type: EncounterType;
  status: EncounterStatus;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface EncounterVitals {
  id: number;
  encounter_id: number;
  patient_id: number;
  recorded_by_id: number;
  recorded_by_name?: string;
  temperature_c?: number;
  heart_rate?: number;
  respiratory_rate?: number;
  systolic_bp?: number;
  diastolic_bp?: number;
  oxygen_saturation?: number;
  height_cm?: number;
  weight_kg?: number;
  bmi?: number;
  pain_score?: number;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ClinicalNote {
  id: number;
  encounter_id: number;
  patient_id: number;
  doctor_id: number;
  doctor_name?: string;
  author_id: number;
  author_name?: string;
  status: ClinicalNoteStatus;
  version: number;
  parent_note_id?: number;
  chief_complaint?: string;
  history_of_present_illness?: string;
  symptoms?: string;
  medical_history_notes?: string;
  examination_findings?: string;
  vitals_summary?: string;
  observations?: string;
  clinical_assessment?: string;
  differential_diagnosis?: string;
  treatment_plan?: string;
  patient_instructions?: string;
  follow_up_instructions?: string;
  follow_up_date?: string;
  recommendations?: string;
  created_at: string;
  updated_at: string;
  finalized_at?: string;
  amended_at?: string;
  amendment_reason?: string;
}

export interface ClinicalDiagnosis {
  id: number;
  encounter_id: number;
  patient_id: number;
  doctor_id: number;
  doctor_name?: string;
  name: string;
  code?: string;
  code_system?: string;
  type: DiagnosisType;
  notes?: string;
  created_at: string;
}

export interface ClinicalTimelineEntry {
  date: string;
  entry_type: 'ENCOUNTER' | 'VITALS' | 'CLINICAL_NOTE' | 'DIAGNOSIS';
  encounter_id: number;
  encounter_number: string;
  doctor_name?: string;
  department_name?: string;
  summary?: string;
  details: Record<string, any>;
}

// Step 4 Laboratory & Diagnostics Types

export type LabOrderPriority = 'ROUTINE' | 'URGENT' | 'STAT';
export type LabOrderStatus = 'DRAFT' | 'ORDERED' | 'PARTIALLY_COLLECTED' | 'COLLECTED' | 'PROCESSING' | 'RESULTS_PENDING' | 'VERIFIED' | 'COMPLETED' | 'CANCELLED';
export type LabOrderItemStatus = 'PENDING' | 'COLLECTED' | 'RECEIVED' | 'PROCESSING' | 'COMPLETED' | 'CANCELLED';
export type LabSampleStatus = 'PENDING' | 'COLLECTED' | 'RECEIVED' | 'PROCESSING' | 'COMPLETED' | 'REJECTED';
export type LabResultStatus = 'PENDING' | 'ENTERED' | 'VERIFIED' | 'FINAL' | 'AMENDED';
export type AbnormalFlag = 'NORMAL' | 'HIGH' | 'LOW' | 'ABNORMAL' | 'CRITICAL';

export interface LabTestDefinition {
  id: number;
  code: string;
  name: string;
  category?: string;
  specimen_type: string;
  default_unit?: string;
  reference_range?: string;
  description?: string;
  turnaround_hours?: number;
  is_active: boolean;
  created_at: string;
}

export interface LabResult {
  id: number;
  order_item_id: number;
  patient_id: number;
  test_id: number;
  test_name?: string;
  test_code?: string;
  value: string;
  numeric_value?: number;
  unit?: string;
  reference_range?: string;
  abnormal_flag: AbnormalFlag;
  status: LabResultStatus;
  comments?: string;
  parent_result_id?: number;
  entered_by_id: number;
  entered_by_name?: string;
  entered_at: string;
  verified_by_id?: number;
  verified_by_name?: string;
  verified_at?: string;
  amendment_reason?: string;
  amended_by_id?: number;
  amended_at?: string;
  created_at: string;
  updated_at: string;
}

export interface LabOrderItem {
  id: number;
  order_id: number;
  test_id: number;
  test_name?: string;
  test_code?: string;
  sample_id?: number;
  sample_accession?: string;
  status: LabOrderItemStatus;
  notes?: string;
  result?: LabResult;
  created_at: string;
  updated_at: string;
}

export interface LabSample {
  id: number;
  accession_number: string;
  order_id: number;
  specimen_type: string;
  status: LabSampleStatus;
  collected_at?: string;
  collected_by_id?: number;
  collected_by_name?: string;
  received_at?: string;
  received_by_id?: number;
  received_by_name?: string;
  rejected_at?: string;
  rejected_by_id?: number;
  rejection_reason?: string;
  created_at: string;
  updated_at: string;
}

export interface LabOrder {
  id: number;
  order_number: string;
  patient_id: number;
  patient_name?: string;
  ordering_doctor_id: number;
  doctor_name?: string;
  encounter_id?: number;
  encounter_number?: string;
  status: LabOrderStatus;
  priority: LabOrderPriority;
  clinical_indication?: string;
  notes?: string;
  ordered_at: string;
  cancelled_at?: string;
  cancellation_reason?: string;
  items: LabOrderItem[];
  samples: LabSample[];
  created_at: string;
  updated_at: string;
}

