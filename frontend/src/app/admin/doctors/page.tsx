"use client";

import React, { useState, useEffect } from "react";
import { AdminLayout } from "@/components/layout/admin-layout";
import { api } from "@/lib/api";
import { Doctor } from "@/types";
import { Stethoscope, Star, Search } from "lucide-react";

export default function AdminDoctorsPage() {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get<Doctor[]>("/doctors")
      .then(setDoctors)
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  const filtered = doctors.filter(d =>
    d.full_name?.toLowerCase().includes(search.toLowerCase()) ||
    d.department_name?.toLowerCase().includes(search.toLowerCase()) ||
    d.specialization?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Hospital Medical Faculty</h1>
          <p className="text-xs text-slate-500 mt-1">Directory of all 15 active clinicians, consultation fees, ratings, and room numbers.</p>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-3">
          <Search className="w-5 h-5 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Search physicians by name, specialty, or department..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full text-xs sm:text-sm outline-none text-slate-800 placeholder-slate-400 bg-transparent"
          />
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                <th className="p-4">Physician Name</th>
                <th className="p-4">Department</th>
                <th className="p-4">Specialization</th>
                <th className="p-4">Room</th>
                <th className="p-4">Consultation Fee</th>
                <th className="p-4">Rating</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((d) => (
                <tr key={d.id} className="hover:bg-slate-50/60 transition">
                  <td className="p-4 font-bold text-slate-900">
                    <div>{d.full_name}</div>
                    <div className="text-[11px] text-slate-400 font-normal">{d.qualification}</div>
                  </td>
                  <td className="p-4 font-semibold text-medicore-600">{d.department_name}</td>
                  <td className="p-4 text-slate-700">{d.specialization}</td>
                  <td className="p-4 font-mono text-slate-600">Room {d.room_number || "OPD"}</td>
                  <td className="p-4 font-bold text-slate-900">${d.consultation_fee}</td>
                  <td className="p-4 text-amber-500 font-bold">⭐ {d.rating}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AdminLayout>
  );
}
