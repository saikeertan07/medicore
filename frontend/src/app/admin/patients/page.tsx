"use client";

import React, { useState, useEffect } from "react";
import { AdminLayout } from "@/components/layout/admin-layout";
import { api } from "@/lib/api";
import { Search, User, ShieldCheck } from "lucide-react";

export default function AdminPatientsPage() {
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
    <AdminLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Master Patient Registry</h1>
          <p className="text-xs text-slate-500 mt-1">Enterprise view of all registered hospital patients across departments.</p>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-3">
          <Search className="w-5 h-5 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Search patient by name, email, or policy number..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full text-xs sm:text-sm outline-none text-slate-800 placeholder-slate-400 bg-transparent"
          />
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                <th className="p-4">Patient Name</th>
                <th className="p-4">Contact Info</th>
                <th className="p-4">DOB / Gender</th>
                <th className="p-4">Blood Group</th>
                <th className="p-4">Insurance Provider</th>
                <th className="p-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredPatients.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50/60 transition">
                  <td className="p-4 font-bold text-slate-900">{p.full_name}</td>
                  <td className="p-4 text-slate-600">
                    <div>{p.email}</div>
                    <div className="text-[11px] text-slate-400">{p.phone || "No phone"}</div>
                  </td>
                  <td className="p-4 text-slate-600">{p.date_of_birth || "-"} ({p.gender || "-"})</td>
                  <td className="p-4 font-semibold text-rose-600">{p.blood_group || "-"}</td>
                  <td className="p-4 text-slate-600">{p.insurance_provider || "Self-Pay"}</td>
                  <td className="p-4">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700">
                      Active
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AdminLayout>
  );
}
