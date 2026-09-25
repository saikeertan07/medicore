"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { DoctorLayout } from "@/components/layout/doctor-layout";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { 
  Encounter, EncounterVitals, ClinicalNote, ClinicalDiagnosis,
  LabOrder, LabTestDefinition, LabResult, LabOrderPriority, AbnormalFlag
} from "@/types";
import { 
  Stethoscope, Activity, FileText, CheckCircle2, Lock, 
  AlertCircle, ArrowLeft, Save, Plus, Clock, User, ShieldCheck, RefreshCw,
  FlaskConical, TestTube2, AlertTriangle
} from "lucide-react";

export default function DoctorEncounterPage() {
  const params = useParams();
  const router = useRouter();
  const encounterId = Number(params?.id);
  const { user } = useAuth();

  const [encounter, setEncounter] = useState<Encounter | null>(null);
  const [vitals, setVitals] = useState<EncounterVitals[]>([]);
  const [notes, setNotes] = useState<ClinicalNote[]>([]);
  const [diagnoses, setDiagnoses] = useState<ClinicalDiagnosis[]>([]);
  const [labOrders, setLabOrders] = useState<LabOrder[]>([]);
  const [catalogTests, setCatalogTests] = useState<LabTestDefinition[]>([]);
  const [activeNote, setActiveNote] = useState<ClinicalNote | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [showFinalizeModal, setShowFinalizeModal] = useState(false);
  const [showAmendModal, setShowAmendModal] = useState(false);
  const [amendReason, setAmendReason] = useState("");

  // Lab Ordering & Result States
  const [showLabModal, setShowLabModal] = useState(false);
  const [selectedTestIds, setSelectedTestIds] = useState<number[]>([]);
  const [labPriority, setLabPriority] = useState<LabOrderPriority>("ROUTINE");
  const [labIndication, setLabIndication] = useState("");
  const [labNotes, setLabNotes] = useState("");
  const [isSubmittingLab, setIsSubmittingLab] = useState(false);

  // Result Verification & Amendment States
  const [showVerifyModal, setShowVerifyModal] = useState(false);
  const [selectedResult, setSelectedResult] = useState<LabResult | null>(null);
  const [verifyComments, setVerifyComments] = useState("");
  const [showAmendResultModal, setShowAmendResultModal] = useState(false);
  const [amendResultVal, setAmendResultVal] = useState("");
  const [amendResultNumeric, setAmendResultNumeric] = useState<string>("");
  const [amendResultFlag, setAmendResultFlag] = useState<AbnormalFlag>("NORMAL");
  const [amendResultReason, setAmendResultReason] = useState("");

  // SOAP Fields
  const [chiefComplaint, setChiefComplaint] = useState("");
  const [hpi, setHpi] = useState("");
  const [symptoms, setSymptoms] = useState("");
  const [examFindings, setExamFindings] = useState("");
  const [observations, setObservations] = useState("");
  const [assessment, setAssessment] = useState("");
  const [diffDiag, setDiffDiag] = useState("");
  const [treatmentPlan, setTreatmentPlan] = useState("");
  const [patientInstructions, setPatientInstructions] = useState("");
  const [followUpInstructions, setFollowUpInstructions] = useState("");
  const [followUpDate, setFollowUpDate] = useState("");

  // Diagnosis Form State
  const [diagName, setDiagName] = useState("");
  const [diagCode, setDiagCode] = useState("");
  const [diagType, setDiagType] = useState<"PRIMARY" | "SECONDARY" | "WORKING" | "SUSPECTED">("PRIMARY");
  const [diagNotes, setDiagNotes] = useState("");

  const loadAll = () => {
    if (!encounterId) return;
    setIsLoading(true);
    Promise.all([
      api.get<Encounter>(`/encounters/${encounterId}`),
      api.get<EncounterVitals[]>(`/encounters/${encounterId}/vitals`),
      api.get<ClinicalNote[]>(`/encounters/${encounterId}/clinical-notes`),
      api.get<ClinicalDiagnosis[]>(`/encounters/${encounterId}/diagnoses`),
      api.get<LabOrder[]>(`/lab/orders?encounter_id=${encounterId}`),
      api.get<LabTestDefinition[]>(`/lab/tests`)
    ])
      .then(([enc, vList, nList, dList, lOrders, tCatalog]) => {
        setEncounter(enc);
        setVitals(vList);
        setNotes(nList);
        setDiagnoses(dList);
        setLabOrders(lOrders || []);
        setCatalogTests(tCatalog || []);

        // Populate active note: prefer latest note
        if (nList.length > 0) {
          const latest = nList[nList.length - 1];
          setActiveNote(latest);
          setChiefComplaint(latest.chief_complaint || "");
          setHpi(latest.history_of_present_illness || "");
          setSymptoms(latest.symptoms || "");
          setExamFindings(latest.examination_findings || "");
          setObservations(latest.observations || "");
          setAssessment(latest.clinical_assessment || "");
          setDiffDiag(latest.differential_diagnosis || "");
          setTreatmentPlan(latest.treatment_plan || "");
          setPatientInstructions(latest.patient_instructions || "");
          setFollowUpInstructions(latest.follow_up_instructions || "");
          setFollowUpDate(latest.follow_up_date || "");
        }
      })
      .catch(err => {
        setStatusMsg({ type: "error", text: err.message || "Failed to load clinical workspace." });
      })
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    loadAll();
  }, [encounterId]);

  const isLocked = activeNote?.status === "FINAL" || activeNote?.status === "AMENDED";

  const handleSaveDraft = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLocked) return;

    setIsSaving(true);
    setStatusMsg(null);

    const payload = {
      chief_complaint: chiefComplaint || undefined,
      history_of_present_illness: hpi || undefined,
      symptoms: symptoms || undefined,
      examination_findings: examFindings || undefined,
      observations: observations || undefined,
      clinical_assessment: assessment || undefined,
      differential_diagnosis: diffDiag || undefined,
      treatment_plan: treatmentPlan || undefined,
      patient_instructions: patientInstructions || undefined,
      follow_up_instructions: followUpInstructions || undefined,
      follow_up_date: followUpDate || undefined
    };

    try {
      if (activeNote) {
        // PUT update draft
        const updated = await api.put<ClinicalNote>(`/clinical-notes/${activeNote.id}`, payload);
        setActiveNote(updated);
        setStatusMsg({ type: "success", text: "Clinical note draft saved successfully." });
      } else {
        // POST create draft
        const created = await api.post<ClinicalNote>(`/encounters/${encounterId}/clinical-notes`, payload);
        setActiveNote(created);
        setStatusMsg({ type: "success", text: "Clinical note draft initiated and saved." });
      }
      loadAll();
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Failed to save clinical draft." });
    } finally {
      setIsSaving(false);
    }
  };

  const handleFinalize = async () => {
    if (!activeNote) return;
    setIsSaving(true);
    setShowFinalizeModal(false);

    try {
      await api.post(`/clinical-notes/${activeNote.id}/finalize`, {});
      setStatusMsg({ type: "success", text: "Clinical note finalized and locked in medical record." });
      loadAll();
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Failed to finalize clinical note." });
    } finally {
      setIsSaving(false);
    }
  };

  const handleAmend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeNote || !amendReason.trim()) return;

    setIsSaving(true);
    setShowAmendModal(false);

    const payload = {
      amendment_reason: amendReason,
      treatment_plan: treatmentPlan,
      patient_instructions: patientInstructions,
      follow_up_instructions: followUpInstructions,
      follow_up_date: followUpDate || undefined
    };

    try {
      await api.post(`/clinical-notes/${activeNote.id}/amend`, payload);
      setStatusMsg({ type: "success", text: "New versioned clinical amendment appended successfully." });
      setAmendReason("");
      loadAll();
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Failed to amend note." });
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddDiagnosis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!diagName.trim()) return;

    try {
      await api.post(`/encounters/${encounterId}/diagnoses`, {
        name: diagName.trim(),
        code: diagCode.trim() || undefined,
        type: diagType,
        notes: diagNotes.trim() || undefined
      });
      setDiagName("");
      setDiagCode("");
      setDiagNotes("");
      loadAll();
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Failed to record diagnosis." });
    }
  };

  const handleCreateLabOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!encounter || selectedTestIds.length === 0) return;

    setIsSubmittingLab(true);
    setStatusMsg(null);
    try {
      await api.post('/lab/orders', {
        patient_id: encounter.patient_id,
        encounter_id: encounter.id,
        priority: labPriority,
        clinical_indication: labIndication || undefined,
        notes: labNotes || undefined,
        items: selectedTestIds.map(id => ({ test_id: id }))
      });
      setShowLabModal(false);
      setSelectedTestIds([]);
      setLabIndication("");
      setLabNotes("");
      setStatusMsg({ type: "success", text: "Laboratory order placed successfully." });
      loadAll();
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Failed to submit laboratory order." });
    } finally {
      setIsSubmittingLab(false);
    }
  };

  const handleVerifyResult = async () => {
    if (!selectedResult) return;
    try {
      await api.post(`/lab/results/${selectedResult.id}/verify`, {
        comments: verifyComments.trim() || undefined
      });
      setShowVerifyModal(false);
      setSelectedResult(null);
      setVerifyComments("");
      setStatusMsg({ type: "success", text: "Laboratory result verified and finalized." });
      loadAll();
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Failed to verify result." });
    }
  };

  const handleAmendResult = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedResult || !amendResultReason.trim()) return;
    try {
      await api.post(`/lab/results/${selectedResult.id}/amend`, {
        value: amendResultVal,
        numeric_value: amendResultNumeric ? parseFloat(amendResultNumeric) : undefined,
        abnormal_flag: amendResultFlag,
        amendment_reason: amendResultReason.trim()
      });
      setShowAmendResultModal(false);
      setSelectedResult(null);
      setAmendResultReason("");
      setStatusMsg({ type: "success", text: "Laboratory result amended. Version recorded." });
      loadAll();
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Failed to amend result." });
    }
  };

  const handleCompleteEncounter = async () => {
    try {
      await api.post(`/encounters/${encounterId}/complete`, {});
      setStatusMsg({ type: "success", text: "Encounter marked COMPLETED. Appointment synchronized." });
      loadAll();
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Failed to complete encounter." });
    }
  };

  return (
    <DoctorLayout>
      <div className="space-y-6">
        {/* Navigation back */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => router.push("/doctor/dashboard")}
            className="flex items-center gap-2 text-xs font-semibold text-slate-500 hover:text-slate-800 transition"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Doctor Dashboard</span>
          </button>
          {encounter && (
            <span className="font-mono text-xs px-3 py-1 rounded-xl bg-slate-100 text-slate-700 font-bold border border-slate-200">
              {encounter.encounter_number}
            </span>
          )}
        </div>

        {/* Patient & Encounter Header */}
        {encounter && (
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-medicore-50 text-medicore-600 flex items-center justify-center font-bold text-lg border border-medicore-100">
                <Stethoscope className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-lg font-bold text-slate-900">{encounter.patient_name || "Patient"}</h1>
                  <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded ${
                    encounter.status === "COMPLETED" ? "bg-emerald-50 text-emerald-700" :
                    encounter.status === "IN_PROGRESS" ? "bg-indigo-50 text-indigo-700" : "bg-amber-50 text-amber-700"
                  }`}>
                    {encounter.status}
                  </span>
                  {activeNote && (
                    <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded flex items-center gap-1 ${
                      activeNote.status === "FINAL" ? "bg-emerald-50 text-emerald-700 border border-emerald-200" :
                      activeNote.status === "AMENDED" ? "bg-purple-50 text-purple-700 border border-purple-200" :
                      "bg-amber-50 text-amber-700 border border-amber-200"
                    }`}>
                      {activeNote.status === "FINAL" && <Lock className="w-3 h-3" />}
                      Note v{activeNote.version} • {activeNote.status}
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Dept: <strong className="text-slate-700">{encounter.department_name}</strong> • Visit: <strong className="text-slate-700">{encounter.encounter_type}</strong>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {encounter.status === "IN_PROGRESS" && (
                <button
                  onClick={handleCompleteEncounter}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition flex items-center gap-2 shadow-sm"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Complete Encounter</span>
                </button>
              )}
            </div>
          </div>
        )}

        {statusMsg && (
          <div className={`p-4 rounded-xl text-xs flex items-center gap-2 border ${
            statusMsg.type === "success" ? "bg-emerald-50 text-emerald-800 border-emerald-200" : "bg-rose-50 text-rose-800 border-rose-200"
          }`}>
            {statusMsg.type === "success" ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
            <span>{statusMsg.text}</span>
          </div>
        )}

        {/* Nurse Vitals Review Banner */}
        {vitals.length > 0 && (
          <div className="bg-emerald-50/70 border border-emerald-200 rounded-2xl p-5 shadow-sm space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-xs font-bold text-emerald-900 flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-600" />
                <span>Nurse Intake & Vitals Assessment</span>
              </span>
              <span className="text-[11px] text-emerald-700">
                Recorded by {vitals[0].recorded_by_name || "Nurse"} • {new Date(vitals[0].created_at).toLocaleTimeString()}
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
              <div className="bg-white/80 p-2.5 rounded-xl border border-emerald-100">
                <span className="text-[10px] text-slate-500 block">BP</span>
                <strong className="text-slate-800">{vitals[0].systolic_bp}/{vitals[0].diastolic_bp} mmHg</strong>
              </div>
              <div className="bg-white/80 p-2.5 rounded-xl border border-emerald-100">
                <span className="text-[10px] text-slate-500 block">Heart Rate</span>
                <strong className="text-slate-800">{vitals[0].heart_rate} bpm</strong>
              </div>
              <div className="bg-white/80 p-2.5 rounded-xl border border-emerald-100">
                <span className="text-[10px] text-slate-500 block">Temperature</span>
                <strong className="text-slate-800">{vitals[0].temperature_c} °C</strong>
              </div>
              <div className="bg-white/80 p-2.5 rounded-xl border border-emerald-100">
                <span className="text-[10px] text-slate-500 block">SpO2</span>
                <strong className="text-slate-800">{vitals[0].oxygen_saturation} %</strong>
              </div>
              <div className="bg-white/80 p-2.5 rounded-xl border border-emerald-100">
                <span className="text-[10px] text-slate-500 block">BMI (calc)</span>
                <strong className="text-slate-800">{vitals[0].bmi || "N/A"}</strong>
              </div>
            </div>
            {vitals[0].notes && (
              <p className="text-xs text-emerald-800 italic">"{vitals[0].notes}"</p>
            )}
          </div>
        )}

        {/* Clinical Note SOAP Editor */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
          <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3 border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <FileText className="w-4 h-4 text-medicore-600" />
                <span>SOAP Clinical Documentation</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">Authoritative physician documentation with versioning and immutability safeguards.</p>
            </div>

            <div className="flex items-center gap-2">
              {!isLocked ? (
                <>
                  <button
                    type="button"
                    onClick={handleSaveDraft}
                    disabled={isSaving}
                    className="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold px-4 py-2 rounded-xl transition flex items-center gap-2"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>Save Draft</span>
                  </button>
                  {activeNote && activeNote.status === "DRAFT" && (
                    <button
                      type="button"
                      onClick={() => setShowFinalizeModal(true)}
                      className="bg-medicore-600 hover:bg-medicore-700 text-white text-xs font-bold px-4 py-2 rounded-xl transition flex items-center gap-2 shadow-sm"
                    >
                      <Lock className="w-3.5 h-3.5" />
                      <span>Finalize Note</span>
                    </button>
                  )}
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => setShowAmendModal(true)}
                  className="bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold px-4 py-2 rounded-xl transition flex items-center gap-2 shadow-sm"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Amend Finalized Note</span>
                </button>
              )}
            </div>
          </div>

          <form onSubmit={handleSaveDraft} className="space-y-6">
            {/* Subjective */}
            <div className="space-y-4">
              <h3 className="text-xs font-bold text-indigo-700 uppercase tracking-wider bg-indigo-50 px-3 py-1 rounded-lg inline-block">
                1. Subjective (Patient Narrative)
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Chief Presenting Complaint</label>
                  <input
                    type="text"
                    disabled={isLocked}
                    value={chiefComplaint}
                    onChange={e => setChiefComplaint(e.target.value)}
                    placeholder="E.g. Recurrent chest tightness on exertion"
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500 disabled:bg-slate-50 disabled:text-slate-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Associated Symptoms</label>
                  <input
                    type="text"
                    disabled={isLocked}
                    value={symptoms}
                    onChange={e => setSymptoms(e.target.value)}
                    placeholder="E.g. Dyspnea, palpitations, diaphoresis"
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500 disabled:bg-slate-50 disabled:text-slate-500"
                  />
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">History of Present Illness (HPI)</label>
                <textarea
                  rows={2}
                  disabled={isLocked}
                  value={hpi}
                  onChange={e => setHpi(e.target.value)}
                  placeholder="Chronological timeline of symptoms, aggravating and relieving factors..."
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500 disabled:bg-slate-50 disabled:text-slate-500"
                />
              </div>
            </div>

            {/* Objective */}
            <div className="space-y-4 pt-4 border-t border-slate-100">
              <h3 className="text-xs font-bold text-emerald-700 uppercase tracking-wider bg-emerald-50 px-3 py-1 rounded-lg inline-block">
                2. Objective (Physician Findings)
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Physical Examination Findings</label>
                  <textarea
                    rows={2}
                    disabled={isLocked}
                    value={examFindings}
                    onChange={e => setExamFindings(e.target.value)}
                    placeholder="Cardiovascular: S1/S2 normal, no murmurs. Lungs: Clear to auscultation."
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500 disabled:bg-slate-50 disabled:text-slate-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Clinical Observations & Signs</label>
                  <textarea
                    rows={2}
                    disabled={isLocked}
                    value={observations}
                    onChange={e => setObservations(e.target.value)}
                    placeholder="Patient appears comfortable, no acute distress noted."
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500 disabled:bg-slate-50 disabled:text-slate-500"
                  />
                </div>
              </div>
            </div>

            {/* Assessment */}
            <div className="space-y-4 pt-4 border-t border-slate-100">
              <h3 className="text-xs font-bold text-amber-700 uppercase tracking-wider bg-amber-50 px-3 py-1 rounded-lg inline-block">
                3. Assessment & Working Formulation
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Clinical Assessment</label>
                  <textarea
                    rows={2}
                    disabled={isLocked}
                    value={assessment}
                    onChange={e => setAssessment(e.target.value)}
                    placeholder="Primary diagnostic impression and synthesized assessment..."
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500 disabled:bg-slate-50 disabled:text-slate-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Differential Diagnoses</label>
                  <textarea
                    rows={2}
                    disabled={isLocked}
                    value={diffDiag}
                    onChange={e => setDiffDiag(e.target.value)}
                    placeholder="Alternative conditions under active clinical evaluation..."
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500 disabled:bg-slate-50 disabled:text-slate-500"
                  />
                </div>
              </div>
            </div>

            {/* Plan */}
            <div className="space-y-4 pt-4 border-t border-slate-100">
              <h3 className="text-xs font-bold text-sky-700 uppercase tracking-wider bg-sky-50 px-3 py-1 rounded-lg inline-block">
                4. Plan & Instructions
              </h3>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Treatment Plan</label>
                <textarea
                  rows={2}
                  disabled={isLocked}
                  value={treatmentPlan}
                  onChange={e => setTreatmentPlan(e.target.value)}
                  placeholder="Medical management, therapeutic instructions, recommended interventions..."
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500 disabled:bg-slate-50 disabled:text-slate-500"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Patient Precautions & Safety-Net</label>
                  <textarea
                    rows={2}
                    disabled={isLocked}
                    value={patientInstructions}
                    onChange={e => setPatientInstructions(e.target.value)}
                    placeholder="Direct patient instructions, red-flag warnings..."
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500 disabled:bg-slate-50 disabled:text-slate-500"
                  />
                </div>
                <div className="space-y-3">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-700">Follow-up Date</label>
                    <input
                      type="date"
                      disabled={isLocked}
                      value={followUpDate}
                      onChange={e => setFollowUpDate(e.target.value)}
                      className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500 disabled:bg-slate-50 disabled:text-slate-500"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-700">Follow-up Instructions</label>
                    <input
                      type="text"
                      disabled={isLocked}
                      value={followUpInstructions}
                      onChange={e => setFollowUpInstructions(e.target.value)}
                      placeholder="E.g. Return in 2 weeks with repeat lipid profile"
                      className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500 disabled:bg-slate-50 disabled:text-slate-500"
                    />
                  </div>
                </div>
              </div>
            </div>
          </form>
        </div>

        {/* Structured Diagnoses Block */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex justify-between items-center border-b border-slate-100 pb-3">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-rose-500" />
              <span>Structured Clinical Diagnoses ({diagnoses.length})</span>
            </h3>
          </div>

          {/* Add Diagnosis Form */}
          <form onSubmit={handleAddDiagnosis} className="grid grid-cols-1 sm:grid-cols-4 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-100">
            <div className="space-y-1 sm:col-span-2">
              <label className="text-[11px] font-semibold text-slate-700">Diagnosis Description</label>
              <input
                type="text"
                required
                value={diagName}
                onChange={e => setDiagName(e.target.value)}
                placeholder="E.g. Essential (primary) hypertension"
                className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-medicore-500"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-700">Code (Optional)</label>
              <input
                type="text"
                value={diagCode}
                onChange={e => setDiagCode(e.target.value)}
                placeholder="E.g. I10"
                className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-medicore-500 font-mono"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-700">Type</label>
              <select
                value={diagType}
                onChange={e => setDiagType(e.target.value as any)}
                className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-medicore-500 bg-white"
              >
                <option value="PRIMARY">PRIMARY</option>
                <option value="SECONDARY">SECONDARY</option>
                <option value="WORKING">WORKING</option>
                <option value="SUSPECTED">SUSPECTED</option>
              </select>
            </div>
            <div className="sm:col-span-4 flex justify-end">
              <button
                type="submit"
                className="bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold px-4 py-2 rounded-xl transition flex items-center gap-1.5 shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Diagnosis</span>
              </button>
            </div>
          </form>

          {/* List of existing diagnoses */}
          {diagnoses.length > 0 && (
            <div className="space-y-2 pt-2">
              {diagnoses.map(d => (
                <div key={d.id} className="p-3 bg-white border border-slate-200 rounded-xl flex justify-between items-center text-xs">
                  <div>
                    <span className={`text-[10px] font-extrabold uppercase px-1.5 py-0.5 rounded mr-2 ${
                      d.type === "PRIMARY" ? "bg-rose-50 text-rose-700" : "bg-slate-100 text-slate-700"
                    }`}>
                      {d.type}
                    </span>
                    <strong className="text-slate-800">{d.name}</strong>
                    {d.code && (
                      <span className="ml-2 font-mono text-[10px] text-slate-500 bg-slate-100 px-1 py-0.5 rounded">
                        {d.code}
                      </span>
                    )}
                  </div>
                  <span className="text-[11px] text-slate-400">
                    Dr. {d.doctor_name || "Physician"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Step 4 Laboratory Orders & Diagnostic Results */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-3 border-b border-slate-100">
            <div>
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <FlaskConical className="w-4 h-4 text-purple-600" />
                <span>Laboratory Orders & Diagnostic Results</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Place clinical pathology orders, track specimen accessions, and verify analyzer test results.
              </p>
            </div>
            {encounter?.status !== "COMPLETED" && (
              <button
                type="button"
                onClick={() => setShowLabModal(true)}
                className="bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold px-3.5 py-2 rounded-xl transition flex items-center gap-1.5 shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Order Lab Tests</span>
              </button>
            )}
          </div>

          {labOrders.length === 0 ? (
            <div className="text-center py-8 bg-slate-50 rounded-xl border border-dashed border-slate-200">
              <TestTube2 className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-xs text-slate-500 font-medium">No laboratory orders placed for this encounter.</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Order hematology, biochemistry, or metabolic panels above.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {labOrders.map(order => (
                <div key={order.id} className="border border-slate-200 rounded-xl overflow-hidden bg-slate-50/50">
                  {/* Order Bar */}
                  <div className="bg-slate-100/80 px-4 py-3 flex flex-wrap justify-between items-center gap-2 border-b border-slate-200">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs font-bold text-slate-900">{order.order_number}</span>
                      <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded ${
                        order.priority === "STAT" ? "bg-rose-100 text-rose-800 border border-rose-300 animate-pulse" :
                        order.priority === "URGENT" ? "bg-amber-100 text-amber-800 border border-amber-300" :
                        "bg-slate-200 text-slate-700"
                      }`}>
                        {order.priority}
                      </span>
                      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                        order.status === "COMPLETED" ? "bg-emerald-100 text-emerald-800" :
                        order.status === "CANCELLED" ? "bg-slate-200 text-slate-500 line-through" :
                        order.status === "PROCESSING" ? "bg-blue-100 text-blue-800" :
                        "bg-amber-100 text-amber-800"
                      }`}>
                        {order.status}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-500">
                      Ordered: {new Date(order.ordered_at).toLocaleString()}
                    </div>
                  </div>

                  {order.clinical_indication && (
                    <div className="px-4 py-2 bg-white text-xs text-slate-600 border-b border-slate-100">
                      <span className="font-semibold text-slate-700">Indication:</span> {order.clinical_indication}
                    </div>
                  )}

                  {/* Samples Badge Row */}
                  {order.samples && order.samples.length > 0 && (
                    <div className="px-4 py-2 bg-purple-50/40 border-b border-purple-100 flex items-center gap-2 flex-wrap text-xs">
                      <span className="text-[11px] font-bold text-purple-900 flex items-center gap-1">
                        <TestTube2 className="w-3.5 h-3.5 text-purple-600" />
                        <span>Specimens:</span>
                      </span>
                      {order.samples.map(s => (
                        <span key={s.id} className="font-mono text-[10px] bg-white border border-purple-200 text-purple-800 px-2 py-0.5 rounded-md">
                          {s.accession_number} ({s.specimen_type} - {s.status})
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Order Items Table */}
                  <div className="p-4 bg-white space-y-3">
                    {order.items.map(item => {
                      const res = item.result;
                      return (
                        <div key={item.id} className="p-3 rounded-xl border border-slate-100 bg-slate-50/30 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                          <div>
                            <div className="flex items-center gap-2">
                              <strong className="text-xs font-bold text-slate-900">{item.test_name}</strong>
                              <span className="font-mono text-[10px] bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded">
                                {item.test_code}
                              </span>
                              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                                item.status === "COMPLETED" ? "bg-emerald-50 text-emerald-700" :
                                item.status === "PROCESSING" ? "bg-blue-50 text-blue-700" :
                                item.status === "CANCELLED" ? "bg-slate-100 text-slate-400 line-through" :
                                "bg-amber-50 text-amber-700"
                              }`}>
                                {item.status}
                              </span>
                            </div>
                            {item.notes && (
                              <p className="text-[11px] text-slate-500 mt-1">{item.notes}</p>
                            )}
                          </div>

                          {/* Result details if entered */}
                          {res ? (
                            <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-end">
                              <div className="text-right">
                                <div className="flex items-center gap-1.5 justify-end">
                                  <span className="text-sm font-extrabold text-slate-900">{res.value}</span>
                                  {res.unit && <span className="text-xs text-slate-500 font-medium">{res.unit}</span>}
                                  
                                  {/* Abnormal Flag Badge */}
                                  <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded flex items-center gap-1 ${
                                    res.abnormal_flag === "CRITICAL" ? "bg-rose-100 text-rose-800 border border-rose-300 animate-pulse" :
                                    res.abnormal_flag === "HIGH" || res.abnormal_flag === "LOW" || res.abnormal_flag === "ABNORMAL" ? "bg-amber-100 text-amber-800 border border-amber-200" :
                                    "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                  }`}>
                                    {res.abnormal_flag === "CRITICAL" && <AlertTriangle className="w-3 h-3" />}
                                    {res.abnormal_flag}
                                  </span>
                                </div>
                                {res.reference_range && (
                                  <span className="text-[10px] text-slate-400 block mt-0.5">Ref: {res.reference_range}</span>
                                )}
                                {res.amendment_reason && (
                                  <span className="text-[10px] text-purple-600 block italic">Amended: {res.amendment_reason}</span>
                                )}
                              </div>

                              {/* Physician Action: Verify or Amend */}
                              <div className="flex items-center gap-1">
                                {res.status === "ENTERED" && (
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setSelectedResult(res);
                                      setShowVerifyModal(true);
                                    }}
                                    className="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-1 shadow-sm"
                                  >
                                    <ShieldCheck className="w-3.5 h-3.5" />
                                    <span>Verify</span>
                                  </button>
                                )}
                                {res.status === "FINAL" && (
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setSelectedResult(res);
                                      setAmendResultVal(res.value);
                                      setAmendResultNumeric(res.numeric_value ? String(res.numeric_value) : "");
                                      setAmendResultFlag(res.abnormal_flag);
                                      setShowAmendResultModal(true);
                                    }}
                                    className="px-2.5 py-1.5 bg-purple-100 hover:bg-purple-200 text-purple-800 rounded-lg text-xs font-bold transition flex items-center gap-1"
                                  >
                                    <RefreshCw className="w-3.5 h-3.5" />
                                    <span>Amend</span>
                                  </button>
                                )}
                              </div>
                            </div>
                          ) : (
                            <div className="text-xs text-slate-400 italic">
                              Awaiting laboratory specimen processing
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Finalize Confirmation Modal */}
        {showFinalizeModal && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
              <div className="flex items-center gap-3 text-amber-600">
                <Lock className="w-6 h-6" />
                <h3 className="font-bold text-base text-slate-900">Finalize Clinical Note?</h3>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Once finalized, this clinical note will become an immutable part of the patient's longitudinal record. Normal editing will be strictly disabled. Any subsequent changes will require an attributable clinical amendment.
              </p>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowFinalizeModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleFinalize}
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-medicore-600 hover:bg-medicore-700 text-white transition shadow-sm"
                >
                  Confirm & Finalize
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Amend Modal */}
        {showAmendModal && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4">
              <div className="flex items-center gap-3 text-purple-600">
                <RefreshCw className="w-6 h-6" />
                <h3 className="font-bold text-base text-slate-900">Author Clinical Amendment</h3>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                This will preserve version {activeNote?.version} unchanged and create version {(activeNote?.version || 1) + 1} with your attributable clinical reason.
              </p>
              <form onSubmit={handleAmend} className="space-y-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Clinical Reason for Amendment *</label>
                  <textarea
                    rows={3}
                    required
                    value={amendReason}
                    onChange={e => setAmendReason(e.target.value)}
                    placeholder="Specify reason for revision (e.g. Added laboratory findings, updated dosage)..."
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowAmendModal(false)}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-xl text-xs font-bold bg-purple-600 hover:bg-purple-700 text-white transition shadow-sm"
                  >
                    Submit Amendment
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Step 4: Create Lab Order Modal */}
        {showLabModal && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-2xl border border-slate-200 space-y-4 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center gap-3 text-purple-600">
                <FlaskConical className="w-6 h-6" />
                <div>
                  <h3 className="font-bold text-base text-slate-900">Place Laboratory Pathology Order</h3>
                  <p className="text-xs text-slate-500">Select diagnostic tests and specify clinical indications.</p>
                </div>
              </div>

              <form onSubmit={handleCreateLabOrder} className="space-y-4 pt-2">
                {/* Priority Selection */}
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-700">Order Priority *</label>
                  <div className="grid grid-cols-3 gap-2">
                    {(["ROUTINE", "URGENT", "STAT"] as LabOrderPriority[]).map(p => (
                      <button
                        key={p}
                        type="button"
                        onClick={() => setLabPriority(p)}
                        className={`py-2 text-xs font-bold rounded-xl border transition ${
                          labPriority === p
                            ? p === "STAT" ? "bg-rose-50 border-rose-500 text-rose-700" :
                              p === "URGENT" ? "bg-amber-50 border-amber-500 text-amber-700" :
                              "bg-purple-50 border-purple-500 text-purple-700"
                            : "border-slate-200 text-slate-600 hover:bg-slate-50"
                        }`}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Test Catalog Selection */}
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-700 flex justify-between items-center">
                    <span>Select Laboratory Tests ({selectedTestIds.length} selected) *</span>
                    <span className="text-[11px] font-normal text-slate-400">At least one test required</span>
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-48 overflow-y-auto p-2 border border-slate-200 rounded-xl bg-slate-50/50">
                    {catalogTests.map(t => {
                      const isSelected = selectedTestIds.includes(t.id);
                      return (
                        <div
                          key={t.id}
                          onClick={() => {
                            setSelectedTestIds(prev => 
                              isSelected ? prev.filter(id => id !== t.id) : [...prev, t.id]
                            );
                          }}
                          className={`p-2.5 rounded-lg border text-xs cursor-pointer transition flex items-start gap-2 ${
                            isSelected ? "bg-purple-50 border-purple-300 shadow-xs" : "bg-white border-slate-200 hover:border-slate-300"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => {}}
                            className="mt-0.5 rounded text-purple-600 focus:ring-purple-500"
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between">
                              <strong className="text-slate-800 text-[11px] truncate">{t.name}</strong>
                              <span className="font-mono text-[9px] bg-slate-100 text-slate-600 px-1 rounded ml-1">{t.code}</span>
                            </div>
                            <span className="text-[10px] text-slate-400 block mt-0.5">
                              {t.specimen_type} {t.turnaround_hours ? `• ~${t.turnaround_hours}h` : ""}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Clinical Indication */}
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-700">Clinical Indication / Diagnosis Rationale</label>
                  <input
                    type="text"
                    value={labIndication}
                    onChange={e => setLabIndication(e.target.value)}
                    placeholder="e.g. Diagnostic evaluation for chronic fatigue and microcytic anemia..."
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>

                {/* Notes */}
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-700">Instructions / Notes for Laboratory</label>
                  <input
                    type="text"
                    value={labNotes}
                    onChange={e => setLabNotes(e.target.value)}
                    placeholder="e.g. Fasting specimen, protect from light..."
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setShowLabModal(false)}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={selectedTestIds.length === 0 || isSubmittingLab}
                    className="px-5 py-2 rounded-xl text-xs font-bold bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white transition shadow-sm"
                  >
                    {isSubmittingLab ? "Placing Order..." : "Confirm & Place Order"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Step 4: Verify Result Modal */}
        {showVerifyModal && selectedResult && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
              <div className="flex items-center gap-3 text-emerald-600">
                <ShieldCheck className="w-6 h-6" />
                <div>
                  <h3 className="font-bold text-base text-slate-900">Verify Laboratory Result</h3>
                  <p className="text-xs text-slate-500">Finalize analyzer findings into immutable medical record.</p>
                </div>
              </div>

              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-500">Test:</span>
                  <strong className="text-slate-900">{selectedResult.test_name} ({selectedResult.test_code})</strong>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Reported Value:</span>
                  <div className="flex items-center gap-1.5">
                    <strong className="text-base text-slate-900">{selectedResult.value} {selectedResult.unit}</strong>
                    <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded ${
                      selectedResult.abnormal_flag === "CRITICAL" ? "bg-rose-100 text-rose-800" :
                      selectedResult.abnormal_flag !== "NORMAL" ? "bg-amber-100 text-amber-800" :
                      "bg-emerald-100 text-emerald-800"
                    }`}>
                      {selectedResult.abnormal_flag}
                    </span>
                  </div>
                </div>
                {selectedResult.reference_range && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Reference Range:</span>
                    <span className="text-slate-700 font-mono">{selectedResult.reference_range}</span>
                  </div>
                )}
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Verification Comments (Optional)</label>
                <textarea
                  rows={2}
                  value={verifyComments}
                  onChange={e => setVerifyComments(e.target.value)}
                  placeholder="Physician notes or confirmatory remarks..."
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowVerifyModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleVerifyResult}
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white transition shadow-sm"
                >
                  Confirm & Finalize Result
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Amend Result Modal */}
        {showAmendResultModal && selectedResult && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
              <div className="flex items-center gap-3 text-purple-600">
                <RefreshCw className="w-6 h-6" />
                <div>
                  <h3 className="font-bold text-base text-slate-900">Amend Finalized Laboratory Result</h3>
                  <p className="text-xs text-slate-500">Preserves original result and issues new immutable version.</p>
                </div>
              </div>

              <form onSubmit={handleAmendResult} className="space-y-3 pt-1">
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 text-xs">
                  <span className="text-slate-500 block">Original Value (Preserved):</span>
                  <strong className="text-slate-900 text-sm">{selectedResult.value} {selectedResult.unit} ({selectedResult.abnormal_flag})</strong>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-700">Corrected Value *</label>
                    <input
                      type="text"
                      required
                      value={amendResultVal}
                      onChange={e => setAmendResultVal(e.target.value)}
                      placeholder="e.g. 14.8"
                      className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-700">Abnormal Flag</label>
                    <select
                      value={amendResultFlag}
                      onChange={e => setAmendResultFlag(e.target.value as AbnormalFlag)}
                      className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white"
                    >
                      <option value="NORMAL">NORMAL</option>
                      <option value="HIGH">HIGH</option>
                      <option value="LOW">LOW</option>
                      <option value="ABNORMAL">ABNORMAL</option>
                      <option value="CRITICAL">CRITICAL</option>
                    </select>
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Clinical Reason for Amendment * (Required)</label>
                  <textarea
                    rows={3}
                    required
                    value={amendResultReason}
                    onChange={e => setAmendResultReason(e.target.value)}
                    placeholder="Specify justification (e.g. Analyzer recalibration offset corrected per QA protocol)..."
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowAmendResultModal(false)}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-xl text-xs font-bold bg-purple-600 hover:bg-purple-700 text-white transition shadow-sm"
                  >
                    Publish Amendment
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </DoctorLayout>
  );
}
