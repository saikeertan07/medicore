"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { DoctorLayout } from "@/components/layout/doctor-layout";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { Appointment, MedicalDocument, Encounter } from "@/types";
import { 
  Calendar, Users, Clock, FileText, CheckCircle2, 
  ArrowRight, AlertCircle, Stethoscope, Bot
} from "lucide-react";

export default function DoctorDashboardPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [documents, setDocuments] = useState<MedicalDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const openClinicalWorkspace = async (app: Appointment) => {
    try {
      const res = await api.get<Encounter[]>(`/patients/${app.patient_id}/encounters`);
      let target = res.find(e => e.appointment_id === app.id);
      if (!target) {
        target = await api.post<Encounter>("/encounters", {
          patient_id: app.patient_id,
          appointment_id: app.id,
          attending_doctor_id: app.doctor_id,
          department_id: app.department_id,
          encounter_type: "OUTPATIENT"
        });
      }
      router.push(`/doctor/encounters/${target.id}`);
    } catch (err: any) {
      alert(err.message || "Failed to open clinical workspace.");
    }
  };

  useEffect(() => {
    Promise.all([
      api.get<Appointment[]>("/appointments").catch(() => []),
      api.get<MedicalDocument[]>("/documents").catch(() => [])
    ]).then(([apps, docs]) => {
      setAppointments(apps);
      setDocuments(docs);
    }).finally(() => setIsLoading(false));
  }, []);

  const todayStr = new Date().toISOString().split("T")[0];
  const todayAppointments = appointments.filter(a => a.date === todayStr);
  const completedCount = appointments.filter(a => a.status === "COMPLETED").length;
  const upcomingCount = appointments.filter(a => a.status === "CONFIRMED" || a.status === "SCHEDULED").length;

  return (
    <DoctorLayout>
      <div className="space-y-8">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <div>
            <span className="text-xs font-bold text-medicore-600 uppercase tracking-wider">Clinical Station</span>
            <h1 className="text-2xl font-extrabold text-slate-900 mt-0.5">{user?.full_name}</h1>
            <p className="text-xs text-slate-500 mt-1">Review your patient consultations, clinical lab feeds, and AI chart assistance.</p>
          </div>
          <Link
            href="/doctor/ai"
            className="bg-medicore-600 hover:bg-medicore-700 text-white font-semibold px-4 py-2.5 rounded-xl text-xs flex items-center gap-2 transition shadow-sm"
          >
            <Bot className="w-4 h-4 text-white" />
            <span>Open Clinical AI Assistant</span>
          </Link>
        </div>

        {/* METRICS ROW */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-xs font-medium text-slate-500">Today's Schedule</span>
            <div className="text-3xl font-extrabold text-slate-900 mt-1">{todayAppointments.length}</div>
            <span className="text-[11px] text-medicore-600 font-semibold mt-1 block">Scheduled Consultations</span>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-xs font-medium text-slate-500">Upcoming Consultations</span>
            <div className="text-3xl font-extrabold text-slate-900 mt-1">{upcomingCount}</div>
            <span className="text-[11px] text-emerald-600 font-semibold mt-1 block">Active Bookings</span>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-xs font-medium text-slate-500">Completed Sessions</span>
            <div className="text-3xl font-extrabold text-slate-900 mt-1">{completedCount}</div>
            <span className="text-[11px] text-slate-400 font-medium mt-1 block">Historical Encounters</span>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-xs font-medium text-slate-500">Patient Documents</span>
            <div className="text-3xl font-extrabold text-slate-900 mt-1">{documents.length}</div>
            <span className="text-[11px] text-indigo-600 font-semibold mt-1 block">Available Labs & Imaging</span>
          </div>
        </div>

        {/* TODAY'S APPOINTMENTS SCHEDULE */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
              <Calendar className="w-5 h-5 text-medicore-600" />
              <span>Today's Consultations ({todayAppointments.length})</span>
            </h3>
            <Link href="/doctor/appointments" className="text-xs font-semibold text-medicore-600 hover:underline">
              View All Schedule
            </Link>
          </div>

          {todayAppointments.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400">
              No appointments scheduled for today.
            </div>
          ) : (
            <div className="space-y-3">
              {todayAppointments.map((app) => (
                <div key={app.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-bold text-slate-900 text-sm">{app.patient_name}</h4>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase tracking-wider ${
                        app.status === "CHECKED_IN"
                          ? "bg-amber-100 text-amber-800 border border-amber-300"
                          : app.status === "IN_PROGRESS"
                          ? "bg-blue-100 text-blue-800 border border-blue-300"
                          : app.status === "COMPLETED"
                          ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                          : "bg-slate-100 text-slate-700 border border-slate-200"
                      }`}>
                        {app.status.replace("_", " ")}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600">{app.reason}</p>
                    <div className="text-[11px] text-slate-400 flex items-center gap-3 pt-1">
                      <span>🕒 {app.start_time.substring(0, 5)} - {app.end_time.substring(0, 5)}</span>
                      <span>Ref: #{app.appointment_number}</span>
                      {app.check_in_time && (
                        <span className="text-amber-700 font-semibold font-mono">
                          Arrived: {new Date(app.check_in_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {(app.status === "CHECKED_IN" || app.status === "IN_PROGRESS" || app.status === "COMPLETED") && (
                      <button
                        onClick={() => openClinicalWorkspace(app)}
                        className="bg-medicore-600 hover:bg-medicore-700 text-white text-xs font-bold px-3 py-1.5 rounded-lg shadow-sm transition flex items-center gap-1 cursor-pointer"
                      >
                        <Stethoscope className="w-3.5 h-3.5" />
                        <span>Open Clinical Workspace</span>
                      </button>
                    )}
                    {app.status === "CHECKED_IN" && (
                      <button
                        onClick={async () => {
                          try {
                            const updated = await api.post<Appointment>(`/appointments/${app.id}/status`, { status: "IN_PROGRESS" });
                            setAppointments(prev => prev.map(a => a.id === app.id ? updated : a));
                          } catch (err: any) {
                            alert(err.message || "Failed to start consultation.");
                          }
                        }}
                        className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold px-3 py-1.5 rounded-lg shadow-2xs transition cursor-pointer"
                      >
                        Start Consultation
                      </button>
                    )}
                    {app.status === "IN_PROGRESS" && (
                      <button
                        onClick={async () => {
                          try {
                            const updated = await api.post<Appointment>(`/appointments/${app.id}/status`, { status: "COMPLETED" });
                            setAppointments(prev => prev.map(a => a.id === app.id ? updated : a));
                          } catch (err: any) {
                            alert(err.message || "Failed to complete consultation.");
                          }
                        }}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold px-3 py-1.5 rounded-lg shadow-2xs transition cursor-pointer"
                      >
                        Mark Completed
                      </button>
                    )}
                    <Link
                      href={`/doctor/ai`}
                      className="bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-200 transition"
                    >
                      AI Summary
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* RECENT CLINICAL DOCUMENTS */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
              <FileText className="w-5 h-5 text-medicore-600" />
              <span>Recent Patient Lab & Imaging Documents</span>
            </h3>
            <Link href="/doctor/documents" className="text-xs font-semibold text-medicore-600 hover:underline">
              Browse Archive
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {documents.slice(0, 4).map((doc) => (
              <div key={doc.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 space-y-2">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-bold text-slate-900 text-xs">{doc.file_name}</h4>
                    <span className="text-[11px] text-slate-500">Patient: {doc.patient_name || "Assigned"}</span>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-700">
                    {doc.status}
                  </span>
                </div>
                <p className="text-xs text-slate-600 line-clamp-2">{doc.summary}</p>
              </div>
            ))}
          </div>
        </div>

      </div>
    </DoctorLayout>
  );
}
