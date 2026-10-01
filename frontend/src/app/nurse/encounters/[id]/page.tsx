"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { NurseLayout } from "@/components/layout/nurse-layout";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { Encounter, EncounterVitals } from "@/types";
import { 
  Activity, Heart, Thermometer, User, ArrowLeft, Save, 
  Play, CheckCircle2, AlertCircle, ShieldAlert 
} from "lucide-react";

export default function NurseEncounterPage() {
  const params = useParams();
  const router = useRouter();
  const encounterId = Number(params?.id);
  const { user } = useAuth();

  const [encounter, setEncounter] = useState<Encounter | null>(null);
  const [vitalsHistory, setVitalsHistory] = useState<EncounterVitals[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Form State
  const [temp, setTemp] = useState<string>("37.0");
  const [heartRate, setHeartRate] = useState<string>("72");
  const [respRate, setRespRate] = useState<string>("16");
  const [systolic, setSystolic] = useState<string>("120");
  const [diastolic, setDiastolic] = useState<string>("80");
  const [spo2, setSpo2] = useState<string>("99");
  const [height, setHeight] = useState<string>("175");
  const [weight, setWeight] = useState<string>("70");
  const [painScore, setPainScore] = useState<number>(0);
  const [notes, setNotes] = useState<string>("");

  // Client-side BMI computation for immediate UX
  const computedBmi = React.useMemo(() => {
    const h = parseFloat(height);
    const w = parseFloat(weight);
    if (h > 0 && w > 0) {
      const hM = h / 100;
      return (w / (hM * hM)).toFixed(1);
    }
    return null;
  }, [height, weight]);

  const loadData = () => {
    if (!encounterId) return;
    setIsLoading(true);
    Promise.all([
      api.get<Encounter>(`/encounters/${encounterId}`),
      api.get<EncounterVitals[]>(`/encounters/${encounterId}/vitals`),
    ])
      .then(([enc, vList]) => {
        setEncounter(enc);
        setVitalsHistory(vList);
        if (vList.length > 0) {
          const latest = vList[0];
          if (latest.temperature_c) setTemp(String(latest.temperature_c));
          if (latest.heart_rate) setHeartRate(String(latest.heart_rate));
          if (latest.respiratory_rate) setRespRate(String(latest.respiratory_rate));
          if (latest.systolic_bp) setSystolic(String(latest.systolic_bp));
          if (latest.diastolic_bp) setDiastolic(String(latest.diastolic_bp));
          if (latest.oxygen_saturation) setSpo2(String(latest.oxygen_saturation));
          if (latest.height_cm) setHeight(String(latest.height_cm));
          if (latest.weight_kg) setWeight(String(latest.weight_kg));
          if (latest.pain_score !== undefined && latest.pain_score !== null) setPainScore(latest.pain_score);
          if (latest.notes) setNotes(latest.notes);
        }
      })
      .catch(err => {
        setStatusMsg({ type: "error", text: err.message || "Failed to load encounter." });
      })
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [encounterId]);

  const handleSaveVitals = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setStatusMsg(null);

    const payload = {
      temperature_c: temp ? parseFloat(temp) : undefined,
      heart_rate: heartRate ? parseInt(heartRate) : undefined,
      respiratory_rate: respRate ? parseInt(respRate) : undefined,
      systolic_bp: systolic ? parseInt(systolic) : undefined,
      diastolic_bp: diastolic ? parseInt(diastolic) : undefined,
      oxygen_saturation: spo2 ? parseFloat(spo2) : undefined,
      height_cm: height ? parseFloat(height) : undefined,
      weight_kg: weight ? parseFloat(weight) : undefined,
      pain_score: painScore,
      notes: notes || undefined
    };

    try {
      await api.post(`/encounters/${encounterId}/vitals`, payload);
      setStatusMsg({ type: "success", text: "Vitals intake successfully recorded in clinical record." });
      loadData();
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Failed to record vitals." });
    } finally {
      setIsSaving(false);
    }
  };

  const handleStartEncounter = async () => {
    try {
      await api.post(`/encounters/${encounterId}/start`, {});
      setStatusMsg({ type: "success", text: "Encounter status updated to IN_PROGRESS." });
      loadData();
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Failed to start encounter." });
    }
  };

  return (
    <NurseLayout>
      <div className="space-y-6">
        {/* Navigation back */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => router.push("/nurse/dashboard")}
            className="flex items-center gap-2 text-xs font-semibold text-slate-500 hover:text-slate-800 transition"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Nurse Triage Queue</span>
          </button>
          {encounter && (
            <span className="font-mono text-xs px-3 py-1 rounded-xl bg-slate-100 text-slate-700 font-bold border border-slate-200">
              {encounter.encounter_number}
            </span>
          )}
        </div>

        {/* Patient Banner */}
        {encounter && (
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-teal-50 text-teal-600 flex items-center justify-center font-bold text-lg border border-teal-100">
                <User className="w-6 h-6" />
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
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Doctor: <strong className="text-slate-700">{encounter.doctor_name || "Attending Doctor"}</strong> • Dept: <strong className="text-slate-700">{encounter.department_name}</strong>
                </p>
              </div>
            </div>

            {encounter.status === "OPEN" && (
              <button
                onClick={handleStartEncounter}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition flex items-center gap-2 shadow-sm"
              >
                <Play className="w-4 h-4" />
                <span>Begin Consultation (In-Progress)</span>
              </button>
            )}
          </div>
        )}

        {statusMsg && (
          <div className={`p-4 rounded-xl text-xs flex items-center gap-2 border ${
            statusMsg.type === "success" 
              ? "bg-emerald-50 text-emerald-800 border-emerald-200" 
              : "bg-rose-50 text-rose-800 border-rose-200"
          }`}>
            {statusMsg.type === "success" ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
            <span>{statusMsg.text}</span>
          </div>
        )}

        {/* Vitals Form */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Activity className="w-4 h-4 text-medicore-600" />
                <span>Physiological Intake & Vitals Assessment</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">Validated ranges enforced server-side. Recorded with nurse timestamp.</p>
            </div>
            {computedBmi && (
              <div className="text-right">
                <span className="text-[10px] uppercase font-bold text-slate-400 block">Instant BMI Preview</span>
                <span className="text-sm font-extrabold text-medicore-700">{computedBmi} kg/m²</span>
              </div>
            )}
          </div>

          <form onSubmit={handleSaveVitals} className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Temp */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700 flex items-center gap-1">
                  <Thermometer className="w-3.5 h-3.5 text-rose-500" />
                  <span>Temperature (°C)</span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="30"
                  max="45"
                  value={temp}
                  onChange={e => setTemp(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500"
                  placeholder="37.0"
                />
                <span className="text-[10px] text-slate-400">Valid: 30.0 - 45.0 °C</span>
              </div>

              {/* Heart Rate */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700 flex items-center gap-1">
                  <Heart className="w-3.5 h-3.5 text-rose-500" />
                  <span>Heart Rate (bpm)</span>
                </label>
                <input
                  type="number"
                  min="30"
                  max="300"
                  value={heartRate}
                  onChange={e => setHeartRate(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500"
                  placeholder="72"
                />
                <span className="text-[10px] text-slate-400">Valid: 30 - 300 bpm</span>
              </div>

              {/* Respiratory Rate */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Respiratory Rate (breaths/min)</label>
                <input
                  type="number"
                  min="5"
                  max="100"
                  value={respRate}
                  onChange={e => setRespRate(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500"
                  placeholder="16"
                />
                <span className="text-[10px] text-slate-400">Valid: 5 - 100 breaths/min</span>
              </div>

              {/* SpO2 */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Oxygen Saturation (SpO2 %)</label>
                <input
                  type="number"
                  step="0.1"
                  min="50"
                  max="100"
                  value={spo2}
                  onChange={e => setSpo2(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500"
                  placeholder="98.5"
                />
                <span className="text-[10px] text-slate-400">Valid: 50.0 - 100.0 %</span>
              </div>

              {/* Blood Pressure Systolic */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Systolic BP (mmHg)</label>
                <input
                  type="number"
                  min="50"
                  max="300"
                  value={systolic}
                  onChange={e => setSystolic(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500"
                  placeholder="120"
                />
                <span className="text-[10px] text-slate-400">Valid: 50 - 300 mmHg</span>
              </div>

              {/* Blood Pressure Diastolic */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Diastolic BP (mmHg)</label>
                <input
                  type="number"
                  min="30"
                  max="200"
                  value={diastolic}
                  onChange={e => setDiastolic(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500"
                  placeholder="80"
                />
                <span className="text-[10px] text-slate-400">Must be &lt; Systolic</span>
              </div>

              {/* Height */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Height (cm)</label>
                <input
                  type="number"
                  step="0.5"
                  min="21"
                  max="300"
                  value={height}
                  onChange={e => setHeight(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500"
                  placeholder="175"
                />
                <span className="text-[10px] text-slate-400">Valid: 21 - 300 cm</span>
              </div>

              {/* Weight */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">Weight (kg)</label>
                <input
                  type="number"
                  step="0.5"
                  min="2"
                  max="500"
                  value={weight}
                  onChange={e => setWeight(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500"
                  placeholder="70"
                />
                <span className="text-[10px] text-slate-400">Valid: 2 - 500 kg</span>
              </div>
            </div>

            {/* Pain Score Slider */}
            <div className="space-y-2 bg-slate-50 p-4 rounded-xl border border-slate-100">
              <div className="flex justify-between items-center text-xs font-semibold text-slate-700">
                <span>Pain Score (Wong-Baker Scale: 0 = No Pain, 10 = Worst Pain)</span>
                <span className="px-2 py-0.5 rounded bg-slate-200 text-slate-800 font-bold">{painScore} / 10</span>
              </div>
              <input
                type="range"
                min="0"
                max="10"
                value={painScore}
                onChange={e => setPainScore(parseInt(e.target.value))}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-medicore-600"
              />
            </div>

            {/* Triage / Intake Notes */}
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Clinical Intake & Triage Notes</label>
              <textarea
                rows={3}
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="Patient symptoms, ambulatory status, chief presenting complaint..."
                className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-medicore-500"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="submit"
                disabled={isSaving}
                className="bg-medicore-600 hover:bg-medicore-700 disabled:opacity-50 text-white text-xs font-bold px-6 py-2.5 rounded-xl transition flex items-center gap-2 shadow-sm"
              >
                <Save className="w-4 h-4" />
                <span>{isSaving ? "Saving Vitals..." : "Record & Save Vitals"}</span>
              </button>
            </div>
          </form>
        </div>

        {/* Existing Vitals History */}
        {vitalsHistory.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Previous Vitals Records ({vitalsHistory.length})</h3>
            <div className="space-y-3">
              {vitalsHistory.map((v) => (
                <div key={v.id} className="text-xs p-4 rounded-xl bg-slate-50 border border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                  <div className="space-y-1">
                    <div className="font-semibold text-slate-800">
                      BP: {v.systolic_bp}/{v.diastolic_bp} mmHg • HR: {v.heart_rate} bpm • Temp: {v.temperature_c} °C • SpO2: {v.oxygen_saturation}% • BMI: {v.bmi}
                    </div>
                    {v.notes && <p className="text-slate-500 italic">"{v.notes}"</p>}
                  </div>
                  <div className="text-[11px] text-slate-400 text-right">
                    <div>Recorded by {v.recorded_by_name || "Nurse"}</div>
                    <div>{new Date(v.created_at).toLocaleTimeString()}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </NurseLayout>
  );
}
