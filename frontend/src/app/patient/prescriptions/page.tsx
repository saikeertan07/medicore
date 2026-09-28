"use client";

import React, { useState, useEffect } from "react";
import { PatientLayout } from "@/components/layout/patient-layout";
import { api } from "@/lib/api";
import { Pill, Clock, AlertCircle, RefreshCw, CheckCircle2, UserCheck, Calendar } from "lucide-react";

interface MedicationItem {
  name: string;
  dosage: string;
  frequency?: string;
  duration?: string;
}

interface PrescriptionRecord {
  id: number;
  patient_id: number;
  doctor_id: number;
  doctor_name?: string;
  specialization?: string;
  medications: MedicationItem[] | string;
  instructions?: string;
  is_active: boolean;
  created_at: string;
}

export default function PatientPrescriptionsPage() {
  const [prescriptions, setPrescriptions] = useState<PrescriptionRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPrescriptions = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<PrescriptionRecord[]>("/prescriptions");
      setPrescriptions(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message || "Failed to load prescriptions.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPrescriptions();
  }, []);

  const parseMedications = (meds: MedicationItem[] | string): MedicationItem[] => {
    if (Array.isArray(meds)) return meds;
    if (typeof meds === "string") {
      try {
        const parsed = JSON.parse(meds);
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [{ name: meds, dosage: "As directed" }];
      }
    }
    return [];
  };

  return (
    <PatientLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Prescription Medications</h1>
            <p className="text-xs text-slate-500 mt-1">
              Active medications, dosage instructions, and clinical safety records prescribed by your care team.
            </p>
          </div>
          <button
            onClick={fetchPrescriptions}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 shadow-sm transition self-start sm:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {isLoading ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500 shadow-sm">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-medicore-600 mb-3" />
            <p className="text-sm font-medium">Loading clinical prescriptions...</p>
          </div>
        ) : prescriptions.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500 shadow-sm space-y-2">
            <Pill className="w-10 h-10 text-slate-400 mx-auto mb-2" />
            <h3 className="text-base font-semibold text-slate-800">No Prescriptions On File</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              You currently have no prescribed medications recorded. When your physician writes a prescription, it will appear here in real-time.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {prescriptions.map((p) => {
              const meds = parseMedications(p.medications);
              const dateStr = p.created_at ? new Date(p.created_at).toLocaleDateString("en-US", {
                year: "numeric",
                month: "short",
                day: "numeric"
              }) : "Recent";

              return (
                <div
                  key={p.id}
                  className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shadow-sm hover:border-slate-300 transition"
                >
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center shrink-0">
                      <Pill className="w-6 h-6" />
                    </div>
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs font-bold text-slate-500">Rx #{p.id}</span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            p.is_active
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : "bg-slate-100 text-slate-600 border border-slate-200"
                          }`}
                        >
                          {p.is_active ? "ACTIVE" : "COMPLETED / CANCELLED"}
                        </span>
                      </div>

                      <div className="space-y-1">
                        {meds.map((m, mIdx) => (
                          <div key={mIdx} className="text-slate-900 font-semibold text-sm flex items-center gap-2">
                            <span>{m.name}</span>
                            <span className="text-xs font-normal text-slate-500">({m.dosage})</span>
                            {m.frequency && (
                              <span className="text-[11px] font-medium text-teal-700 bg-teal-50 px-2 py-0.5 rounded">
                                {m.frequency}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>

                      {p.instructions && (
                        <p className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-100 max-w-xl">
                          <strong className="text-slate-700">Instructions:</strong> {p.instructions}
                        </p>
                      )}

                      <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-500 pt-1">
                        <span className="flex items-center gap-1">
                          <UserCheck className="w-3.5 h-3.5 text-slate-400" />
                          Prescribed by {p.doctor_name || "Staff Physician"}
                          {p.specialization && ` (${p.specialization})`}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5 text-slate-400" />
                          {dateStr}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end md:self-auto shrink-0">
                    <button
                      onClick={() => alert(`Refill request submitted for Rx #${p.id}`)}
                      className="bg-teal-50 hover:bg-teal-100 text-teal-700 text-xs font-semibold px-4 py-2 rounded-xl transition border border-teal-200"
                    >
                      Request Refill
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </PatientLayout>
  );
}
