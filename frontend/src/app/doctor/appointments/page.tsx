"use client";

import React, { useState, useEffect } from "react";
import { DoctorLayout } from "@/components/layout/doctor-layout";
import { api } from "@/lib/api";
import { Appointment } from "@/types";
import { Calendar, Clock, CheckCircle2, X } from "lucide-react";

export default function DoctorAppointmentsPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get<Appointment[]>("/appointments")
      .then(setAppointments)
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <DoctorLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Physician Consultation Schedule</h1>
          <p className="text-xs text-slate-500 mt-1">Review all scheduled, completed, and upcoming patient encounters.</p>
        </div>

        {isLoading ? (
          <div className="text-center py-12 text-xs text-slate-400">Loading appointments...</div>
        ) : appointments.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-xs text-slate-500">
            No consultations assigned to your calendar at this time.
          </div>
        ) : (
          <div className="space-y-3">
            {appointments.map((app) => (
              <div key={app.id} className="bg-white rounded-2xl border border-slate-200 p-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 shadow-sm">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900 text-sm">{app.patient_name}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      app.status === "CONFIRMED" ? "bg-emerald-50 text-emerald-700" :
                      app.status === "COMPLETED" ? "bg-slate-100 text-slate-700" :
                      app.status === "CANCELLED" ? "bg-rose-50 text-rose-600" : "bg-medicore-50 text-medicore-700"
                    }`}>
                      {app.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 font-medium">Chief Complaint: {app.reason}</p>
                  <div className="flex items-center gap-4 text-xs text-slate-400 pt-1">
                    <span>📅 {app.date}</span>
                    <span>🕒 {app.start_time.substring(0, 5)} - {app.end_time.substring(0, 5)}</span>
                    <span>Ref: #{app.appointment_number}</span>
                    <span>{app.type}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </DoctorLayout>
  );
}
