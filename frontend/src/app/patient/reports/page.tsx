"use client";

import React, { useState, useEffect } from "react";
import { PatientLayout } from "@/components/layout/patient-layout";
import { api } from "@/lib/api";
import { MedicalDocument } from "@/types";
import { FileCheck, Download, AlertCircle, CheckCircle2 } from "lucide-react";

export default function PatientReportsPage() {
  const [reports, setReports] = useState<MedicalDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get<MedicalDocument[]>("/documents")
      .then(docs => {
        // Filter completed reports / labs
        setReports(docs.filter(d => d.status === "COMPLETED"));
      })
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <PatientLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Clinical Diagnostic Reports</h1>
          <p className="text-xs text-slate-500 mt-1">Verified lab results, electrocardiograms, and diagnostic radiology imaging.</p>
        </div>

        {isLoading ? (
          <div className="text-center py-12 text-xs text-slate-400">Loading clinical reports...</div>
        ) : reports.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-xs text-slate-500">
            No diagnostic reports on record. Reports will appear here once finalized by hospital labs.
          </div>
        ) : (
          <div className="space-y-4">
            {reports.map((r) => (
              <div key={r.id} className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 shadow-sm hover:shadow-md transition">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <FileCheck className="w-5 h-5 text-medicore-600" />
                    <h3 className="font-bold text-slate-900 text-sm">{r.file_name}</h3>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700">Verified</span>
                  </div>
                  <p className="text-xs text-slate-600 max-w-2xl mt-1">{r.summary}</p>
                  <span className="text-[11px] text-slate-400 block pt-1">{r.created_at.substring(0, 10)} • {r.tags || "Diagnostic Study"}</span>
                </div>

                <a
                  href={`http://localhost:8000/api/v1/documents/${r.id}/download`}
                  target="_blank"
                  rel="noreferrer"
                  className="bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold px-4 py-2 rounded-xl transition border border-slate-200 flex items-center gap-2 shrink-0"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download PDF</span>
                </a>
              </div>
            ))}
          </div>
        )}
      </div>
    </PatientLayout>
  );
}
