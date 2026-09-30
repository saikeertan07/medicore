"use client";

import React, { useState } from "react";
import { NurseLayout } from "@/components/layout/nurse-layout";
import { api } from "@/lib/api";
import { 
  AlertTriangle, HeartPulse, ShieldAlert, Activity, CheckCircle, 
  Flame, Thermometer, Stethoscope, RefreshCw 
} from "lucide-react";

export default function NurseTriagePage() {
  const [patientId, setPatientId] = useState("");
  const [chiefComplaint, setChiefComplaint] = useState("");
  const [anticipatedResources, setAnticipatedResources] = useState(2);

  // Vitals
  const [respRate, setRespRate] = useState(16);
  const [spo2, setSpo2] = useState(98);
  const [onOxygen, setOnOxygen] = useState(false);
  const [systolicBp, setSystolicBp] = useState(120);
  const [heartRate, setHeartRate] = useState(76);
  const [consciousness, setConsciousness] = useState("ALERT");
  const [temperature, setTemperature] = useState(37.0);

  const [isLoading, setIsLoading] = useState(false);
  const [triageResult, setTriageResult] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleEvaluateTriage = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);

    try {
      const payload = {
        patient_id: patientId ? parseInt(patientId) : undefined,
        chief_complaint: chiefComplaint || "Emergency intake evaluation",
        anticipated_resources: anticipatedResources,
        vitals: {
          respiration_rate: Number(respRate),
          spo2: Number(spo2),
          on_oxygen: onOxygen,
          systolic_bp: Number(systolicBp),
          heart_rate: Number(heartRate),
          consciousness: consciousness,
          temperature: Number(temperature)
        }
      };

      const res = await api.post<any>("/triage/assess", payload);
      setTriageResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to calculate emergency triage assessment.");
    } finally {
      setIsLoading(false);
    }
  };

  const getRiskBadgeColor = (risk: string) => {
    switch (risk) {
      case "HIGH":
        return "bg-red-500/10 text-red-400 border-red-500/30";
      case "MEDIUM":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      default:
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
    }
  };

  return (
    <NurseLayout>
      <div className="p-8 max-w-6xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <ShieldAlert className="w-8 h-8 text-red-400" />
            Emergency Triage & NEWS2 Deterioration Engine
          </h1>
          <p className="text-zinc-400 mt-1">
            Real-time Emergency Severity Index (ESI Level 1-5) and Royal College of Physicians NEWS2 clinical scoring.
          </p>
        </div>

        {errorMsg && (
          <div className="p-4 bg-red-950/40 border border-red-800 rounded-xl text-red-200 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Triage Form */}
          <div className="lg:col-span-7 bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl">
            <form onSubmit={handleEvaluateTriage} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                    Patient ID (Optional)
                  </label>
                  <input
                    type="number"
                    value={patientId}
                    onChange={(e) => setPatientId(e.target.value)}
                    placeholder="e.g. 102"
                    className="w-full bg-zinc-800/80 border border-zinc-700 rounded-xl px-4 py-2.5 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                    Anticipated Resources (ESI)
                  </label>
                  <select
                    value={anticipatedResources}
                    onChange={(e) => setAnticipatedResources(parseInt(e.target.value))}
                    className="w-full bg-zinc-800/80 border border-zinc-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value={0}>0 Resources (Routine/Prescription)</option>
                    <option value={1}>1 Resource (X-ray or simple sutures)</option>
                    <option value={2}>2+ Resources (Labs, IV, CT/MRI, multi-specialty)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                  Chief Complaint / Trauma Presentation
                </label>
                <textarea
                  required
                  rows={2}
                  value={chiefComplaint}
                  onChange={(e) => setChiefComplaint(e.target.value)}
                  placeholder="e.g. Acute severe substernal chest pain radiating to left arm with diaphoresis..."
                  className="w-full bg-zinc-800/80 border border-zinc-700 rounded-xl p-3 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              {/* Vitals Grid */}
              <div className="border-t border-zinc-800 pt-6">
                <h3 className="text-sm font-semibold text-zinc-200 mb-4 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-emerald-400" />
                  Physiological Vital Telemetry
                </h3>
                
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs text-zinc-400 mb-1">Respiration (bpm)</label>
                    <input
                      type="number"
                      required
                      value={respRate}
                      onChange={(e) => setRespRate(parseInt(e.target.value) || 0)}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-zinc-400 mb-1">SpO2 (%)</label>
                    <input
                      type="number"
                      required
                      value={spo2}
                      onChange={(e) => setSpo2(parseInt(e.target.value) || 0)}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-zinc-400 mb-1">Heart Rate (bpm)</label>
                    <input
                      type="number"
                      required
                      value={heartRate}
                      onChange={(e) => setHeartRate(parseInt(e.target.value) || 0)}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-zinc-400 mb-1">Systolic BP (mmHg)</label>
                    <input
                      type="number"
                      required
                      value={systolicBp}
                      onChange={(e) => setSystolicBp(parseInt(e.target.value) || 0)}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-zinc-400 mb-1">Temperature (°C)</label>
                    <input
                      type="number"
                      step="0.1"
                      required
                      value={temperature}
                      onChange={(e) => setTemperature(parseFloat(e.target.value) || 0)}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-zinc-400 mb-1">Consciousness (AVPU)</label>
                    <select
                      value={consciousness}
                      onChange={(e) => setConsciousness(e.target.value)}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white"
                    >
                      <option value="ALERT">Alert (A)</option>
                      <option value="VOICE">Voice (V)</option>
                      <option value="PAIN">Pain (P)</option>
                      <option value="UNRESPONSIVE">Unresponsive (U)</option>
                    </select>
                  </div>
                </div>

                <div className="mt-4 flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="o2Toggle"
                    checked={onOxygen}
                    onChange={(e) => setOnOxygen(e.target.checked)}
                    className="w-4 h-4 rounded text-emerald-500 bg-zinc-800 border-zinc-700 focus:ring-emerald-500"
                  />
                  <label htmlFor="o2Toggle" className="text-xs text-zinc-300">
                    Patient is on supplemental oxygen therapy
                  </label>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold rounded-xl shadow-lg transition-all flex items-center justify-center gap-2"
              >
                {isLoading ? <RefreshCw className="w-5 h-5 animate-spin" /> : <HeartPulse className="w-5 h-5" />}
                Calculate Emergency Triage & NEWS2
              </button>
            </form>
          </div>

          {/* Clinical Results Display */}
          <div className="lg:col-span-5 space-y-6">
            {triageResult ? (
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl space-y-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-bold text-white">Clinical Assessment</h3>
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getRiskBadgeColor(triageResult.news2.risk_level)}`}>
                    NEWS2: {triageResult.news2.risk_level} RISK
                  </span>
                </div>

                {triageResult.requires_critical_care_alert && (
                  <div className="p-4 bg-red-950/60 border border-red-700 rounded-xl text-red-200 animate-pulse flex items-start gap-3">
                    <Flame className="w-6 h-6 text-red-400 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-bold text-red-300">CRITICAL MET ESCALATION ALERT</div>
                      <div className="text-xs mt-1 text-red-200">
                        Immediate medical emergency team mobilization and critical care consult required.
                      </div>
                    </div>
                  </div>
                )}

                {/* Scores */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-zinc-800/60 rounded-xl border border-zinc-700/50">
                    <div className="text-xs text-zinc-400">Total NEWS2 Score</div>
                    <div className="text-3xl font-extrabold text-white mt-1">
                      {triageResult.news2.total_score} <span className="text-sm font-normal text-zinc-400">/ 20</span>
                    </div>
                  </div>
                  <div className="p-4 bg-zinc-800/60 rounded-xl border border-zinc-700/50">
                    <div className="text-xs text-zinc-400">ESI Triage Category</div>
                    <div className="text-xl font-bold text-emerald-400 mt-1">
                      Level {triageResult.esi.esi_level}
                    </div>
                    <div className="text-xs text-zinc-400 mt-0.5">{triageResult.esi.category}</div>
                  </div>
                </div>

                {/* Protocol */}
                <div className="p-4 bg-zinc-800/40 rounded-xl border border-zinc-700/40 space-y-2">
                  <div className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
                    Clinical Action Protocol
                  </div>
                  <div className="text-sm text-zinc-200 leading-relaxed">
                    {triageResult.news2.clinical_escalation_protocol}
                  </div>
                </div>

                {/* ESI Action */}
                <div className="p-4 bg-zinc-800/40 rounded-xl border border-zinc-700/40 space-y-2">
                  <div className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
                    ESI Resource Recommendation
                  </div>
                  <div className="text-sm text-zinc-200 leading-relaxed">
                    {triageResult.esi.action}
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8 text-center text-zinc-500 shadow-xl space-y-3">
                <Stethoscope className="w-12 h-12 text-zinc-600 mx-auto" />
                <div className="font-medium text-zinc-400">Awaiting Vital Telemetry</div>
                <div className="text-xs text-zinc-500">
                  Enter patient vitals and chief complaint on the left to calculate real-time NEWS2 and ESI triage priority.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </NurseLayout>
  );
}
