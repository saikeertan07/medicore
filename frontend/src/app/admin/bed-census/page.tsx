"use client";

import React, { useState } from "react";
import { AdminLayout } from "@/components/layout/admin-layout";
import { api } from "@/lib/api";
import { 
  Building2, Activity, ShieldAlert, CheckCircle2, 
  AlertTriangle, Truck, RefreshCw, BedDouble, AlertOctagon 
} from "lucide-react";

export default function AdminBedCensusPage() {
  const [wards, setWards] = useState([
    { ward_type: "ICU", total_beds: 20, occupied_beds: 17, isolation_beds: 2 },
    { ward_type: "CCU", total_beds: 15, occupied_beds: 11, isolation_beds: 1 },
    { ward_type: "EMERGENCY", total_beds: 30, occupied_beds: 24, isolation_beds: 4 },
    { ward_type: "SURGICAL", total_beds: 40, occupied_beds: 28, isolation_beds: 3 },
    { ward_type: "GENERAL", total_beds: 100, occupied_beds: 78, isolation_beds: 10 }
  ]);

  const [censusResult, setCensusResult] = useState<any>(null);
  const [ambulanceId, setAmbulanceId] = useState("MEDIC-104");
  const [ambulanceTriage, setAmbulanceTriage] = useState("CRITICAL");
  const [requiresIcu, setRequiresIcu] = useState(true);
  const [ambulanceRouting, setAmbulanceRouting] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleCalculateCensus = async () => {
    setIsLoading(true);
    try {
      const res = await api.post<any>("/bed-telemetry/census", { wards });
      setCensusResult(res);
    } catch (err: any) {
      alert(err.message || "Failed to calculate bed census.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRouteAmbulance = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.post<any>("/bed-telemetry/ambulance-intake", {
        ambulance_id: ambulanceId,
        triage_severity: ambulanceTriage,
        requires_icu: requiresIcu,
        wards: wards
      });
      setAmbulanceRouting(res);
    } catch (err: any) {
      alert(err.message || "Failed to route ambulance intake.");
    }
  };

  const updateOccupied = (index: number, val: number) => {
    const updated = [...wards];
    updated[index].occupied_beds = Math.max(0, Math.min(updated[index].total_beds, val));
    setWards(updated);
  };

  return (
    <AdminLayout>
      <div className="p-8 max-w-6xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
              <BedDouble className="w-8 h-8 text-cyan-400" />
              Real-Time ICU Telemetry & Bed Capacity Census
            </h1>
            <p className="text-zinc-400 mt-1">
              Executive capacity monitoring, threshold divert alerts, and predictive inbound ambulance intake.
            </p>
          </div>
          <button
            onClick={handleCalculateCensus}
            disabled={isLoading}
            className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold rounded-xl flex items-center gap-2 shadow-lg transition-all"
          >
            {isLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Activity className="w-4 h-4" />}
            Refresh Census Telemetry
          </button>
        </div>

        {/* Divert Alert Banner */}
        {censusResult?.icu_divert_active && (
          <div className="p-5 bg-red-950/70 border border-red-700 rounded-2xl text-red-200 animate-pulse flex items-start gap-4 shadow-2xl">
            <AlertOctagon className="w-8 h-8 text-red-400 shrink-0 mt-0.5" />
            <div>
              <div className="text-lg font-bold text-red-300">CRITICAL ICU DIVERT ACTIVE</div>
              <div className="text-sm text-red-200 mt-1">
                ICU capacity has reached or exceeded 90% saturation. Regional EMS notified to divert critical inbound transports to secondary trauma centers.
              </div>
            </div>
          </div>
        )}

        {/* Overall Stats */}
        {censusResult && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-5 bg-zinc-900 border border-zinc-800 rounded-2xl">
              <div className="text-xs text-zinc-400 uppercase font-semibold">Total Hospital Beds</div>
              <div className="text-3xl font-extrabold text-white mt-1">{censusResult.overall_total_beds}</div>
            </div>
            <div className="p-5 bg-zinc-900 border border-zinc-800 rounded-2xl">
              <div className="text-xs text-zinc-400 uppercase font-semibold">Occupied Beds</div>
              <div className="text-3xl font-extrabold text-amber-400 mt-1">{censusResult.overall_occupied}</div>
            </div>
            <div className="p-5 bg-zinc-900 border border-zinc-800 rounded-2xl">
              <div className="text-xs text-zinc-400 uppercase font-semibold">Available Beds</div>
              <div className="text-3xl font-extrabold text-emerald-400 mt-1">{censusResult.overall_available}</div>
            </div>
            <div className="p-5 bg-zinc-900 border border-zinc-800 rounded-2xl">
              <div className="text-xs text-zinc-400 uppercase font-semibold">Utilization Rate</div>
              <div className="text-3xl font-extrabold text-cyan-400 mt-1">{censusResult.overall_utilization_pct}%</div>
            </div>
          </div>
        )}

        {/* Ward Breakdown Cards */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl space-y-4">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Building2 className="w-5 h-5 text-cyan-400" />
            Ward Occupancy Adjustments & Capacity Breakdown
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {wards.map((ward, i) => {
              const util = Math.round((ward.occupied_beds / ward.total_beds) * 100);
              const isCrit = util >= 90;
              return (
                <div key={i} className={`p-4 rounded-xl border ${isCrit ? "bg-red-950/20 border-red-800/80" : "bg-zinc-800/60 border-zinc-700/60"}`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-white">{ward.ward_type} Ward</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-bold ${isCrit ? "bg-red-950 text-red-400 border border-red-800" : "bg-zinc-700 text-zinc-300"}`}>
                      {util}%
                    </span>
                  </div>
                  <div className="text-xs text-zinc-400 mb-2">
                    Occupied: {ward.occupied_beds} / {ward.total_beds} beds
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="range"
                      min={0}
                      max={ward.total_beds}
                      value={ward.occupied_beds}
                      onChange={(e) => updateOccupied(i, parseInt(e.target.value))}
                      className="w-full h-1.5 bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Ambulance Intake Simulation */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl space-y-6">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Truck className="w-5 h-5 text-amber-400" />
            Inbound Emergency Ambulance Intake Routing
          </h2>

          <form onSubmit={handleRouteAmbulance} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
            <div>
              <label className="block text-xs font-semibold text-zinc-400 mb-1">Ambulance Unit ID</label>
              <input
                type="text"
                required
                value={ambulanceId}
                onChange={(e) => setAmbulanceId(e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2 text-white"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-zinc-400 mb-1">Triage Severity</label>
              <select
                value={ambulanceTriage}
                onChange={(e) => setAmbulanceTriage(e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2 text-white"
              >
                <option value="CRITICAL">Critical (Immediate Care)</option>
                <option value="URGENT">Urgent (Wait &lt; 30 mins)</option>
                <option value="STABLE">Stable Transport</option>
              </select>
            </div>
            <div className="flex items-center gap-2 pb-2">
              <input
                type="checkbox"
                id="reqIcu"
                checked={requiresIcu}
                onChange={(e) => setRequiresIcu(e.target.checked)}
                className="w-4 h-4 rounded text-cyan-500 bg-zinc-800 border-zinc-700"
              />
              <label htmlFor="reqIcu" className="text-xs text-zinc-300">
                Requires Intensive Care (ICU)
              </label>
            </div>
            <div>
              <button
                type="submit"
                className="w-full py-2.5 bg-amber-600 hover:bg-amber-500 text-white font-semibold rounded-xl flex items-center justify-center gap-2 shadow-lg transition-all"
              >
                <Truck className="w-4 h-4" /> Route Ambulance
              </button>
            </div>
          </form>

          {ambulanceRouting && (
            <div className={`p-4 rounded-xl border flex items-start gap-3 ${
              ambulanceRouting.status === "ACCEPT"
                ? "bg-emerald-950/60 border-emerald-700 text-emerald-200"
                : "bg-red-950/60 border-red-700 text-red-200"
            }`}>
              {ambulanceRouting.status === "ACCEPT" ? (
                <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="w-6 h-6 text-red-400 shrink-0 mt-0.5" />
              )}
              <div>
                <div className="font-bold text-base flex items-center gap-2">
                  <span>Routing Decision: {ambulanceRouting.status}</span>
                  {ambulanceRouting.assigned_bay && (
                    <span className="px-2 py-0.5 bg-emerald-900 border border-emerald-700 rounded text-xs text-emerald-300 font-mono">
                      {ambulanceRouting.assigned_bay}
                    </span>
                  )}
                </div>
                <div className="text-xs mt-1 leading-relaxed opacity-90">{ambulanceRouting.recommended_action}</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  );
}
