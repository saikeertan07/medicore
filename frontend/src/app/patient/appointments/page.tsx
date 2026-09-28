"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { PatientLayout } from "@/components/layout/patient-layout";
import { api } from "@/lib/api";
import { Appointment } from "@/types";
import { Calendar, Clock, Stethoscope, AlertCircle, X, CheckCircle2, RotateCcw } from "lucide-react";

export default function PatientAppointmentsPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [cancelAppId, setCancelAppId] = useState<number | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("ALL");

  const loadAppointments = () => {
    setIsLoading(true);
    api.get<Appointment[]>("/appointments")
      .then(setAppointments)
      .catch(() => {})
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    loadAppointments();
  }, []);

  const handleCancel = async () => {
    if (!cancelAppId) return;
    try {
      await api.post(`/appointments/${cancelAppId}/cancel`, {
        cancellation_reason: cancelReason || "Cancelled by patient"
      });
      setActionMessage("Appointment successfully cancelled. The time slot has been released.");
      setCancelAppId(null);
      setCancelReason("");
      loadAppointments();
    } catch (err: any) {
      setActionMessage(err.message || "Failed to cancel appointment.");
    }
  };

  const filteredAppointments = appointments.filter(a => {
    if (filter === "ACTIVE") return a.status === "CONFIRMED" || a.status === "SCHEDULED";
    if (filter === "COMPLETED") return a.status === "COMPLETED";
    if (filter === "CANCELLED") return a.status === "CANCELLED";
    return true;
  });

  return (
    <PatientLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">My Appointments</h1>
            <p className="text-xs text-slate-500 mt-1">Manage scheduled consultations, view past clinical visits, and reschedule.</p>
          </div>
          <Link
            href="/appointments"
            className="bg-medicore-600 hover:bg-medicore-700 text-white font-semibold px-4 py-2.5 rounded-xl text-xs flex items-center gap-2 transition shadow-sm"
          >
            <Calendar className="w-3.5 h-3.5" />
            <span>Book New Appointment</span>
          </Link>
        </div>

        {actionMessage && (
          <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between">
            <span>{actionMessage}</span>
            <button onClick={() => setActionMessage(null)} className="text-emerald-600 font-bold"><X className="w-4 h-4" /></button>
          </div>
        )}

        {/* Filters */}
        <div className="flex gap-2">
          {["ALL", "ACTIVE", "COMPLETED", "CANCELLED"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                filter === f 
                  ? "bg-slate-900 text-white shadow-sm" 
                  : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
              }`}
            >
              {f.charAt(0) + f.slice(1).toLowerCase()} ({
                f === "ALL" ? appointments.length : appointments.filter(a => f === "ACTIVE" ? (a.status === "CONFIRMED" || a.status === "SCHEDULED") : a.status === f).length
              })
            </button>
          ))}
        </div>

        {/* Appointments List */}
        {isLoading ? (
          <div className="text-center py-12 text-xs text-slate-400">Loading appointments...</div>
        ) : filteredAppointments.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-xs text-slate-500">
            No appointments found in this category.
          </div>
        ) : (
          <div className="space-y-4">
            {filteredAppointments.map((app) => (
              <div key={app.id} className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 shadow-sm hover:shadow-md transition">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900 text-sm">{app.doctor_name}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      app.status === "CONFIRMED" ? "bg-emerald-50 text-emerald-700" :
                      app.status === "COMPLETED" ? "bg-slate-100 text-slate-700" :
                      app.status === "CANCELLED" ? "bg-rose-50 text-rose-600" : "bg-medicore-50 text-medicore-700"
                    }`}>
                      {app.status}
                    </span>
                    <span className="text-slate-300">•</span>
                    <span className="text-xs text-medicore-600 font-medium">{app.department_name}</span>
                  </div>

                  <p className="text-xs text-slate-600 font-medium">Reason: {app.reason}</p>

                  <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-1">
                    <span className="flex items-center gap-1 font-semibold text-slate-700">📅 {app.date}</span>
                    <span>🕒 {app.start_time.substring(0, 5)} - {app.end_time.substring(0, 5)}</span>
                    <span>Ref: #{app.appointment_number}</span>
                    <span>Mode: {app.type}</span>
                  </div>
                </div>

                {/* Actions */}
                {(app.status === "CONFIRMED" || app.status === "SCHEDULED") && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setCancelAppId(app.id)}
                      className="text-rose-600 hover:text-rose-700 hover:bg-rose-50 px-3 py-1.5 rounded-lg text-xs font-semibold transition border border-rose-200"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Cancellation Modal */}
        {cancelAppId && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl border border-slate-200">
              <h3 className="text-base font-bold text-slate-900">Cancel Appointment</h3>
              <p className="text-xs text-slate-500">
                Are you sure you want to cancel this consultation? The slot will be released back to the general availability pool.
              </p>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Reason for Cancellation</label>
                <input
                  type="text"
                  placeholder="e.g. Work conflict, feeling better, scheduling conflict"
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs outline-none focus:border-medicore-500"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setCancelAppId(null)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100"
                >
                  Keep Appointment
                </button>
                <button
                  onClick={handleCancel}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white transition"
                >
                  Confirm Cancellation
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </PatientLayout>
  );
}
