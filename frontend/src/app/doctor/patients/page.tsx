"use client";

import React, { useState, useEffect } from "react";
import { DoctorLayout } from "@/components/layout/doctor-layout";
import { api } from "@/lib/api";
import { Search, User, ShieldCheck } from "lucide-react";

export default function DoctorPatientsPage() {
  const [patients, setPatients] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get<any[]>("/patients")
      .then(setPatients)
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  const filteredPatients = patients.filter(p =>
    p.full_name?.toLowerCase().includes(search.toLowerCase()) ||
    p.email?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <DoctorLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Assigned Patients</h1>
          <p className="text-xs text-slate-500 mt-1">Authorized clinical access to patients under your active or historical care.</p>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-3 px-3 py-1">
            <Search className="w-5 h-5 text-slate-400 shrink-0" />
            <input
              type="text"
              placeholder="Search patients by name or email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full text-xs sm:text-sm outline-none text-slate-800 placeholder-slate-400 bg-transparent"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="text-center py-12 text-xs text-slate-400">Loading patients...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredPatients.map((p) => (
              <div key={p.id} className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-xl bg-medicore-50 text-medicore-700 font-bold flex items-center justify-center text-base">
                    {p.full_name?.split(" ").map((n: string) => n[0]).join("")}
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 text-sm">{p.full_name}</h3>
                    <p className="text-xs text-slate-400">{p.email}</p>
                  </div>
                </div>

                <div className="text-xs text-slate-600 space-y-1 bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <div><strong>DOB:</strong> {p.date_of_birth || "N/A"} ({p.gender || "Patient"})</div>
                  <div><strong>Blood Group:</strong> {p.blood_group || "Unknown"}</div>
                  <div className="truncate"><strong>Insurance:</strong> {p.insurance_provider || "Self-Pay"}</div>
                </div>

                <p className="text-xs text-slate-500 line-clamp-2">{p.medical_history_summary || "No chronic alerts."}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </DoctorLayout>
  );
}
