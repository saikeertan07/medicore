"use client";

import React, { useState, useEffect } from "react";
import { ReceptionLayout } from "@/components/layout/reception-layout";
import { api } from "@/lib/api";
import { Appointment, Patient, Department, Doctor } from "@/types";
import { 
  Users, Calendar, Clock, CheckCircle2, AlertCircle, 
  UserPlus, Search, Phone, Mail, ChevronRight, Activity, ArrowRight, X
} from "lucide-react";

export default function ReceptionDashboardPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [metrics, setMetrics] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Filters & Search
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Quick Patient Create Modal
  const [showPatientModal, setShowPatientModal] = useState(false);
  const [newPatient, setNewPatient] = useState({
    full_name: "",
    email: "",
    phone: "",
    date_of_birth: "",
    gender: "Other",
    blood_group: "O+",
    emergency_contact: "",
    address: ""
  });
  const [isSubmittingPatient, setIsSubmittingPatient] = useState(false);

  // Load Today's Data
  const loadData = async () => {
    setIsLoading(true);
    try {
      const [todayAppts, dashboardData, deptsData, docsData] = await Promise.all([
        api.get<Appointment[]>("/appointments/today"),
        api.get<any>("/analytics/dashboard"),
        api.get<Department[]>("/departments"),
        api.get<Doctor[]>("/doctors")
      ]);
      setAppointments(todayAppts);
      setMetrics(dashboardData?.reception || null);
      setDepartments(deptsData);
      setDoctors(docsData);
    } catch (err: any) {
      console.error("Failed to load reception data:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Quick Check-In Action
  const handleCheckIn = async (appointmentId: number) => {
    try {
      const updated = await api.post<Appointment>(`/appointments/${appointmentId}/check-in`, {
        notes: "Patient arrived at front desk."
      });
      setAppointments((prev) => prev.map((a) => (a.id === appointmentId ? updated : a)));
      setFeedback({ type: "success", message: `Patient checked in successfully at ${new Date().toLocaleTimeString()}!` });
      // Refresh metrics
      api.get<any>("/analytics/dashboard").then((d) => setMetrics(d?.reception || null)).catch(() => {});
    } catch (err: any) {
      setFeedback({ type: "error", message: err.message || "Failed to check in patient." });
    }
  };

  // Register New Walk-In Patient
  const handleRegisterPatient = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingPatient(true);
    setFeedback(null);
    try {
      const created = await api.post<Patient>("/patients", {
        ...newPatient,
        email: newPatient.email.trim() || undefined,
        phone: newPatient.phone.trim() || undefined
      });
      setShowPatientModal(false);
      setFeedback({
        type: "success",
        message: `Registered patient ${created.full_name} with ID: ${created.patient_number}`
      });
      setNewPatient({
        full_name: "",
        email: "",
        phone: "",
        date_of_birth: "",
        gender: "Other",
        blood_group: "O+",
        emergency_contact: "",
        address: ""
      });
      // Refresh metrics
      api.get<any>("/analytics/dashboard").then((d) => setMetrics(d?.reception || null)).catch(() => {});
    } catch (err: any) {
      setFeedback({ type: "error", message: err.message || "Failed to register patient." });
    } finally {
      setIsSubmittingPatient(false);
    }
  };

  // Filtered Appointments
  const filteredAppointments = appointments.filter((appt) => {
    const matchesStatus = statusFilter === "ALL" || appt.status === statusFilter;
    const matchesSearch = !searchQuery || 
      (appt.patient_name && appt.patient_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (appt.appointment_number && appt.appointment_number.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (appt.doctor_name && appt.doctor_name.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesStatus && matchesSearch;
  });

  return (
    <ReceptionLayout>
      <div className="space-y-8">
        
        {/* Header with Quick Actions */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-3xl border border-slate-200 shadow-sm">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-600">
              <Activity className="w-4 h-4" />
              <span>Front Desk Operations</span>
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 mt-1">Today's Reception & Check-In Desk</h1>
            <p className="text-xs text-slate-500 mt-0.5">Streamlined patient arrival, instant check-in telemetry, and walk-in registrations.</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowPatientModal(true)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-amber-500 text-white text-xs font-bold hover:bg-amber-600 shadow-sm transition cursor-pointer"
            >
              <UserPlus className="w-4 h-4" />
              <span>Register Walk-in Patient</span>
            </button>
          </div>
        </div>

        {/* Feedback Alert */}
        {feedback && (
          <div className={`p-4 rounded-2xl border flex items-center justify-between text-xs font-semibold ${
            feedback.type === "success" 
              ? "bg-emerald-50 border-emerald-200 text-emerald-800" 
              : "bg-rose-50 border-rose-200 text-rose-800"
          }`}>
            <div className="flex items-center gap-2">
              {feedback.type === "success" ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <AlertCircle className="w-4 h-4 text-rose-600" />}
              <span>{feedback.message}</span>
            </div>
            <button onClick={() => setFeedback(null)} className="text-slate-400 hover:text-slate-600">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Telemetry Metric Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Today's Schedule</span>
            <div className="mt-2 text-2xl font-extrabold text-slate-900">{metrics?.today_total ?? appointments.length}</div>
            <p className="mt-1 text-[10px] text-slate-500 font-medium">Total consultations today</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-amber-200 shadow-xs bg-amber-50/20">
            <span className="text-[11px] font-bold text-amber-600 uppercase tracking-wider">Checked In Waiting</span>
            <div className="mt-2 text-2xl font-extrabold text-amber-600">
              {metrics?.today_checked_in ?? appointments.filter((a) => a.status === "CHECKED_IN").length}
            </div>
            <p className="mt-1 text-[10px] text-amber-700 font-medium">Arrived at waiting room</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-blue-200 shadow-xs bg-blue-50/20">
            <span className="text-[11px] font-bold text-blue-600 uppercase tracking-wider">In Consultation</span>
            <div className="mt-2 text-2xl font-extrabold text-blue-600">
              {metrics?.today_in_progress ?? appointments.filter((a) => a.status === "IN_PROGRESS").length}
            </div>
            <p className="mt-1 text-[10px] text-blue-700 font-medium">With physician/nurse</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Pending Arrival</span>
            <div className="mt-2 text-2xl font-extrabold text-slate-700">
              {metrics?.today_pending_checkin ?? appointments.filter((a) => a.status === "CONFIRMED").length}
            </div>
            <p className="mt-1 text-[10px] text-slate-500 font-medium">Expected to check in</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-emerald-200 shadow-xs bg-emerald-50/20">
            <span className="text-[11px] font-bold text-emerald-600 uppercase tracking-wider">Completed</span>
            <div className="mt-2 text-2xl font-extrabold text-emerald-600">
              {metrics?.today_completed ?? appointments.filter((a) => a.status === "COMPLETED").length}
            </div>
            <p className="mt-1 text-[10px] text-emerald-700 font-medium">Finished consultations</p>
          </div>
        </div>

        {/* Live Today's Queue Section */}
        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
          {/* Controls Bar */}
          <div className="p-5 border-b border-slate-100 flex flex-col md:flex-row justify-between items-center gap-4 bg-slate-50/50">
            {/* Status Filter Tabs */}
            <div className="flex flex-wrap items-center gap-1.5 p-1 bg-slate-200/60 rounded-xl">
              {[
                { label: "All Today", value: "ALL" },
                { label: "Pending Check-In", value: "CONFIRMED" },
                { label: "Checked In", value: "CHECKED_IN" },
                { label: "In Progress", value: "IN_PROGRESS" },
                { label: "Completed", value: "COMPLETED" },
              ].map((tab) => (
                <button
                  key={tab.value}
                  onClick={() => setStatusFilter(tab.value)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition cursor-pointer ${
                    statusFilter === tab.value
                      ? "bg-white text-slate-900 shadow-2xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Search Input */}
            <div className="relative w-full md:w-72">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search patient, doc, or ID..."
                className="w-full pl-9 pr-4 py-1.5 rounded-xl border border-slate-200 text-xs bg-white text-slate-900 placeholder:text-slate-400 focus:outline-hidden focus:border-amber-500"
              />
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider border-b border-slate-100">
                <tr>
                  <th className="py-3.5 px-6">Appointment ID</th>
                  <th className="py-3.5 px-6">Patient</th>
                  <th className="py-3.5 px-6">Physician & Dept</th>
                  <th className="py-3.5 px-6">Scheduled Time</th>
                  <th className="py-3.5 px-6">Status & Telemetry</th>
                  <th className="py-3.5 px-6 text-right">Desk Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-400">Loading today's hospital queue...</td>
                  </tr>
                ) : filteredAppointments.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-400">No appointments matching current criteria.</td>
                  </tr>
                ) : (
                  filteredAppointments.map((appt) => (
                    <tr key={appt.id} className="hover:bg-slate-50/80 transition">
                      <td className="py-4 px-6 font-mono font-semibold text-slate-900">{appt.appointment_number}</td>
                      <td className="py-4 px-6">
                        <div className="font-bold text-slate-900">{appt.patient_name || "Walk-In Patient"}</div>
                        <div className="text-[11px] text-slate-500">ID #{appt.patient_id}</div>
                      </td>
                      <td className="py-4 px-6">
                        <div className="font-semibold text-slate-900">{appt.doctor_name || "Doctor"}</div>
                        <div className="text-[11px] text-slate-500">{appt.department_name || "Clinical Dept"}</div>
                      </td>
                      <td className="py-4 px-6 font-mono text-slate-700">
                        {appt.start_time.substring(0, 5)} - {appt.end_time.substring(0, 5)}
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-2">
                          <span className={`px-2.5 py-1 rounded-full text-[10px] font-extrabold uppercase tracking-wider ${
                            appt.status === "CHECKED_IN"
                              ? "bg-amber-100 text-amber-800 border border-amber-300"
                              : appt.status === "IN_PROGRESS"
                              ? "bg-blue-100 text-blue-800 border border-blue-300"
                              : appt.status === "COMPLETED"
                              ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                              : appt.status === "CANCELLED"
                              ? "bg-rose-100 text-rose-800 border border-rose-300"
                              : "bg-slate-100 text-slate-800 border border-slate-300"
                          }`}>
                            {appt.status.replace("_", " ")}
                          </span>
                          {appt.check_in_time && (
                            <span className="text-[10px] text-slate-400 font-mono">
                              Arr: {new Date(appt.check_in_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-4 px-6 text-right">
                        {appt.status === "CONFIRMED" || appt.status === "SCHEDULED" ? (
                          <button
                            onClick={() => handleCheckIn(appt.id)}
                            className="px-3.5 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold transition shadow-xs cursor-pointer"
                          >
                            Check In Patient
                          </button>
                        ) : appt.status === "CHECKED_IN" ? (
                          <span className="text-xs font-bold text-amber-600 flex items-center justify-end gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Waiting Room
                          </span>
                        ) : (
                          <span className="text-slate-400 text-xs">—</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal: Register Walk-in Patient */}
        {showPatientModal && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl max-w-xl w-full p-6 space-y-5">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                <div>
                  <h3 className="text-lg font-extrabold text-slate-900">Walk-In Patient Quick Registration</h3>
                  <p className="text-xs text-slate-500">Creates an official hospital patient record with an auto-generated PAT ID.</p>
                </div>
                <button onClick={() => setShowPatientModal(false)} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleRegisterPatient} className="space-y-4 text-xs">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5 sm:col-span-2">
                    <label className="font-bold text-slate-700">Full Name *</label>
                    <input
                      type="text"
                      required
                      value={newPatient.full_name}
                      onChange={(e) => setNewPatient({ ...newPatient, full_name: e.target.value })}
                      placeholder="e.g. Eleanor Rigby"
                      className="w-full px-3.5 py-2 rounded-xl border border-slate-200 focus:border-amber-500 focus:outline-hidden"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="font-bold text-slate-700">Contact Phone</label>
                    <input
                      type="text"
                      value={newPatient.phone}
                      onChange={(e) => setNewPatient({ ...newPatient, phone: e.target.value })}
                      placeholder="+1-555-0199"
                      className="w-full px-3.5 py-2 rounded-xl border border-slate-200 focus:border-amber-500 focus:outline-hidden"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="font-bold text-slate-700">Email Address (Optional)</label>
                    <input
                      type="email"
                      value={newPatient.email}
                      onChange={(e) => setNewPatient({ ...newPatient, email: e.target.value })}
                      placeholder="patient@example.com"
                      className="w-full px-3.5 py-2 rounded-xl border border-slate-200 focus:border-amber-500 focus:outline-hidden"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="font-bold text-slate-700">Date of Birth</label>
                    <input
                      type="date"
                      value={newPatient.date_of_birth}
                      onChange={(e) => setNewPatient({ ...newPatient, date_of_birth: e.target.value })}
                      className="w-full px-3.5 py-2 rounded-xl border border-slate-200 focus:border-amber-500 focus:outline-hidden"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="font-bold text-slate-700">Blood Group</label>
                    <select
                      value={newPatient.blood_group}
                      onChange={(e) => setNewPatient({ ...newPatient, blood_group: e.target.value })}
                      className="w-full px-3.5 py-2 rounded-xl border border-slate-200 focus:border-amber-500 focus:outline-hidden"
                    >
                      {["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"].map((bg) => (
                        <option key={bg} value={bg}>{bg}</option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1.5 sm:col-span-2">
                    <label className="font-bold text-slate-700">Emergency Contact</label>
                    <input
                      type="text"
                      value={newPatient.emergency_contact}
                      onChange={(e) => setNewPatient({ ...newPatient, emergency_contact: e.target.value })}
                      placeholder="Family member / Phone"
                      className="w-full px-3.5 py-2 rounded-xl border border-slate-200 focus:border-amber-500 focus:outline-hidden"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setShowPatientModal(false)}
                    className="px-4 py-2 rounded-xl border border-slate-200 text-slate-600 font-bold hover:bg-slate-50 cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmittingPatient}
                    className="px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-bold transition shadow-sm cursor-pointer disabled:opacity-50"
                  >
                    {isSubmittingPatient ? "Registering..." : "Complete Registration"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

      </div>
    </ReceptionLayout>
  );
}
