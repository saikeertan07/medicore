"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { PatientLayout } from "@/components/layout/patient-layout";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { Appointment, MedicalDocument, NotificationItem } from "@/types";
import { 
  Calendar, FileText, Bell, Bot, Clock, Stethoscope, 
  ArrowRight, Plus, Upload, CheckCircle2, AlertCircle, FileCheck
} from "lucide-react";

export default function PatientDashboardPage() {
  const { user } = useAuth();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [documents, setDocuments] = useState<MedicalDocument[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get<Appointment[]>("/appointments").catch(() => []),
      api.get<MedicalDocument[]>("/documents").catch(() => []),
      api.get<NotificationItem[]>("/notifications").catch(() => [])
    ]).then(([apps, docs, notifs]) => {
      setAppointments(apps);
      setDocuments(docs);
      setNotifications(notifs);
    }).finally(() => setIsLoading(false));
  }, []);

  const upcomingAppointment = appointments.find(
    a => a.status === "CONFIRMED" || a.status === "SCHEDULED"
  );

  const pastAppointments = appointments.filter(
    a => a.id !== upcomingAppointment?.id
  );

  return (
    <PatientLayout>
      <div className="space-y-8">
        
        {/* Welcome Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <div>
            <span className="text-xs font-bold text-medicore-600 uppercase tracking-wider">Patient Portal</span>
            <h1 className="text-2xl font-extrabold text-slate-900 mt-0.5">Welcome back, {user?.full_name}</h1>
            <p className="text-xs text-slate-500 mt-1">Review your scheduled clinical visits, lab reports, and doctor communications.</p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/appointments"
              className="bg-medicore-600 hover:bg-medicore-700 text-white font-semibold px-4 py-2.5 rounded-xl text-xs flex items-center gap-2 transition shadow-sm"
            >
              <Calendar className="w-3.5 h-3.5" />
              <span>Book Appointment</span>
            </Link>
            <Link
              href="/patient/ai"
              className="bg-slate-900 hover:bg-slate-800 text-white font-semibold px-4 py-2.5 rounded-xl text-xs flex items-center gap-2 transition"
            >
              <Bot className="w-3.5 h-3.5 text-medicore-400" />
              <span>Ask AI</span>
            </Link>
          </div>
        </div>

        {/* QUICK ACTIONS ROW */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Link
            href="/appointments"
            className="p-4 rounded-2xl bg-white border border-slate-200 hover:border-medicore-400 hover:shadow-md transition flex flex-col items-center text-center group"
          >
            <div className="w-11 h-11 rounded-xl bg-medicore-50 text-medicore-600 flex items-center justify-center mb-3 group-hover:scale-110 transition">
              <Calendar className="w-5 h-5" />
            </div>
            <span className="text-xs font-bold text-slate-900">Book Appointment</span>
            <span className="text-[11px] text-slate-400 mt-0.5">Choose Doctor & Slot</span>
          </Link>

          <Link
            href="/patient/documents"
            className="p-4 rounded-2xl bg-white border border-slate-200 hover:border-medicore-400 hover:shadow-md transition flex flex-col items-center text-center group"
          >
            <div className="w-11 h-11 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-3 group-hover:scale-110 transition">
              <Upload className="w-5 h-5" />
            </div>
            <span className="text-xs font-bold text-slate-900">Upload Document</span>
            <span className="text-[11px] text-slate-400 mt-0.5">Labs, ECGs, Scans</span>
          </Link>

          <Link
            href="/patient/reports"
            className="p-4 rounded-2xl bg-white border border-slate-200 hover:border-medicore-400 hover:shadow-md transition flex flex-col items-center text-center group"
          >
            <div className="w-11 h-11 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3 group-hover:scale-110 transition">
              <FileCheck className="w-5 h-5" />
            </div>
            <span className="text-xs font-bold text-slate-900">View Reports</span>
            <span className="text-[11px] text-slate-400 mt-0.5">Diagnostic Results</span>
          </Link>

          <Link
            href="/patient/ai"
            className="p-4 rounded-2xl bg-white border border-slate-200 hover:border-medicore-400 hover:shadow-md transition flex flex-col items-center text-center group"
          >
            <div className="w-11 h-11 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center mb-3 group-hover:scale-110 transition">
              <Bot className="w-5 h-5" />
            </div>
            <span className="text-xs font-bold text-slate-900">Ask MediCore AI</span>
            <span className="text-[11px] text-slate-400 mt-0.5">Instant Assistance</span>
          </Link>
        </div>

        {/* UPCOMING APPOINTMENT BANNER */}
        {upcomingAppointment ? (
          <div className="bg-gradient-to-r from-medicore-600 to-medicore-700 text-white rounded-2xl p-6 shadow-md shadow-medicore-700/10">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
              <div>
                <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/20 text-white text-[11px] font-bold tracking-wide uppercase mb-2">
                  <Clock className="w-3 h-3" /> Upcoming Consultation
                </div>
                <h3 className="text-xl font-bold">{upcomingAppointment.doctor_name}</h3>
                <p className="text-xs text-medicore-100">{upcomingAppointment.doctor_specialization} • {upcomingAppointment.department_name}</p>
                <div className="mt-3 flex items-center gap-4 text-xs font-semibold">
                  <span>📅 {upcomingAppointment.date}</span>
                  <span>🕒 {upcomingAppointment.start_time.substring(0, 5)} - {upcomingAppointment.end_time.substring(0, 5)}</span>
                  <span>🏥 {upcomingAppointment.type}</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Link
                  href="/patient/appointments"
                  className="bg-white text-medicore-800 hover:bg-medicore-50 font-bold px-4 py-2.5 rounded-xl text-xs transition shadow-sm"
                >
                  Manage Booking
                </Link>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 flex items-center justify-between">
            <div>
              <h3 className="font-bold text-slate-900 text-sm">No Upcoming Appointments</h3>
              <p className="text-xs text-slate-400 mt-0.5">You have no scheduled clinical visits. Schedule an annual checkup or specialist review.</p>
            </div>
            <Link
              href="/appointments"
              className="bg-medicore-50 text-medicore-700 font-semibold px-4 py-2 rounded-xl text-xs hover:bg-medicore-100 transition border border-medicore-200"
            >
              Book Now
            </Link>
          </div>
        )}

        {/* TWO-COLUMN GRID: RECENT DOCUMENTS & APPOINTMENT HISTORY */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* Recent Medical Documents */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <FileText className="w-4 h-4 text-medicore-600" />
                <span>Recent Medical Documents</span>
              </h3>
              <Link href="/patient/documents" className="text-xs font-semibold text-medicore-600 hover:underline">
                View All
              </Link>
            </div>

            {documents.length === 0 ? (
              <p className="text-xs text-slate-400 py-6 text-center">No documents uploaded yet.</p>
            ) : (
              <div className="space-y-3">
                {documents.slice(0, 4).map((doc) => (
                  <div key={doc.id} className="p-3.5 rounded-xl border border-slate-100 bg-slate-50/60 flex items-start justify-between gap-3">
                    <div>
                      <h4 className="font-semibold text-slate-900 text-xs">{doc.file_name}</h4>
                      <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-1">{doc.summary || "Processing clinical summary..."}</p>
                      <span className="text-[10px] text-slate-400 mt-1 block">{(doc.file_size / 1024).toFixed(0)} KB • {doc.tags || "Clinical"}</span>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-700 shrink-0">
                      {doc.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Past Consultations */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <Calendar className="w-4 h-4 text-medicore-600" />
                <span>Appointment History</span>
              </h3>
              <Link href="/patient/appointments" className="text-xs font-semibold text-medicore-600 hover:underline">
                Full History
              </Link>
            </div>

            {pastAppointments.length === 0 ? (
              <p className="text-xs text-slate-400 py-6 text-center">No past appointments on record.</p>
            ) : (
              <div className="space-y-3">
                {pastAppointments.slice(0, 4).map((app) => (
                  <div key={app.id} className="p-3.5 rounded-xl border border-slate-100 bg-slate-50/60 flex items-start justify-between gap-3">
                    <div>
                      <h4 className="font-semibold text-slate-900 text-xs">{app.doctor_name}</h4>
                      <p className="text-[11px] text-slate-500 mt-0.5">{app.reason}</p>
                      <span className="text-[10px] text-slate-400 mt-1 block">{app.date} at {app.start_time.substring(0, 5)}</span>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold shrink-0 ${
                      app.status === "COMPLETED" ? "bg-slate-100 text-slate-700" : (app.status === "CANCELLED" ? "bg-rose-50 text-rose-600" : "bg-medicore-50 text-medicore-700")
                    }`}>
                      {app.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>

      </div>
    </PatientLayout>
  );
}
