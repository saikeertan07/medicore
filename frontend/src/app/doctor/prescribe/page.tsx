"use client";

import React, { useState, useEffect } from "react";
import { DoctorLayout } from "@/components/layout/doctor-layout";
import { api } from "@/lib/api";
import { 
  Pill, ShieldAlert, CheckCircle2, AlertTriangle, 
  XCircle, Stethoscope, RefreshCw, Plus, Trash2, Send, Check
} from "lucide-react";

export default function DoctorPrescribePage() {
  const [patients, setPatients] = useState<any[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<number | null>(null);

  const [proposedDrug, setProposedDrug] = useState("Aspirin");
  const [dosage, setDosage] = useState("325mg PO Daily");
  const [frequency, setFrequency] = useState("Once daily with food");
  const [duration, setDuration] = useState("30 days");
  const [instructions, setInstructions] = useState("Take with a full glass of water. Do not take with other NSAIDs.");

  const [activeMeds, setActiveMeds] = useState<string[]>(["Warfarin", "Lisinopril"]);
  const [newMedInput, setNewMedInput] = useState("");
  const [allergies, setAllergies] = useState<string[]>(["Penicillin"]);
  const [newAllergyInput, setNewAllergyInput] = useState("");
  const [egfr, setEgfr] = useState<number>(65);

  const [isLoading, setIsLoading] = useState(false);
  const [safetyAudit, setSafetyAudit] = useState<any>(null);

  const [overrideAcknowledged, setOverrideAcknowledged] = useState(false);
  const [isIssuing, setIsIssuing] = useState(false);
  const [issueSuccess, setIssueSuccess] = useState<any>(null);
  const [issueError, setIssueError] = useState<string | null>(null);

  useEffect(() => {
    api.get<any[]>("/patients")
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setPatients(data);
          setSelectedPatientId(data[0].id);
        }
      })
      .catch(() => {});
  }, []);

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setIssueSuccess(null);
    setIssueError(null);
    setOverrideAcknowledged(false);
    try {
      const res = await api.post<any>("/pharmacy/verify-prescription", {
        proposed_drug: proposedDrug,
        dosage: dosage,
        active_medications: activeMeds,
        patient_allergies: allergies,
        patient_egfr: egfr
      });
      setSafetyAudit(res);
    } catch (err: any) {
      alert(err.message || "Failed to verify prescription safety.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleIssuePrescription = async () => {
    if (!selectedPatientId) {
      alert("Please select a target patient.");
      return;
    }

    if (safetyAudit?.verdict === "BLOCKED") {
      alert("Cannot issue medication: Severe pharmacological contraindication detected.");
      return;
    }

    if (safetyAudit?.verdict === "WARNING_OVERRIDABLE" && !overrideAcknowledged) {
      alert("Please acknowledge the clinical safety warning before issuing.");
      return;
    }

    setIsIssuing(true);
    setIssueError(null);
    try {
      const payload = {
        patient_id: selectedPatientId,
        medications: [
          {
            name: proposedDrug,
            dosage: dosage,
            frequency: frequency,
            duration: duration
          }
        ],
        instructions: instructions,
        is_active: true
      };

      const result = await api.post<any>("/prescriptions", payload);
      setIssueSuccess(result);
    } catch (err: any) {
      setIssueError(err.message || "Failed to record prescription.");
    } finally {
      setIsIssuing(false);
    }
  };

  const addMed = () => {
    if (newMedInput.trim() && !activeMeds.includes(newMedInput.trim())) {
      setActiveMeds([...activeMeds, newMedInput.trim()]);
      setNewMedInput("");
    }
  };

  const removeMed = (med: string) => {
    setActiveMeds(activeMeds.filter(m => m !== med));
  };

  const addAllergy = () => {
    if (newAllergyInput.trim() && !allergies.includes(newAllergyInput.trim())) {
      setAllergies([...allergies, newAllergyInput.trim()]);
      setNewAllergyInput("");
    }
  };

  const removeAllergy = (all: string) => {
    setAllergies(allergies.filter(a => a !== all));
  };

  const getVerdictStyle = (verdict: string) => {
    switch (verdict) {
      case "BLOCKED":
        return "bg-red-950/80 border-red-700 text-red-200";
      case "WARNING_OVERRIDABLE":
        return "bg-amber-950/80 border-amber-700 text-amber-200";
      default:
        return "bg-emerald-950/80 border-emerald-700 text-emerald-200";
    }
  };

  return (
    <DoctorLayout>
      <div className="p-8 max-w-6xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <Pill className="w-8 h-8 text-emerald-400" />
            Clinical Prescribing & Medication Safety AI
          </h1>
          <p className="text-zinc-400 mt-1">
            Real-time checks for drug-drug interactions, allergy cross-reactivity, and automated clinical record commitment.
          </p>
        </div>

        {issueSuccess && (
          <div className="bg-emerald-950/80 border border-emerald-600 rounded-2xl p-5 text-emerald-200 flex items-start gap-4 shadow-xl">
            <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="font-bold text-base text-emerald-100">
                Prescription Successfully Issued (Rx #{issueSuccess.id})
              </div>
              <div className="text-xs text-emerald-300">
                Medication record committed to patient longitudinal vault with verified clinical audit trail.
              </div>
            </div>
          </div>
        )}

        {issueError && (
          <div className="bg-red-950/80 border border-red-600 rounded-2xl p-5 text-red-200 flex items-start gap-4 shadow-xl">
            <XCircle className="w-6 h-6 text-red-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="font-bold text-base text-red-100">Prescription Issuance Failed</div>
              <div className="text-xs text-red-300">{issueError}</div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Form */}
          <div className="lg:col-span-6 bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl space-y-6">
            <form onSubmit={handleVerify} className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">
                  Target Patient
                </label>
                {patients.length > 0 ? (
                  <select
                    value={selectedPatientId || ""}
                    onChange={(e) => setSelectedPatientId(Number(e.target.value))}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2.5 text-white"
                  >
                    {patients.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.full_name || `Patient #${p.id}`} ({p.email || p.patient_number || "ID: " + p.id})
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="number"
                    placeholder="Enter Patient ID (e.g. 1)"
                    value={selectedPatientId || ""}
                    onChange={(e) => setSelectedPatientId(Number(e.target.value))}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2.5 text-white"
                  />
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">
                    Proposed Medication
                  </label>
                  <input
                    type="text"
                    required
                    value={proposedDrug}
                    onChange={(e) => setProposedDrug(e.target.value)}
                    placeholder="e.g. Aspirin, Amoxicillin, Metformin"
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2.5 text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">
                    Dosage & Route
                  </label>
                  <input
                    type="text"
                    required
                    value={dosage}
                    onChange={(e) => setDosage(e.target.value)}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2.5 text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">
                    Frequency
                  </label>
                  <input
                    type="text"
                    value={frequency}
                    onChange={(e) => setFrequency(e.target.value)}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2.5 text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">
                    Duration
                  </label>
                  <input
                    type="text"
                    value={duration}
                    onChange={(e) => setDuration(e.target.value)}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2.5 text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">
                  Clinical Instructions
                </label>
                <textarea
                  rows={2}
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2.5 text-white text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">
                  Renal Function (eGFR mL/min/1.73m²)
                </label>
                <input
                  type="number"
                  value={egfr}
                  onChange={(e) => setEgfr(parseFloat(e.target.value) || 0)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2.5 text-white"
                />
              </div>

              {/* Active Meds */}
              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                  Current Active Medications
                </label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={newMedInput}
                    onChange={(e) => setNewMedInput(e.target.value)}
                    placeholder="Add medication..."
                    className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-white"
                  />
                  <button
                    type="button"
                    onClick={addMed}
                    className="px-3 py-1.5 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-xs font-semibold text-white flex items-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {activeMeds.map((med, i) => (
                    <span key={i} className="px-2.5 py-1 bg-zinc-800 border border-zinc-700 rounded-md text-xs text-zinc-200 flex items-center gap-1.5">
                      {med}
                      <button type="button" onClick={() => removeMed(med)} className="hover:text-red-400">
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              </div>

              {/* Allergies */}
              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                  Documented Patient Allergies
                </label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={newAllergyInput}
                    onChange={(e) => setNewAllergyInput(e.target.value)}
                    placeholder="Add allergy..."
                    className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-white"
                  />
                  <button
                    type="button"
                    onClick={addAllergy}
                    className="px-3 py-1.5 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-xs font-semibold text-white flex items-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {allergies.map((all, i) => (
                    <span key={i} className="px-2.5 py-1 bg-red-950/40 border border-red-800/60 rounded-md text-xs text-red-300 flex items-center gap-1.5">
                      {all}
                      <button type="button" onClick={() => removeAllergy(all)} className="hover:text-red-200">
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold rounded-xl shadow-lg transition-all flex items-center justify-center gap-2"
              >
                {isLoading ? <RefreshCw className="w-5 h-5 animate-spin" /> : <ShieldAlert className="w-5 h-5" />}
                Audit Prescription Safety
              </button>
            </form>
          </div>

          {/* Audit Results */}
          <div className="lg:col-span-6 space-y-6">
            {safetyAudit ? (
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl space-y-6">
                <div className={`p-4 rounded-xl border flex items-start gap-3 ${getVerdictStyle(safetyAudit.verdict)}`}>
                  {safetyAudit.verdict === "BLOCKED" ? (
                    <XCircle className="w-6 h-6 text-red-400 shrink-0 mt-0.5" />
                  ) : safetyAudit.verdict === "WARNING_OVERRIDABLE" ? (
                    <AlertTriangle className="w-6 h-6 text-amber-400 shrink-0 mt-0.5" />
                  ) : (
                    <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <div className="font-bold text-base">{safetyAudit.verdict}</div>
                    <div className="text-xs mt-1 leading-relaxed opacity-90">{safetyAudit.action_guidance}</div>
                  </div>
                </div>

                {/* Interactions */}
                {safetyAudit.drug_interactions && safetyAudit.drug_interactions.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
                      Drug-Drug Interaction Warnings ({safetyAudit.drug_interactions.length})
                    </h4>
                    {safetyAudit.drug_interactions.map((inter: any, idx: number) => (
                      <div key={idx} className="p-3 bg-zinc-800/60 rounded-xl border border-zinc-700/60 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-sm text-red-300">
                            {inter.proposed_drug} + {inter.interacting_drug}
                          </span>
                          <span className="px-2 py-0.5 bg-red-950 text-red-400 border border-red-800 rounded text-xs font-bold">
                            {inter.severity}
                          </span>
                        </div>
                        <div className="text-xs text-zinc-300 leading-relaxed">{inter.mechanism}</div>
                        <div className="text-xs text-amber-300 mt-1 font-medium">💡 {inter.recommendation}</div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Allergies */}
                {safetyAudit.allergy_warnings && safetyAudit.allergy_warnings.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
                      Allergy Cross-Reactivity Alerts
                    </h4>
                    {safetyAudit.allergy_warnings.map((all: any, idx: number) => (
                      <div key={idx} className="p-3 bg-red-950/40 rounded-xl border border-red-800/60 text-xs text-red-200">
                        {all.message}
                      </div>
                    ))}
                  </div>
                )}

                {/* Renal Alert */}
                {safetyAudit.renal_contraindication && (
                  <div className="p-3 bg-red-950/40 rounded-xl border border-red-800/60 text-xs text-red-200">
                    <strong>Renal Safety Alert:</strong> {safetyAudit.renal_contraindication.message}
                  </div>
                )}

                {/* Action Area: Issuance */}
                <div className="pt-4 border-t border-zinc-800 space-y-3">
                  {safetyAudit.verdict === "WARNING_OVERRIDABLE" && (
                    <label className="flex items-center gap-2.5 text-xs text-amber-300 cursor-pointer p-3 bg-amber-950/30 rounded-xl border border-amber-800/50">
                      <input
                        type="checkbox"
                        checked={overrideAcknowledged}
                        onChange={(e) => setOverrideAcknowledged(e.target.checked)}
                        className="rounded border-amber-600 text-amber-500 focus:ring-amber-500"
                      />
                      <span>I confirm that I have reviewed the interaction warnings and authorize clinical override.</span>
                    </label>
                  )}

                  <button
                    type="button"
                    onClick={handleIssuePrescription}
                    disabled={isIssuing || safetyAudit.verdict === "BLOCKED" || (safetyAudit.verdict === "WARNING_OVERRIDABLE" && !overrideAcknowledged)}
                    className={`w-full py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition-all ${
                      safetyAudit.verdict === "BLOCKED"
                        ? "bg-zinc-800 text-zinc-500 cursor-not-allowed"
                        : "bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-900/30"
                    }`}
                  >
                    {isIssuing ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                    {safetyAudit.verdict === "BLOCKED" ? "Contraindicated (Cannot Issue)" : "Commit & Issue Prescription"}
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 text-center text-zinc-500 shadow-xl space-y-3">
                <Stethoscope className="w-12 h-12 text-zinc-600 mx-auto" />
                <div className="font-medium text-zinc-400">Awaiting Prescription Audit</div>
                <div className="text-xs text-zinc-500">
                  Select a patient, enter proposed medication, and run safety audit before issuing the prescription to the patient's record.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </DoctorLayout>
  );
}
