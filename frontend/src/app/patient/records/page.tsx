"use client";

import React, { useState, useEffect } from "react";
import { PatientLayout } from "@/components/layout/patient-layout";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { ClinicalTimelineEntry, LabResult } from "@/types";
import { 
  FileCheck, Stethoscope, Activity, Heart, Thermometer, 
  Calendar, Clock, ShieldCheck, AlertCircle, CheckCircle2,
  FlaskConical, TestTube2, AlertTriangle
} from "lucide-react";

export default function PatientRecordsPage() {
  const { user } = useAuth();
  const [timeline, setTimeline] = useState<ClinicalTimelineEntry[]>([]);
  const [labResults, setLabResults] = useState<LabResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>("ALL");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!user || !user.patient_id) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    Promise.all([
      api.get<ClinicalTimelineEntry[]>(`/patients/${user.patient_id}/clinical-timeline`),
      api.get<LabResult[]>(`/lab/patients/${user.patient_id}/results`).catch(() => [])
    ])
      .then(([tData, lData]) => {
        setTimeline(tData || []);
        setLabResults(lData || []);
        setErrorMsg(null);
      })
      .catch(err => {
        setErrorMsg(err.message || "Unable to retrieve clinical timeline.");
      })
      .finally(() => setIsLoading(false));
  }, [user]);

  const filteredEntries = timeline.filter(entry => {
    if (filterType === "ALL") return true;
    return entry.entry_type === filterType;
  });

  return (
    <PatientLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-xl bg-medicore-50 text-medicore-600">
                <FileCheck className="w-5 h-5" />
              </span>
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">Longitudinal Clinical Records</h1>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Authoritative medical history, clinical assessments, vitals intake, and physician treatment plans.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-xl border border-emerald-200">
            <ShieldCheck className="w-4 h-4" />
            <span>Verified & Finalized</span>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex gap-2 overflow-x-auto pb-1">
          {[
            { label: "All Records", val: "ALL" },
            { label: "Diagnostic Labs", val: "LAB" },
            { label: "Physician Notes", val: "CLINICAL_NOTE" },
            { label: "Vitals & Intake", val: "VITALS" },
            { label: "Diagnoses", val: "DIAGNOSIS" },
            { label: "Encounters", val: "ENCOUNTER" },
          ].map(btn => (
            <button
              key={btn.val}
              onClick={() => setFilterType(btn.val)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition border ${
                filterType === btn.val
                  ? "bg-medicore-600 text-white border-medicore-600 shadow-sm"
                  : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
              }`}
            >
              {btn.label}
            </button>
          ))}
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-xs text-slate-400">
            Loading longitudinal medical records...
          </div>
        ) : errorMsg ? (
          <div className="bg-rose-50 border border-rose-200 text-rose-700 rounded-2xl p-6 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Laboratory Diagnostic Results Card */}
            {(filterType === "ALL" || filterType === "LAB") && labResults.length > 0 && (
              <div className="bg-white rounded-2xl border border-purple-200 p-6 shadow-sm space-y-4">
                <div className="flex justify-between items-center pb-3 border-b border-purple-100">
                  <div className="flex items-center gap-2">
                    <span className="p-2 rounded-xl bg-purple-50 text-purple-600">
                      <FlaskConical className="w-4 h-4" />
                    </span>
                    <div>
                      <h2 className="text-sm font-bold text-slate-900">Authoritative Diagnostic Laboratory Results</h2>
                      <p className="text-[11px] text-slate-500">Verified and finalized analyzer reports released to medical record.</p>
                    </div>
                  </div>
                  <span className="text-xs font-bold text-purple-700 bg-purple-50 px-2.5 py-1 rounded-xl border border-purple-200">
                    {labResults.length} Finalized Result{labResults.length > 1 ? "s" : ""}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {labResults.map(res => (
                    <div key={res.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
                      <div className="flex justify-between items-start">
                        <div>
                          <strong className="text-xs font-bold text-slate-900">{res.test_name}</strong>
                          <span className="font-mono text-[10px] text-slate-500 bg-slate-200 px-1.5 py-0.5 rounded ml-1.5">{res.test_code}</span>
                        </div>
                        <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded flex items-center gap-1 ${
                          res.abnormal_flag === "CRITICAL" ? "bg-rose-100 text-rose-800 border border-rose-300 animate-pulse" :
                          res.abnormal_flag !== "NORMAL" ? "bg-amber-100 text-amber-800 border border-amber-200" :
                          "bg-emerald-50 text-emerald-700 border border-emerald-200"
                        }`}>
                          {res.abnormal_flag === "CRITICAL" && <AlertTriangle className="w-3 h-3" />}
                          {res.abnormal_flag}
                        </span>
                      </div>

                      <div className="flex items-baseline gap-2">
                        <span className="text-xl font-extrabold text-slate-900">{res.value}</span>
                        {res.unit && <span className="text-xs font-medium text-slate-500">{res.unit}</span>}
                      </div>

                      {res.reference_range && (
                        <div className="text-[11px] text-slate-500 flex justify-between">
                          <span>Standard Reference Range:</span>
                          <span className="font-mono text-slate-700 font-medium">{res.reference_range}</span>
                        </div>
                      )}

                      <div className="text-[10px] text-slate-400 pt-1 border-t border-slate-200 flex justify-between">
                        <span>Verified: {new Date(res.verified_at || res.created_at).toLocaleDateString()}</span>
                        <span className="text-emerald-700 font-semibold uppercase">{res.status}</span>
                      </div>

                      {res.amendment_reason && (
                        <p className="text-[10px] text-purple-700 italic bg-purple-50 p-1.5 rounded border border-purple-100">
                          Clinical Amendment: {res.amendment_reason}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {filterType === "LAB" && labResults.length === 0 && (
              <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-xs text-slate-500">
                No finalized laboratory test results on record.
              </div>
            )}

            {filterType !== "LAB" && filteredEntries.length === 0 ? (
              <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-xs text-slate-500">
                No clinical documentation matching the selected filter.
              </div>
            ) : filterType !== "LAB" && (
              <div className="relative border-l-2 border-slate-200 ml-4 space-y-6 pl-6">
            {filteredEntries.map((entry, idx) => (
              <div key={idx} className="relative group">
                {/* Timeline Dot */}
                <span className={`absolute -left-[31px] top-1.5 w-4 h-4 rounded-full border-2 border-white shadow-sm flex items-center justify-center ${
                  entry.entry_type === "CLINICAL_NOTE" ? "bg-indigo-600" :
                  entry.entry_type === "VITALS" ? "bg-emerald-500" :
                  entry.entry_type === "DIAGNOSIS" ? "bg-rose-500" : "bg-sky-500"
                }`} />

                {/* Entry Card */}
                <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition space-y-3">
                  <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-2 border-b border-slate-100 pb-3">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded ${
                        entry.entry_type === "CLINICAL_NOTE" ? "bg-indigo-50 text-indigo-700" :
                        entry.entry_type === "VITALS" ? "bg-emerald-50 text-emerald-700" :
                        entry.entry_type === "DIAGNOSIS" ? "bg-rose-50 text-rose-700" : "bg-sky-50 text-sky-700"
                      }`}>
                        {entry.entry_type.replace('_', ' ')}
                      </span>
                      <h3 className="text-sm font-bold text-slate-900">{entry.summary}</h3>
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-slate-400">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {new Date(entry.date).toLocaleDateString()}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(entry.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>

                  {/* Metadata */}
                  {(entry.doctor_name || entry.department_name) && (
                    <div className="flex items-center gap-4 text-xs text-slate-600">
                      {entry.doctor_name && (
                        <span className="flex items-center gap-1.5 font-medium">
                          <Stethoscope className="w-3.5 h-3.5 text-medicore-600" />
                          {entry.doctor_name}
                        </span>
                      )}
                      {entry.department_name && (
                        <span className="text-slate-400">
                          Dept: <strong className="text-slate-700">{entry.department_name}</strong>
                        </span>
                      )}
                    </div>
                  )}

                  {/* Details Block */}
                  {entry.entry_type === "CLINICAL_NOTE" && (
                    <div className="space-y-2 text-xs bg-slate-50 p-4 rounded-xl border border-slate-100">
                      {entry.details.chief_complaint && (
                        <div>
                          <strong className="text-slate-700">Chief Complaint:</strong>{" "}
                          <span className="text-slate-600">{entry.details.chief_complaint}</span>
                        </div>
                      )}
                      {entry.details.assessment && (
                        <div>
                          <strong className="text-slate-700">Assessment:</strong>{" "}
                          <span className="text-slate-600">{entry.details.assessment}</span>
                        </div>
                      )}
                      {entry.details.treatment_plan && (
                        <div>
                          <strong className="text-slate-700">Treatment Plan:</strong>{" "}
                          <span className="text-slate-600">{entry.details.treatment_plan}</span>
                        </div>
                      )}
                      {entry.details.patient_instructions && (
                        <div>
                          <strong className="text-slate-700">Physician Instructions:</strong>{" "}
                          <span className="text-slate-600">{entry.details.patient_instructions}</span>
                        </div>
                      )}
                      {entry.details.follow_up_instructions && (
                        <div>
                          <strong className="text-slate-700">Follow-up:</strong>{" "}
                          <span className="text-slate-600">{entry.details.follow_up_instructions}</span>
                          {entry.details.follow_up_date && (
                            <span className="text-medicore-600 font-semibold ml-2">({entry.details.follow_up_date})</span>
                          )}
                        </div>
                      )}
                      {entry.details.amendment_reason && (
                        <div className="pt-2 border-t border-slate-200 text-amber-800 text-[11px]">
                          <strong>Clinical Amendment Note:</strong> {entry.details.amendment_reason}
                        </div>
                      )}
                    </div>
                  )}

                  {entry.entry_type === "VITALS" && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-3 rounded-xl border border-slate-100 text-xs">
                      {entry.details.temperature_c && (
                        <div>
                          <span className="text-slate-400 block text-[10px]">Temperature</span>
                          <span className="font-bold text-slate-800">{entry.details.temperature_c} °C</span>
                        </div>
                      )}
                      {entry.details.heart_rate && (
                        <div>
                          <span className="text-slate-400 block text-[10px]">Heart Rate</span>
                          <span className="font-bold text-slate-800">{entry.details.heart_rate} bpm</span>
                        </div>
                      )}
                      {entry.details.systolic_bp && (
                        <div>
                          <span className="text-slate-400 block text-[10px]">Blood Pressure</span>
                          <span className="font-bold text-slate-800">{entry.details.systolic_bp}/{entry.details.diastolic_bp} mmHg</span>
                        </div>
                      )}
                      {entry.details.oxygen_saturation && (
                        <div>
                          <span className="text-slate-400 block text-[10px]">SpO2</span>
                          <span className="font-bold text-slate-800">{entry.details.oxygen_saturation} %</span>
                        </div>
                      )}
                      {entry.details.bmi && (
                        <div>
                          <span className="text-slate-400 block text-[10px]">Body Mass Index (BMI)</span>
                          <span className="font-bold text-slate-800">{entry.details.bmi}</span>
                        </div>
                      )}
                      {entry.details.pain_score !== null && entry.details.pain_score !== undefined && (
                        <div>
                          <span className="text-slate-400 block text-[10px]">Pain Score</span>
                          <span className="font-bold text-slate-800">{entry.details.pain_score} / 10</span>
                        </div>
                      )}
                    </div>
                  )}

                  {entry.entry_type === "DIAGNOSIS" && (
                    <div className="text-xs bg-slate-50 p-3 rounded-xl border border-slate-100 space-y-1">
                      <div>
                        <strong className="text-slate-700">Diagnosis:</strong>{" "}
                        <span className="text-slate-900 font-semibold">{entry.details.name}</span>
                        {entry.details.code && (
                          <span className="ml-2 font-mono text-[10px] bg-slate-200 px-1.5 py-0.5 rounded text-slate-700">
                            {entry.details.code_system || "Code"}: {entry.details.code}
                          </span>
                        )}
                      </div>
                      {entry.details.notes && (
                        <p className="text-slate-600">{entry.details.notes}</p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    )}
  </div>
</PatientLayout>
);
}
