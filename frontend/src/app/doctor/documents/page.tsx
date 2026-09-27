"use client";

import React, { useState, useEffect } from "react";
import { DoctorLayout } from "@/components/layout/doctor-layout";
import { api } from "@/lib/api";
import { MedicalDocument } from "@/types";
import { FileText, Download, Search, CheckCircle2 } from "lucide-react";

export default function DoctorDocumentsPage() {
  const [documents, setDocuments] = useState<MedicalDocument[]>([]);
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get<MedicalDocument[]>("/documents")
      .then(setDocuments)
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  const filteredDocs = documents.filter(d =>
    d.file_name?.toLowerCase().includes(search.toLowerCase()) ||
    d.patient_name?.toLowerCase().includes(search.toLowerCase()) ||
    d.tags?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <DoctorLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Patient Diagnostic Documents</h1>
          <p className="text-xs text-slate-500 mt-1">Review lab findings, imaging studies, and AI structured digests across assigned patients.</p>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-3 px-3 py-1">
            <Search className="w-5 h-5 text-slate-400 shrink-0" />
            <input
              type="text"
              placeholder="Search documents by patient name, study title, or tags..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full text-xs sm:text-sm outline-none text-slate-800 placeholder-slate-400 bg-transparent"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="text-center py-12 text-xs text-slate-400">Loading documents...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {filteredDocs.map((doc) => (
              <div key={doc.id} className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col justify-between shadow-sm hover:shadow-md transition">
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-medicore-50 text-medicore-600 flex items-center justify-center shrink-0">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="font-bold text-slate-900 text-sm">{doc.file_name}</h3>
                        <p className="text-[11px] text-slate-400">Patient: <strong className="text-slate-700">{doc.patient_name || "Assigned Patient"}</strong></p>
                      </div>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700">
                      {doc.status}
                    </span>
                  </div>

                  <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-100 text-xs text-slate-600 mt-2">
                    <span className="font-bold text-slate-700 block text-[11px] uppercase tracking-wider mb-1">AI Clinical Digest</span>
                    <p className="leading-relaxed">{doc.summary}</p>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  <span className="text-slate-400">{doc.tags || "Clinical"} • {(doc.file_size / 1024).toFixed(0)} KB</span>
                  <a
                    href={`http://localhost:8000/api/v1/documents/${doc.id}/download`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-medicore-600 hover:text-medicore-700 font-semibold flex items-center gap-1.5"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download Original</span>
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </DoctorLayout>
  );
}
