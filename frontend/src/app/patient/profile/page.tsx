"use client";

import React, { useState, useEffect } from "react";
import { PatientLayout } from "@/components/layout/patient-layout";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { User, Shield, CheckCircle2 } from "lucide-react";

export default function PatientProfilePage() {
  const { user } = useAuth();
  const [patientData, setPatientData] = useState<any>(null);
  const [address, setAddress] = useState("");
  const [emergencyContact, setEmergencyContact] = useState("");
  const [medicalHistory, setMedicalHistory] = useState("");
  const [insuranceProvider, setInsuranceProvider] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (user?.patient_id) {
      api.get<any>(`/patients/${user.patient_id}`).then(p => {
        setPatientData(p);
        setAddress(p.address || "");
        setEmergencyContact(p.emergency_contact || "");
        setMedicalHistory(p.medical_history_summary || "");
        setInsuranceProvider(p.insurance_provider || "");
      }).catch(() => {});
    }
  }, [user]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user?.patient_id) return;
    setIsSaving(true);
    setSaveSuccess(false);

    try {
      await api.put(`/patients/${user.patient_id}`, {
        address,
        emergency_contact: emergencyContact,
        medical_history_summary: medicalHistory,
        insurance_provider: insuranceProvider
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <PatientLayout>
      <div className="max-w-3xl space-y-6">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Patient Medical Profile</h1>
          <p className="text-xs text-slate-500 mt-1">Manage personal demographics, medical history summary, and emergency contacts.</p>
        </div>

        {saveSuccess && (
          <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>Profile information updated successfully in hospital records.</span>
          </div>
        )}

        <form onSubmit={handleSave} className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1">Full Legal Name</label>
              <input type="text" disabled value={user?.full_name || ""} className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-xs text-slate-600 font-medium cursor-not-allowed" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1">Registered Email</label>
              <input type="email" disabled value={user?.email || ""} className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-xs text-slate-600 font-medium cursor-not-allowed" />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1">Blood Group</label>
              <input type="text" disabled value={patientData?.blood_group || "A+"} className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-xs text-slate-600 font-medium cursor-not-allowed" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1">Date of Birth</label>
              <input type="text" disabled value={patientData?.date_of_birth || "1991-04-18"} className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-xs text-slate-600 font-medium cursor-not-allowed" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1">Emergency Contact</label>
            <input
              type="text"
              value={emergencyContact}
              onChange={(e) => setEmergencyContact(e.target.value)}
              placeholder="e.g. Spouse: Mark Jenkins - +1-555-0309"
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-xs outline-none focus:border-medicore-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1">Residential Address</label>
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="100 Medical Center Blvd"
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-xs outline-none focus:border-medicore-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1">Primary Insurance Carrier</label>
            <input
              type="text"
              value={insuranceProvider}
              onChange={(e) => setInsuranceProvider(e.target.value)}
              placeholder="e.g. Blue Cross Blue Shield Premier"
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-xs outline-none focus:border-medicore-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1">Known Allergies & Medical History</label>
            <textarea
              rows={3}
              value={medicalHistory}
              onChange={(e) => setMedicalHistory(e.target.value)}
              placeholder="List allergies, chronic conditions, and previous surgeries..."
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-xs outline-none focus:border-medicore-500"
            ></textarea>
          </div>

          <div className="pt-2 flex justify-end">
            <button
              type="submit"
              disabled={isSaving}
              className="bg-medicore-600 hover:bg-medicore-700 disabled:opacity-50 text-white font-bold px-6 py-2.5 rounded-xl text-xs transition"
            >
              {isSaving ? "Saving Updates..." : "Save Medical Profile"}
            </button>
          </div>
        </form>
      </div>
    </PatientLayout>
  );
}
