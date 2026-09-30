"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { NurseLayout } from "@/components/layout/nurse-layout";
import { api } from "@/lib/api";
import { Appointment, Encounter } from "@/types";
import { 
  HeartPulse, Activity, CheckCircle2, AlertCircle, Clock, 
  Stethoscope, User, Search, Play, Check, X, Thermometer
} from "lucide-react";

export default function NurseDashboardPage() {
  const router = useRouter();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [metrics, setMetrics] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Status Action Modal (Intake Vitals)
  const [selectedAppt, setSelectedAppt] = useState<Appointment | null>(null);
  const [vitalsNote, setVitalsNote] = useState("");
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);

  const openNurseWorkspace = async (appt: Appointment) => {
    try {
      const res = await api.get<Encounter[]>(`/patients/${appt.patient_id}/encounters`);
      let target = res.find(e => e.appointment_id === appt.id);
      if (!target) {
        target = await api.post<Encounter>("/encounters", {
          patient_id: appt.patient_id,
          appointment_id: appt.id,
          attending_doctor_id: appt.doctor_id,
          department_id: appt.department_id,
          encounter_type: "OUTPATIENT"
        });
      }
      router.push(`/nurse/encounters/${target.id}`);
    } catch (err: any) {
      alert(err.message || "Failed to open nurse clinical workspace.");
    }
  };

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [todayAppts, dashboardData] = await Promise.all([
        api.get<Appointment[]>("/appointments/today"),
        api.get<any>("/analytics/dashboard")
      ]);
      setAppointments(todayAppts);
      setMetrics(dashboardData?.nurse || null);
    } catch (err: any) {
      console.error("Failed to load nurse station telemetry:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleUpdateStatus = async (apptId: number, targetStatus: string, notes?: string) => {
    setIsUpdatingStatus(true);
    setFeedback(null);
    try {
      const updated = await api.post<Appointment>(`/appointments/${apptId}/status`, {
        status: targetStatus,
        notes: notes || undefined
      });
      setAppointments((prev) => prev.map((a) => (a.id === apptId ? updated : a)));
      setSelectedAppt(null);
      setVitalsNote("");
      setFeedback({
        type: "success",
        message: `Appointment ${updated.appointment_number} transitioned to ${targetStatus.replace("_", " ")}.`
      });
      // Refresh metrics
      api.get<any>("/analytics/dashboard").then((d) => setMetrics(d?.nurse || null)).catch(() => {});
    } catch (err: any) {
      setFeedback({ type: "error", message: err.message || "Failed to update appointment status." });
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const waitingQueue = appointments.filter((a) => a.status === "CHECKED_IN");
  const inProgressQueue = appointments.filter((a) => a.status === "IN_PROGRESS");
  const completedQueue = appointments.filter((a) => a.status === "COMPLETED");

  return (
    <NurseLayout>
      <div className="space-y-8">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-3xl border border-slate-200 shadow-sm">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-teal-600">
              <HeartPulse className="w-4 h-4" />
              <span>Clinical Nurse Station</span>
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 mt-1">Patient Triage & Intake Queue</h1>
            <p className="text-xs text-slate-500 mt-0.5">Real-time arrival queue for vitals assessment, triage sorting, and active clinic room dispatch.</p>
          </div>

          <div className="flex items-center gap-2 text-xs font-semibold px-3.5 py-1.5 rounded-full bg-teal-50 text-teal-700 border border-teal-200">
            <span className="w-2 h-2 rounded-full bg-teal-500 animate-pulse"></span>
            Station Active
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

        {/* Operational Metrics */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-2xl border border-amber-200 shadow-xs bg-amber-50/30">
            <span className="text-[11px] font-bold text-amber-700 uppercase tracking-wider">Awaiting Triage</span>
            <div className="mt-2 text-2xl font-extrabold text-amber-600">
              {metrics?.triage_waiting ?? waitingQueue.length}
            </div>
            <p className="mt-1 text-[10px] text-amber-800 font-medium">Checked in at front desk</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-teal-200 shadow-xs bg-teal-50/30">
            <span className="text-[11px] font-bold text-teal-700 uppercase tracking-wider">In Consultation</span>
            <div className="mt-2 text-2xl font-extrabold text-teal-600">
              {metrics?.in_consultation ?? inProgressQueue.length}
            </div>
            <p className="mt-1 text-[10px] text-teal-800 font-medium">Under active clinical care</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-emerald-200 shadow-xs bg-emerald-50/30">
            <span className="text-[11px] font-bold text-emerald-700 uppercase tracking-wider">Completed Consultations</span>
            <div className="mt-2 text-2xl font-extrabold text-emerald-600">
              {metrics?.today_completed ?? completedQueue.length}
            </div>
            <p className="mt-1 text-[10px] text-emerald-800 font-medium">Discharged today</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Today's Total Schedule</span>
            <div className="mt-2 text-2xl font-extrabold text-slate-800">
              {metrics?.today_total ?? appointments.length}
            </div>
            <p className="mt-1 text-[10px] text-slate-500 font-medium">All department bookings</p>
          </div>
        </div>

        {/* Primary Section: Waiting for Triage */}
        <div className="bg-white rounded-3xl border border-amber-200/80 shadow-sm overflow-hidden">
          <div className="p-5 border-b border-amber-100 flex items-center justify-between bg-amber-50/40">
            <div>
              <h2 className="text-base font-extrabold text-slate-900 flex items-center gap-2">
                <Clock className="w-4 h-4 text-amber-600" />
                <span>Waiting Room Queue (Checked-In Patients)</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">Patients physically present in hospital reception awaiting clinical call-in.</p>
            </div>
            <span className="px-3 py-1 rounded-full bg-amber-100 text-amber-800 text-xs font-bold">
              {waitingQueue.length} Waiting
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider border-b border-slate-100">
                <tr>
                  <th className="py-3 px-6">Arrival Time</th>
                  <th className="py-3 px-6">Patient Name</th>
                  <th className="py-3 px-6">Physician & Dept</th>
                  <th className="py-3 px-6">Reason for Visit</th>
                  <th className="py-3 px-6 text-right">Triage Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {waitingQueue.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-10 text-center text-slate-400">
                      No patients currently waiting in the arrival queue.
                    </td>
                  </tr>
                ) : (
                  waitingQueue.map((appt) => (
                    <tr key={appt.id} className="hover:bg-slate-50/80 transition">
                      <td className="py-4 px-6 font-mono font-bold text-amber-700">
                        {appt.check_in_time 
                          ? new Date(appt.check_in_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) 
                          : appt.start_time.substring(0, 5)}
                      </td>
                      <td className="py-4 px-6 font-bold text-slate-900">
                        {appt.patient_name || `Patient #${appt.patient_id}`}
                      </td>
                      <td className="py-4 px-6">
                        <div className="font-semibold text-slate-900">{appt.doctor_name}</div>
                        <div className="text-[11px] text-slate-500">{appt.department_name}</div>
                      </td>
                      <td className="py-4 px-6 text-slate-600 max-w-xs truncate">{appt.reason}</td>
                      <td className="py-4 px-6 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => openNurseWorkspace(appt)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-medicore-600 hover:bg-medicore-700 text-white font-bold transition shadow-xs cursor-pointer text-xs"
                          >
                            <Thermometer className="w-3.5 h-3.5" />
                            <span>Record Vitals & Intake</span>
                          </button>
                          <button
                            onClick={() => {
                              setSelectedAppt(appt);
                              setVitalsNote("");
                            }}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-bold transition shadow-xs cursor-pointer text-xs"
                          >
                            <Play className="w-3.5 h-3.5 fill-white" />
                            <span>Call In</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Secondary Section: Currently in Consultation */}
        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <div>
              <h2 className="text-base font-extrabold text-slate-900 flex items-center gap-2">
                <Stethoscope className="w-4 h-4 text-teal-600" />
                <span>Active Clinical Consultations</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">Patients currently in examination or procedural rooms.</p>
            </div>
            <span className="px-3 py-1 rounded-full bg-teal-100 text-teal-800 text-xs font-bold">
              {inProgressQueue.length} In Progress
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider border-b border-slate-100">
                <tr>
                  <th className="py-3 px-6">Patient</th>
                  <th className="py-3 px-6">Attending Physician</th>
                  <th className="py-3 px-6">Clinical Dept</th>
                  <th className="py-3 px-6">Status</th>
                  <th className="py-3 px-6 text-right">Discharge / Complete</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {inProgressQueue.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-10 text-center text-slate-400">
                      No consultations currently in progress.
                    </td>
                  </tr>
                ) : (
                  inProgressQueue.map((appt) => (
                    <tr key={appt.id} className="hover:bg-slate-50/80 transition">
                      <td className="py-4 px-6 font-bold text-slate-900">
                        {appt.patient_name || `Patient #${appt.patient_id}`}
                      </td>
                      <td className="py-4 px-6 font-semibold text-slate-900">{appt.doctor_name}</td>
                      <td className="py-4 px-6 text-slate-600">{appt.department_name}</td>
                      <td className="py-4 px-6">
                        <span className="px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-blue-100 text-blue-800 border border-blue-200 uppercase">
                          IN PROGRESS
                        </span>
                      </td>
                      <td className="py-4 px-6 text-right">
                        <button
                          onClick={() => handleUpdateStatus(appt.id, "COMPLETED", "Consultation concluded by nurse/doctor.")}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold transition cursor-pointer"
                        >
                          <Check className="w-3.5 h-3.5" />
                          <span>Mark Completed</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal: Intake Vitals & Start Consultation */}
        {selectedAppt && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl max-w-lg w-full p-6 space-y-5">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                <div>
                  <h3 className="text-base font-extrabold text-slate-900">Patient Intake & Vitals Assessment</h3>
                  <p className="text-xs text-slate-500">Call {selectedAppt.patient_name} to triage and initiate consultation.</p>
                </div>
                <button onClick={() => setSelectedAppt(null)} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4 text-xs">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                  <div className="font-bold text-slate-900">{selectedAppt.patient_name}</div>
                  <div className="text-slate-500">Doctor: {selectedAppt.doctor_name} ({selectedAppt.department_name})</div>
                  <div className="text-slate-500">Reason: {selectedAppt.reason}</div>
                </div>

                <div className="space-y-1.5">
                  <label className="font-bold text-slate-700">Triage Intake Notes & Vitals</label>
                  <textarea
                    rows={3}
                    value={vitalsNote}
                    onChange={(e) => setVitalsNote(e.target.value)}
                    placeholder="e.g. BP 120/80 mmHg, Pulse 72 bpm, Temp 98.6°F, SpO2 99%. Patient escorted to Room 102."
                    className="w-full px-3.5 py-2 rounded-xl border border-slate-200 focus:border-teal-500 focus:outline-hidden text-slate-900"
                  />
                </div>

                <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setSelectedAppt(null)}
                    className="px-4 py-2 rounded-xl border border-slate-200 text-slate-600 font-bold hover:bg-slate-50 cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={isUpdatingStatus}
                    onClick={() => handleUpdateStatus(selectedAppt.id, "IN_PROGRESS", vitalsNote)}
                    className="px-5 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-bold transition shadow-sm cursor-pointer disabled:opacity-50"
                  >
                    {isUpdatingStatus ? "Updating..." : "Confirm & Start Consultation"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

      </div>
    </NurseLayout>
  );
}
