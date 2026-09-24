"use client";

import React, { useState, useEffect } from "react";
import { DoctorLayout } from "@/components/layout/doctor-layout";
import { api } from "@/lib/api";
import { MedicalDocument } from "@/types";
import { FileCheck, Download, Search, CheckCircle2 } from "lucide-react";

export default function DoctorReportsPage() {
  const [reports, setReports] = useState<MedicalDocument[]>([]);
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get<MedicalDocument[]>("/documents")
      .then(docs => {
        setReports(docs.filter(d => d.status === "COMPLETED"));
      })
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  const filteredReports = reports.filter(r =>
    r.file_name?.toLowerCase().includes(search.toLowerCase()) ||
    r.patient_name?.toLowerCase().includes(search.toLowerCase()) ||
    r.summary?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <DoctorLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Clinical Diagnostic Reports</h1>
          <p className="text-xs text-slate-500 mt-1">Finalized laboratory results, radiological studies, and clinical pathology reports.</p>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-3 px-3 py-1">
            <Search className="w-5 h-5 text-slate-400 shrink-0" />
            <input
              type="text"
              placeholder="Search by report name, patient, or clinical keywords..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full text-xs sm:text-sm outline-none text-slate-800 placeholder-slate-400 bg-transparent"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="text-center py-12 text-xs text-slate-400">Loading clinical reports...</div>
        ) : filteredReports.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-xs text-slate-500">
            No diagnostic reports found matching search criteria.
          </div>
        ) : (
          <div className="space-y-3">
            {filteredReports.map((r) => (
              <div key={r.id} className="bg-white rounded-2xl border border-slate-200 p-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 shadow-sm hover:shadow-md transition">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <FileCheck className="w-4 h-4 text-medicore-600" />
                    <h3 className="font-bold text-slate-900 text-sm">{r.file_name}</h3>
                    <span className="text-xs text-slate-400">• Patient: <strong className="text-slate-700">{r.patient_name || "Assigned"}</strong></span>
                  </div>
                  <p className="text-xs text-slate-600 max-w-2xl">{r.summary}</p>
                  <span className="text-[11px] text-slate-400 block pt-0.5">{r.created_at.substring(0, 10)} • {r.tags || "Diagnostic Pathology"}</span>
                </div>

                <a
                  href={`http://localhost:8000/api/v1/documents/${r.id}/download`}
                  target="_blank"
                  rel="noreferrer"
                  className="bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold px-4 py-2 rounded-xl transition border border-slate-200 flex items-center gap-2 shrink-0"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download</span>
                </a>
              </div>
            ))}
          </div>
        )}
      </div>
    </DoctorLayout>
  );
}
