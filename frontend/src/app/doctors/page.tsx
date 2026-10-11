"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { api } from "@/lib/api";
import { Doctor, Department } from "@/types";
import { Search, Star, Calendar, ArrowRight, Stethoscope } from "lucide-react";

function DoctorsContent() {
  const searchParams = useSearchParams();
  const initialDept = searchParams.get("dept");
  const initialSearch = searchParams.get("search") || "";

  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [search, setSearch] = useState(initialSearch);
  const [selectedDept, setSelectedDept] = useState(initialDept || "");
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
    <div className="min-h-screen flex flex-col bg-slate-50">
      <PublicNav />
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 w-full">
        <div className="max-w-3xl mb-10">
          <span className="text-xs font-bold uppercase tracking-wider text-medicore-600">Medical Directory</span>
          <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight mt-1">Our Physicians & Specialists</h1>
          <p className="text-slate-600 text-base mt-2">
            Meet our board-certified medical faculty with extensive clinical experience across 5 specialty disciplines.
          </p>
        </div>

        {/* Filter / Search Bar */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-4 mb-10">
          <div className="flex-1 flex items-center gap-3 px-3 py-1">
            <Search className="w-5 h-5 text-slate-400 shrink-0" />
            <input
              type="text"
              placeholder="Search by physician name or specialty..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full text-sm outline-none text-slate-800 placeholder-slate-400 bg-transparent"
            />
          </div>
          <div className="sm:w-64 border-t sm:border-t-0 sm:border-l border-slate-200 px-3 py-1 flex items-center">
            <select
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
              className="w-full text-sm outline-none text-slate-700 bg-transparent cursor-pointer"
            >
              <option value="">All Departments</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Doctor Grid */}
        {isLoading ? (
          <div className="text-center py-16 text-sm text-slate-400">Loading medical specialists...</div>
        ) : doctors.length === 0 ? (
          <div className="text-center py-16 text-sm text-slate-500 bg-white rounded-2xl border border-slate-200">
            No doctors found matching your criteria. Try adjusting your search query or department filter.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {doctors.map((doc) => (
              <div key={doc.id} className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col justify-between shadow-sm hover:shadow-md transition">
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-14 h-14 rounded-2xl bg-medicore-100 text-medicore-700 font-bold flex items-center justify-center text-lg shadow-sm">
                      {doc.full_name.replace("Dr. ", "").split(" ").map(n => n[0]).join("")}
                    </div>
                    <div className="flex items-center gap-1 text-amber-500 text-xs font-bold bg-amber-50 px-2 py-1 rounded-lg border border-amber-200/50">
                      <Star className="w-3.5 h-3.5 fill-amber-400" />
                      <span>{doc.rating}</span>
                    </div>
                  </div>

                  <span className="text-xs font-bold text-medicore-600 tracking-wide uppercase">{doc.department_name}</span>
                  <h3 className="font-bold text-slate-900 text-lg mt-0.5">{doc.full_name}</h3>
                  <p className="text-xs text-slate-500 font-medium">{doc.specialization}</p>
                  <p className="text-[11px] text-slate-400 mt-1">{doc.qualification} • {doc.experience_years} Years Experience</p>

                  <p className="text-xs text-slate-600 mt-3 line-clamp-3 leading-relaxed">{doc.bio}</p>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-medium">Consultation Fee</span>
                    <div className="text-base font-bold text-slate-900">${doc.consultation_fee}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Link
                      href={`/doctors/${doc.id}`}
                      className="text-xs font-semibold text-slate-600 hover:text-slate-900 px-3 py-2 rounded-lg hover:bg-slate-100 transition"
                    >
                      Profile
                    </Link>
                    <Link
                      href={`/appointments?doctor_id=${doc.id}`}
                      className="bg-medicore-600 hover:bg-medicore-700 text-white text-xs font-semibold px-3 py-2 rounded-lg transition shadow-sm flex items-center gap-1"
                    >
                      <Calendar className="w-3 h-3" />
                      <span>Book Slot</span>
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
      <PublicFooter />
    </div>
  );
}

export default function DoctorsPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-medicore-600"></div>
      </div>
    }>
      <DoctorsContent />
    </Suspense>
  );
}

