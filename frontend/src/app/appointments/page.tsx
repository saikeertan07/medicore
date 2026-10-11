"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { useAuth } from "@/lib/auth-context";
import { api, ApiError } from "@/lib/api";
import { Department, Doctor, TimeSlot, Appointment } from "@/types";
import { 
  Calendar as CalendarIcon, Clock, CheckCircle2, AlertCircle, 
  ArrowRight, ArrowLeft, User, Stethoscope, Building2, Phone
} from "lucide-react";

function AppointmentsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialDoctorId = searchParams.get("doctor_id");
  const initialDeptId = searchParams.get("dept");

  const { user, isAuthenticated } = useAuth();

  // Wizard Steps: 1: Department, 2: Doctor, 3: Date & Slot, 4: Details & Confirm, 5: Success
  const [step, setStep] = useState<number>(initialDoctorId ? 3 : (initialDeptId ? 2 : 1));
  
  const [departments, setDepartments] = useState<Department[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  
  const [selectedDeptId, setSelectedDeptId] = useState<number | null>(initialDeptId ? parseInt(initialDeptId) : null);
  const [selectedDoctorId, setSelectedDoctorId] = useState<number | null>(initialDoctorId ? parseInt(initialDoctorId) : null);
  const [selectedDoctor, setSelectedDoctor] = useState<Doctor | null>(null);
  
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const [selectedDate, setSelectedDate] = useState<string>(tomorrow.toISOString().split("T")[0]);
  
  const [slots, setSlots] = useState<TimeSlot[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(null);
  
  const [appointmentType, setAppointmentType] = useState<"IN_PERSON" | "TELECONSULTATION">("IN_PERSON");
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");

  // Guest/Unauthenticated registration state
  const [guestEmail, setGuestEmail] = useState("");
  const [guestName, setGuestName] = useState("");
  const [guestPhone, setGuestPhone] = useState("");

  const [isLoadingSlots, setIsLoadingSlots] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [confirmedAppointment, setConfirmedAppointment] = useState<Appointment | null>(null);

  useEffect(() => {
    api.get<Department[]>("/departments").then(setDepartments).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedDeptId) {
      api.get<Doctor[]>(`/doctors?department_id=${selectedDeptId}`).then(setDoctors).catch(() => {});
    } else {
      api.get<Doctor[]>("/doctors").then(setDoctors).catch(() => {});
    }
  }, [selectedDeptId]);

  useEffect(() => {
    if (selectedDoctorId) {
      api.get<Doctor>(`/doctors/${selectedDoctorId}`).then(doc => {
        setSelectedDoctor(doc);
        if (!selectedDeptId) setSelectedDeptId(doc.department_id);
      }).catch(() => {});
    }
  }, [selectedDoctorId]);

  // Fetch real available slots whenever doctor or date changes
  useEffect(() => {
    if (selectedDoctorId && selectedDate) {
      setIsLoadingSlots(true);
      setErrorMessage(null);
      api.get<{ slots: TimeSlot[] }>(`/appointments/available-slots?doctor_id=${selectedDoctorId}&date=${selectedDate}`)
        .then(res => {
          setSlots(res.slots);
          setSelectedSlot(null);
        })
        .catch(err => {
          setErrorMessage(err.message || "Failed to load slots");
        })
        .finally(() => setIsLoadingSlots(false));
    }
  }, [selectedDoctorId, selectedDate]);

  const handleBook = async () => {
    if (!selectedDoctorId || !selectedDeptId || !selectedSlot) {
      setErrorMessage("Please select a doctor, date, and time slot.");
      return;
    }

    if (!reason.trim()) {
      setErrorMessage("Please provide a reason for the consultation.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      let activeToken = localStorage.getItem("medicore_token");

      // If user is not logged in, auto-register them as patient or prompt login
      if (!isAuthenticated || !activeToken) {
        if (!guestEmail || !guestName) {
          setErrorMessage("Please enter your name and email to proceed with booking.");
          setIsSubmitting(false);
          return;
        }

        try {
          const regRes = await api.post<any>("/auth/register", {
            email: guestEmail,
            full_name: guestName,
            phone: guestPhone || undefined,
            password: "PatientDefault@123" // Temporary default secure password
          });
          localStorage.setItem("medicore_token", regRes.access_token);
          activeToken = regRes.access_token;
        } catch (regErr: any) {
          // If already exists, user must log in
          if (regErr.message?.includes("already exists")) {
            setErrorMessage("An account with this email already exists. Please log in first.");
            setIsSubmitting(false);
            return;
          }
          throw regErr;
        }
      }

      // Create appointment
      const payload = {
        doctor_id: selectedDoctorId,
        department_id: selectedDeptId,
        date: selectedDate,
        start_time: selectedSlot.start_time,
        end_time: selectedSlot.end_time,
        type: appointmentType,
        reason: reason.trim(),
        notes: notes.trim() || undefined
      };

      const result = await api.post<Appointment>("/appointments", payload);
      setConfirmedAppointment(result);
      setStep(5); // Success step
    } catch (err: any) {
      if (err.status === 409 || err.message?.includes("already booked") || err.message?.includes("conflict")) {
        setErrorMessage("Slot conflict: This slot was just reserved by someone else. Please select another time.");
        // Refresh slots
        if (selectedDoctorId && selectedDate) {
          api.get<{ slots: TimeSlot[] }>(`/appointments/available-slots?doctor_id=${selectedDoctorId}&date=${selectedDate}`)
            .then(res => setSlots(res.slots));
        }
      } else {
        setErrorMessage(err.message || "Failed to confirm appointment. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <PublicNav />

      <main className="flex-1 max-w-5xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-8">
          <span className="text-xs font-bold tracking-wider uppercase text-medicore-600">Real-Time Scheduling Engine</span>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight mt-1">Book a Doctor's Consultation</h1>
          <p className="text-sm text-slate-500 mt-2">Zero wait times. Live availability verified directly against physician calendars.</p>
        </div>

        {/* STEP PROGRESS BAR */}
        <div className="mb-10 flex items-center justify-center">
          <div className="flex items-center gap-3 text-xs font-semibold">
            <span className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 1 ? "bg-medicore-600 text-white" : "bg-slate-200 text-slate-600"}`}>1</span>
            <span className={step >= 1 ? "text-slate-900" : "text-slate-400"}>Department</span>
            <div className={`w-8 h-0.5 ${step >= 2 ? "bg-medicore-600" : "bg-slate-200"}`}></div>

            <span className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 2 ? "bg-medicore-600 text-white" : "bg-slate-200 text-slate-600"}`}>2</span>
            <span className={step >= 2 ? "text-slate-900" : "text-slate-400"}>Doctor</span>
            <div className={`w-8 h-0.5 ${step >= 3 ? "bg-medicore-600" : "bg-slate-200"}`}></div>

            <span className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 3 ? "bg-medicore-600 text-white" : "bg-slate-200 text-slate-600"}`}>3</span>
            <span className={step >= 3 ? "text-slate-900" : "text-slate-400"}>Date & Slot</span>
            <div className={`w-8 h-0.5 ${step >= 4 ? "bg-medicore-600" : "bg-slate-200"}`}></div>

            <span className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 4 ? "bg-medicore-600 text-white" : "bg-slate-200 text-slate-600"}`}>4</span>
            <span className={step >= 4 ? "text-slate-900" : "text-slate-400"}>Confirm</span>
          </div>
        </div>

        {errorMessage && (
          <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div className="flex-1">{errorMessage}</div>
          </div>
        )}

        {/* STEP 1: SELECT DEPARTMENT */}
        {step === 1 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm space-y-6">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <Building2 className="w-5 h-5 text-medicore-600" />
              <span>Step 1: Select Clinical Department</span>
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {departments.map((dept) => (
                <button
                  key={dept.id}
                  onClick={() => {
                    setSelectedDeptId(dept.id);
                    setStep(2);
                  }}
                  className={`p-5 rounded-xl border text-left transition flex flex-col justify-between ${
                    selectedDeptId === dept.id 
                      ? "border-medicore-600 bg-medicore-50/50 ring-2 ring-medicore-500/20" 
                      : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                  }`}
                >
                  <div>
                    <h3 className="font-bold text-slate-900 text-base">{dept.name}</h3>
                    <p className="text-xs text-slate-500 mt-1 line-clamp-2">{dept.description}</p>
                  </div>
                  <span className="text-[11px] text-medicore-600 font-semibold mt-3 block">{dept.floor || "Main Hospital"}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* STEP 2: SELECT DOCTOR */}
        {step === 2 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                <Stethoscope className="w-5 h-5 text-medicore-600" />
                <span>Step 2: Choose Specialist Doctor</span>
              </h2>
              <button onClick={() => setStep(1)} className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1">
                <ArrowLeft className="w-3.5 h-3.5" /> Back to Departments
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {doctors.map((doc) => (
                <div
                  key={doc.id}
                  onClick={() => {
                    setSelectedDoctorId(doc.id);
                    setSelectedDoctor(doc);
                    setStep(3);
                  }}
                  className={`p-5 rounded-xl border cursor-pointer transition flex flex-col justify-between ${
                    selectedDoctorId === doc.id
                      ? "border-medicore-600 bg-medicore-50/50 ring-2 ring-medicore-500/20"
                      : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-medicore-600">{doc.specialization}</span>
                      <span className="text-xs font-bold text-amber-500">⭐ {doc.rating}</span>
                    </div>
                    <h3 className="font-bold text-slate-900 text-base">{doc.full_name}</h3>
                    <p className="text-xs text-slate-400 mt-0.5">{doc.qualification}</p>
                    <p className="text-xs text-slate-500 mt-2 line-clamp-2">{doc.bio}</p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-900">${doc.consultation_fee} fee</span>
                    <span className="text-medicore-600 font-semibold flex items-center gap-1">Select <ArrowRight className="w-3.5 h-3.5" /></span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* STEP 3: DATE & AVAILABLE TIME SLOT */}
        {step === 3 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                  <Clock className="w-5 h-5 text-medicore-600" />
                  <span>Step 3: Select Date & Available Time Slot</span>
                </h2>
                {selectedDoctor && (
                  <p className="text-xs text-slate-500 mt-1">Consulting with <span className="font-semibold text-slate-800">{selectedDoctor.full_name}</span> ({selectedDoctor.specialization})</p>
                )}
              </div>
              <button onClick={() => setStep(2)} className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1">
                <ArrowLeft className="w-3.5 h-3.5" /> Back to Doctors
              </button>
            </div>

            {/* Date Picker Input */}
            <div className="max-w-xs">
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1.5">Consultation Date</label>
              <input
                type="date"
                min={new Date().toISOString().split("T")[0]}
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm font-medium text-slate-900 outline-none focus:border-medicore-500 focus:ring-1 focus:ring-medicore-500"
              />
            </div>

            {/* Time Slot Picker Grid */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide mb-3">
                Live Doctor Availability ({selectedDate})
              </label>

              {isLoadingSlots ? (
                <div className="py-8 text-center text-sm text-slate-400">Querying real-time schedule...</div>
              ) : slots.length === 0 ? (
                <div className="py-8 text-center text-sm text-slate-400">No time slots configured for this date. Please choose another date.</div>
              ) : (
                <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2.5">
                  {slots.map((s, idx) => (
                    <button
                      key={idx}
                      disabled={!s.is_available}
                      onClick={() => setSelectedSlot(s)}
                      className={`py-2.5 px-3 rounded-xl text-xs font-semibold border transition ${
                        !s.is_available 
                          ? "bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed line-through" 
                          : selectedSlot?.start_time === s.start_time
                          ? "bg-medicore-600 text-white border-medicore-600 shadow-sm"
                          : "bg-white text-slate-700 border-slate-200 hover:border-medicore-400 hover:bg-medicore-50"
                      }`}
                    >
                      {s.start_time.substring(0, 5)}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="pt-4 flex justify-end">
              <button
                disabled={!selectedSlot}
                onClick={() => setStep(4)}
                className="bg-medicore-600 hover:bg-medicore-700 disabled:opacity-50 text-white font-medium px-6 py-2.5 rounded-xl text-sm transition flex items-center gap-2"
              >
                <span>Continue to Details</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* STEP 4: DETAILS & CONFIRMATION */}
        {step === 4 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-medicore-600" />
                <span>Step 4: Confirm Consultation Details</span>
              </h2>
              <button onClick={() => setStep(3)} className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1">
                <ArrowLeft className="w-3.5 h-3.5" /> Back to Slots
              </button>
            </div>

            {/* Selected Summary Card */}
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
              <div>
                <span className="text-slate-400 block uppercase">Doctor</span>
                <span className="font-bold text-slate-900 text-sm">{selectedDoctor?.full_name}</span>
                <span className="text-slate-500 block">{selectedDoctor?.specialization}</span>
              </div>
              <div>
                <span className="text-slate-400 block uppercase">Date & Time</span>
                <span className="font-bold text-slate-900 text-sm">{selectedDate}</span>
                <span className="text-slate-600 block">{selectedSlot?.start_time.substring(0, 5)} - {selectedSlot?.end_time.substring(0, 5)}</span>
              </div>
              <div>
                <span className="text-slate-400 block uppercase">Consultation Fee</span>
                <span className="font-bold text-emerald-600 text-sm">${selectedDoctor?.consultation_fee}</span>
                <span className="text-slate-400 block">Payable at check-in or covered by insurance</span>
              </div>
            </div>

            {/* Unauthenticated User Contact Form */}
            {!isAuthenticated && (
              <div className="border border-slate-200 rounded-xl p-5 space-y-4 bg-white">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <User className="w-4 h-4 text-medicore-600" />
                  <span>Patient Contact Information</span>
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Full Legal Name *</label>
                    <input
                      type="text"
                      placeholder="e.g. Sarah Jenkins"
                      value={guestName}
                      onChange={(e) => setGuestName(e.target.value)}
                      className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm outline-none focus:border-medicore-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address *</label>
                    <input
                      type="email"
                      placeholder="e.g. sarah@example.com"
                      value={guestEmail}
                      onChange={(e) => setGuestEmail(e.target.value)}
                      className="w-full px-3.5 py-2 rounded-lg border border-slate-300 text-sm outline-none focus:border-medicore-500"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Consultation Options */}
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide mb-2">Appointment Type</label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 text-sm text-slate-800 cursor-pointer">
                    <input
                      type="radio"
                      name="appType"
                      checked={appointmentType === "IN_PERSON"}
                      onChange={() => setAppointmentType("IN_PERSON")}
                      className="text-medicore-600 focus:ring-medicore-500"
                    />
                    <span>In-Person Hospital Visit (Room {selectedDoctor?.room_number || "OPD"})</span>
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-800 cursor-pointer">
                    <input
                      type="radio"
                      name="appType"
                      checked={appointmentType === "TELECONSULTATION"}
                      onChange={() => setAppointmentType("TELECONSULTATION")}
                      className="text-medicore-600 focus:ring-medicore-500"
                    />
                    <span>Virtual Teleconsultation</span>
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1">Reason for Visit *</label>
                <input
                  type="text"
                  placeholder="e.g., Annual cardiology exam, persistent headache, medication review"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm outline-none focus:border-medicore-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1">Additional Clinical Notes (Optional)</label>
                <textarea
                  rows={3}
                  placeholder="Any symptoms, current medications, or notes for the clinical team..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm outline-none focus:border-medicore-500"
                ></textarea>
              </div>
            </div>

            <div className="pt-4 flex justify-end">
              <button
                disabled={isSubmitting}
                onClick={handleBook}
                className="bg-medicore-600 hover:bg-medicore-700 disabled:opacity-50 text-white font-bold px-8 py-3 rounded-xl text-sm transition shadow-md shadow-medicore-600/20"
              >
                {isSubmitting ? "Confirming with Hospital System..." : "Confirm & Reserve Slot"}
              </button>
            </div>
          </div>
        )}

        {/* STEP 5: SUCCESS CONFIRMATION */}
        {step === 5 && confirmedAppointment && (
          <div className="bg-white rounded-2xl border border-emerald-200 p-8 shadow-sm space-y-6 text-center max-w-xl mx-auto">
            <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-10 h-10" />
            </div>

            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-600">Booking Confirmed by Backend</span>
              <h2 className="text-2xl font-extrabold text-slate-900 mt-1">Appointment Confirmed!</h2>
              <p className="text-sm text-slate-500 mt-2">
                Your consultation has been officially recorded in the MediCore hospital database.
              </p>
            </div>

            <div className="bg-slate-50 p-5 rounded-xl border border-slate-200 text-left space-y-3 text-xs">
              <div className="flex justify-between pb-2 border-b border-slate-200">
                <span className="text-slate-500">Appointment Ref</span>
                <span className="font-bold text-slate-900">{confirmedAppointment.appointment_number}</span>
              </div>
              <div className="flex justify-between pb-2 border-b border-slate-200">
                <span className="text-slate-500">Physician</span>
                <span className="font-bold text-slate-900">{selectedDoctor?.full_name}</span>
              </div>
              <div className="flex justify-between pb-2 border-b border-slate-200">
                <span className="text-slate-500">Scheduled Time</span>
                <span className="font-bold text-slate-900">{confirmedAppointment.date} at {confirmedAppointment.start_time.substring(0, 5)}</span>
              </div>
              <div className="flex justify-between pb-2 border-b border-slate-200">
                <span className="text-slate-500">Type</span>
                <span className="font-semibold text-medicore-600">{confirmedAppointment.type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Status</span>
                <span className="font-bold text-emerald-600">{confirmedAppointment.status}</span>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <button
                onClick={() => router.push("/patient/dashboard")}
                className="flex-1 bg-medicore-600 hover:bg-medicore-700 text-white font-medium py-3 rounded-xl text-sm transition"
              >
                Go to Patient Portal
              </button>
              <button
                onClick={() => {
                  setStep(1);
                  setSelectedSlot(null);
                  setConfirmedAppointment(null);
                }}
                className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-800 font-medium py-3 rounded-xl text-sm transition"
              >
                Book Another Slot
              </button>
            </div>
          </div>
        )}
      </main>

      <PublicFooter />
    </div>
  );
}

export default function AppointmentsPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-medicore-600"></div>
      </div>
    }>
      <AppointmentsContent />
    </Suspense>
  );
}
