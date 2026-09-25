"use client";

import React, { useState } from "react";
import { DoctorLayout } from "@/components/layout/doctor-layout";
import { api } from "@/lib/api";
import { 
  Sparkles, FileText, CheckCircle2, AlertCircle, 
  Stethoscope, ShieldCheck, PenTool, RefreshCw, Tag 
} from "lucide-react";

export default function DoctorScribePage() {
  const [patientId, setPatientId] = useState("101");
  const [encounterId, setEncounterId] = useState("501");
  const [vitalsSummary, setVitalsSummary] = useState("BP 128/82, HR 74, SpO2 98%, Temp 36.8C");
  const [transcript, setTranscript] = useState(
    "Doctor: Good morning, what brings you in today?\n" +
    "Patient: I have had persistent throbbing headache and intermittent fever for the last three days.\n" +
    "Doctor: Any history of high blood pressure or diabetes?\n" +
    "Patient: Yes, I was diagnosed with primary hypertension two years ago.\n" +
    "Doctor: Lungs are clear to auscultation bilaterally. Heart has regular rate and rhythm.\n" +
    "Doctor: I will prescribe acetaminophen 500mg tablet BID for fever and order a routine complete metabolic panel."
  );

  const [isLoading, setIsLoading] = useState(false);
  const [soapData, setSoapData] = useState<any>(null);
  const [isSigning, setIsSigning] = useState(false);
  const [attestationSuccess, setAttestationSuccess] = useState<string | null>(null);

  const handleGenerateSoap = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setAttestationSuccess(null);

    try {
      const res = await api.post<any>("/scribe/generate-soap", {
        patient_id: parseInt(patientId),
        encounter_id: parseInt(encounterId),
        raw_transcript: transcript,
        vitals_summary: vitalsSummary
      });
      setSoapData(res);
    } catch (err: any) {
      alert(err.message || "Failed to generate AI SOAP note.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignSoapNote = async () => {
    if (!soapData) return;
    setIsSigning(true);
    try {
      const res = await api.post<any>("/scribe/attest-soap", {
        encounter_id: parseInt(encounterId),
        attending_physician_id: 1,
        final_soap: soapData.soap,
        physician_signature: "Dr. Chen, MD (Cardiology)"
      });
      setAttestationSuccess(res.signature_hash);
      setSoapData((prev: any) => ({ ...prev, status: "PHYSICIAN_SIGNED" }));
    } catch (err: any) {
      alert(err.message || "Failed to sign SOAP note.");
    } finally {
      setIsSigning(false);
    }
  };

  return (
    <DoctorLayout>
      <div className="p-8 max-w-6xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <Sparkles className="w-8 h-8 text-indigo-400" />
            Ambient Clinical AI Scribe & SOAP Note Generator
          </h1>
          <p className="text-zinc-400 mt-1">
            Converts physician-patient dialogue transcripts into structured SOAP notes with automated ICD-10 diagnostic coding.
          </p>
        </div>

        {attestationSuccess && (
          <div className="p-4 bg-emerald-950/40 border border-emerald-800 rounded-xl text-emerald-200 flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <div>
              <div className="font-semibold text-emerald-300">SOAP Note Cryptographically Authenticated</div>
              <div className="text-xs text-emerald-400 font-mono mt-0.5">Committed: {attestationSuccess}</div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Transcript Input */}
          <div className="lg:col-span-6 bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl space-y-5">
            <form onSubmit={handleGenerateSoap} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">
                    Patient ID
                  </label>
                  <input
                    type="number"
                    required
                    value={patientId}
                    onChange={(e) => setPatientId(e.target.value)}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">
                    Encounter ID
                  </label>
                  <input
                    type="number"
                    required
                    value={encounterId}
                    onChange={(e) => setEncounterId(e.target.value)}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2 text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">
                  Vitals Telemetry Summary
                </label>
                <input
                  type="text"
                  value={vitalsSummary}
                  onChange={(e) => setVitalsSummary(e.target.value)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2 text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">
                  Encounter Conversation Transcript
                </label>
                <textarea
                  required
                  rows={8}
                  value={transcript}
                  onChange={(e) => setTranscript(e.target.value)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-xl p-3 text-white font-mono text-xs leading-relaxed focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-semibold rounded-xl shadow-lg transition-all flex items-center justify-center gap-2"
              >
                {isLoading ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
                Generate Structured SOAP Note
              </button>
            </form>
          </div>

          {/* Generated SOAP Display */}
          <div className="lg:col-span-6 space-y-6">
            {soapData ? (
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl space-y-6">
                <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
                  <div className="flex items-center gap-2">
                    <FileText className="w-5 h-5 text-indigo-400" />
                    <h3 className="font-bold text-white text-lg">Clinical SOAP Note</h3>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-bold border ${
                    soapData.status === "PHYSICIAN_SIGNED"
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                      : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                  }`}>
                    {soapData.status}
                  </span>
                </div>

                <div className="space-y-4 text-sm">
                  {/* S */}
                  <div className="p-3 bg-zinc-800/50 rounded-xl border border-zinc-700/40">
                    <span className="font-bold text-indigo-400 mr-2">S (Subjective):</span>
                    <span className="text-zinc-200">{soapData.soap.subjective.chief_complaint}</span>
                  </div>

                  {/* O */}
                  <div className="p-3 bg-zinc-800/50 rounded-xl border border-zinc-700/40">
                    <span className="font-bold text-indigo-400 mr-2">O (Objective):</span>
                    <span className="text-zinc-200">{soapData.soap.objective.vital_signs} | {soapData.soap.objective.physical_examination}</span>
                  </div>

                  {/* A */}
                  <div className="p-3 bg-zinc-800/50 rounded-xl border border-zinc-700/40">
                    <div className="font-bold text-indigo-400 mb-1">A (Assessment & ICD-10):</div>
                    <div className="text-zinc-200">{soapData.soap.assessment.primary_diagnosis}</div>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {soapData.coding.suggested_icd10.map((code: any, idx: number) => (
                        <span key={idx} className="px-2 py-1 bg-indigo-950/60 border border-indigo-700/50 rounded-md text-xs text-indigo-300 flex items-center gap-1">
                          <Tag className="w-3 h-3" />
                          <strong>{code.code}:</strong> {code.description}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* P */}
                  <div className="p-3 bg-zinc-800/50 rounded-xl border border-zinc-700/40">
                    <div className="font-bold text-indigo-400 mb-1">P (Plan & CPT):</div>
                    <div className="text-zinc-200">{soapData.soap.plan.patient_instructions}</div>
                    <div className="text-xs text-zinc-400 mt-1">Suggested CPT: {soapData.coding.suggested_cpt.code} ({soapData.coding.suggested_cpt.description})</div>
                  </div>
                </div>

                {soapData.status !== "PHYSICIAN_SIGNED" && (
                  <button
                    onClick={handleSignSoapNote}
                    disabled={isSigning}
                    className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-xl shadow-lg transition-all flex items-center justify-center gap-2"
                  >
                    {isSigning ? <RefreshCw className="w-5 h-5 animate-spin" /> : <PenTool className="w-5 h-5" />}
                    Attest & Sign Clinical Note
                  </button>
                )}
              </div>
            ) : (
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 text-center text-zinc-500 shadow-xl space-y-3">
                <Stethoscope className="w-12 h-12 text-zinc-600 mx-auto" />
                <div className="font-medium text-zinc-400">Ready for Ambient Dialogue</div>
                <div className="text-xs text-zinc-500">
                  Input conversational encounter transcript on the left to generate structured SOAP notes and ICD-10 suggestions.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </DoctorLayout>
  );
}
