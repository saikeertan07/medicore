"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { PatientLayout } from "@/components/layout/patient-layout";
import { api } from "@/lib/api";
import { Doctor, Department } from "@/types";
import { Search, Star, Calendar, Stethoscope } from "lucide-react";

export default function PatientDoctorsPage() {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [search, setSearch] = useState("");
  const [selectedDept, setSelectedDept] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get<Department[]>("/departments").then(setDepartments).catch(() => {});
  }, []);

  useEffect(() => {
    setIsLoading(true);
    let url = "/doctors";
    const params = new URLSearchParams();
    if (selectedDept) params.append("department_id", selectedDept);
    if (search) params.append("search", search);
    if (params.toString()) url += `?${params.toString()}`;

    api.get<Doctor[]>(url)
      .then(setDoctors)
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, [search, selectedDept]);

  return (
    <PatientLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Hospital Medical Directory</h1>
          <p className="text-xs text-slate-500 mt-1">Search our 15 specialist physicians, review qualifications, and check consultation availability.</p>
        </div>

        {/* Filter Bar */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-4">
          <div className="flex-1 flex items-center gap-3 px-3 py-1">
            <Search className="w-5 h-5 text-slate-400 shrink-0" />
            <input
              type="text"
              placeholder="Search by physician name or specialty..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full text-xs sm:text-sm outline-none text-slate-800 placeholder-slate-400 bg-transparent"
            />
          </div>
          <div className="sm:w-64 border-t sm:border-t-0 sm:border-l border-slate-200 px-3 py-1 flex items-center">
            <select
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
              className="w-full text-xs sm:text-sm outline-none text-slate-700 bg-transparent cursor-pointer"
            >
              <option value="">All Departments</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Doctor Cards */}
        {isLoading ? (
          <div className="text-center py-12 text-xs text-slate-400">Loading physicians...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {doctors.map((doc) => (
              <div key={doc.id} className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col justify-between shadow-sm hover:shadow-md transition">
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-12 h-12 rounded-xl bg-medicore-100 text-medicore-700 font-bold flex items-center justify-center text-base">
                      {doc.full_name.replace("Dr. ", "").split(" ").map(n => n[0]).join("")}
                    </div>
                    <div className="flex items-center gap-1 text-amber-500 text-xs font-bold bg-amber-50 px-2 py-0.5 rounded-md border border-amber-200/50">
                      <Star className="w-3.5 h-3.5 fill-amber-400" />
                      <span>{doc.rating}</span>
                    </div>
                  </div>

                  <span className="text-xs font-semibold text-medicore-600 uppercase tracking-wide">{doc.department_name}</span>
                  <h3 className="font-bold text-slate-900 text-base mt-0.5">{doc.full_name}</h3>
                  <p className="text-xs text-slate-500">{doc.specialization}</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">{doc.qualification} • Room {doc.room_number || "OPD"}</p>
                  <p className="text-xs text-slate-600 mt-2.5 line-clamp-2">{doc.bio}</p>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-medium">Fee</span>
                    <div className="text-sm font-bold text-slate-900">${doc.consultation_fee}</div>
                  </div>
                  <Link
                    href={`/appointments?doctor_id=${doc.id}`}
                    className="bg-medicore-600 hover:bg-medicore-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition shadow-sm flex items-center gap-1"
                  >
                    <Calendar className="w-3 h-3" />
                    <span>Book</span>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </PatientLayout>
  );
}
