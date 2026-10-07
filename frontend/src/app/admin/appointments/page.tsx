"use client";

import React, { useState, useEffect } from "react";
import { AdminLayout } from "@/components/layout/admin-layout";
import { api } from "@/lib/api";
import { Appointment } from "@/types";
import { Calendar, Search } from "lucide-react";

export default function AdminAppointmentsPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let url = "/appointments";
    if (statusFilter) url += `?status_filter=${statusFilter}`;
    api.get<Appointment[]>(url)
      .then(setAppointments)
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, [statusFilter]);

  const filtered = appointments.filter(a =>
    a.patient_name?.toLowerCase().includes(search.toLowerCase()) ||
    a.doctor_name?.toLowerCase().includes(search.toLowerCase()) ||
    a.appointment_number?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Master Appointment Registry</h1>
          <p className="text-xs text-slate-500 mt-1">Global hospital scheduling roster across all 15 physicians and departments.</p>
        </div>

        {/* Filter Bar */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-4">
          <div className="flex-1 flex items-center gap-3 px-3 py-1">
            <Search className="w-5 h-5 text-slate-400 shrink-0" />
            <input
              type="text"
              placeholder="Search by patient name, doctor, or reference number..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full text-xs sm:text-sm outline-none text-slate-800 placeholder-slate-400 bg-transparent"
            />
          </div>
          <div className="sm:w-48 border-t sm:border-t-0 sm:border-l border-slate-200 px-3 py-1 flex items-center">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full text-xs sm:text-sm outline-none text-slate-700 bg-transparent cursor-pointer"
            >
              <option value="">All Statuses</option>
              <option value="CONFIRMED">CONFIRMED</option>
              <option value="SCHEDULED">SCHEDULED</option>
              <option value="COMPLETED">COMPLETED</option>
              <option value="CANCELLED">CANCELLED</option>
            </select>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                  <th className="p-4">Ref Number</th>
                  <th className="p-4">Date & Time</th>
                  <th className="p-4">Patient</th>
                  <th className="p-4">Physician</th>
                  <th className="p-4">Department</th>
                  <th className="p-4">Type</th>
                  <th className="p-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50/60 transition">
                    <td className="p-4 font-mono font-bold text-slate-800">{a.appointment_number}</td>
                    <td className="p-4 text-slate-700">
                      <div>{a.date}</div>
                      <div className="text-[11px] text-slate-400">{a.start_time.substring(0, 5)} - {a.end_time.substring(0, 5)}</div>
                    </td>
                    <td className="p-4 font-bold text-slate-900">{a.patient_name}</td>
                    <td className="p-4 text-slate-800">{a.doctor_name}</td>
                    <td className="p-4 text-slate-600">{a.department_name}</td>
                    <td className="p-4 font-semibold text-medicore-600">{a.type}</td>
                    <td className="p-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        a.status === "CONFIRMED" ? "bg-emerald-50 text-emerald-700" :
                        a.status === "COMPLETED" ? "bg-slate-100 text-slate-700" :
                        a.status === "CANCELLED" ? "bg-rose-50 text-rose-700" : "bg-medicore-50 text-medicore-700"
                      }`}>
                        {a.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
