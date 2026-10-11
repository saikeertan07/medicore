import React from "react";
import Link from "next/link";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { PhoneCall, AlertTriangle, ShieldCheck, MapPin, Clock, HeartHandshake, ArrowRight } from "lucide-react";

export default function EmergencyPage() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <PublicNav />
      <main className="flex-1 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16 w-full">
        
        {/* Urgent Emergency Alert Header */}
        <div className="bg-red-600 text-white rounded-3xl p-8 sm:p-10 shadow-xl space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-700/80 text-xs font-bold uppercase tracking-wider">
            <AlertTriangle className="w-4 h-4 text-amber-300" />
            <span>24/7 Level 1 Trauma Center Active</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Emergency Care & Clinical Triage
          </h1>

          <p className="text-red-100 text-base leading-relaxed max-w-2xl">
            If you or someone around you is experiencing life-threatening symptoms—including chest pain, sudden numbness, difficulty breathing, or severe trauma—call emergency services immediately.
          </p>

          <div className="flex flex-wrap gap-4 pt-2">
            <a
              href="tel:911"
              className="bg-white text-red-700 hover:bg-red-50 font-extrabold px-8 py-4 rounded-xl text-base transition flex items-center gap-3 shadow-md"
            >
              <PhoneCall className="w-5 h-5 text-red-600" />
              <span>Call 911 (Life Threatening)</span>
            </a>
            <a
              href="tel:5559112673"
              className="bg-red-800 hover:bg-red-900 text-white font-bold px-6 py-4 rounded-xl text-base transition flex items-center gap-2 border border-red-500"
            >
              <PhoneCall className="w-5 h-5 text-red-300" />
              <span>Hospital ER: (555) 911-CORE</span>
            </a>
          </div>
        </div>

        {/* ER Location & Arrival Directions */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <div className="w-10 h-10 rounded-xl bg-medicore-50 border border-medicore-100 flex items-center justify-center text-medicore-600">
              <MapPin className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-slate-900 text-lg">Direct Ambulance & Walk-In Bay</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Dedicated emergency vehicle bay with heated ambulance ramp and immediate wheel-chair access.
            </p>
            <div className="text-xs text-slate-500 pt-2 border-t border-slate-100">
              <strong>Address:</strong> 102 Emergency Drive (West Wing Entrance), Metro City, NY 10001
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <div className="w-10 h-10 rounded-xl bg-medicore-50 border border-medicore-100 flex items-center justify-center text-medicore-600">
              <Clock className="w-5 h-5" />
            </div>
            <h3 className="font-bold text-slate-900 text-lg">Instant Clinical Triage System</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Patients are triaged instantaneously using the Emergency Severity Index (ESI Levels 1 to 5). Critical resuscitation takes zero wait time.
            </p>
            <div className="text-xs text-slate-500 pt-2 border-t border-slate-100">
              <strong>Average ESI Level 2-3 Response:</strong> Under 8 minutes
            </div>
          </div>
        </div>

        {/* Triage Levels Guide */}
        <div className="mt-12 bg-white rounded-2xl border border-slate-200 p-8 shadow-sm space-y-6">
          <h3 className="text-xl font-bold text-slate-900">Emergency Severity Triage Protocol</h3>
          <div className="space-y-3 text-xs sm:text-sm">
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 flex justify-between items-center">
              <div><strong>Level 1 (Resuscitation):</strong> Cardiac arrest, severe respiratory failure, massive trauma.</div>
              <span className="font-bold shrink-0 ml-2">Immediate 0 min</span>
            </div>
            <div className="p-3.5 rounded-xl bg-orange-50 border border-orange-200 text-orange-900 flex justify-between items-center">
              <div><strong>Level 2 (Emergent):</strong> Chest pain, suspected stroke, acute confusion, severe pain.</div>
              <span className="font-bold shrink-0 ml-2">&lt; 10 min</span>
            </div>
            <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex justify-between items-center">
              <div><strong>Level 3 (Urgent):</strong> Moderate abdominal pain, fractures, high fever with dehydration.</div>
              <span className="font-bold shrink-0 ml-2">&lt; 30 min</span>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-700 flex justify-between items-center">
              <div><strong>Level 4 / 5 (Less Urgent / Routine):</strong> Minor sprains, simple lacerations, routine prescription refill.</div>
              <span className="font-bold shrink-0 ml-2">Referred to OPD</span>
            </div>
          </div>

          <div className="pt-2 text-xs text-slate-400">
            *Non-urgent conditions should be scheduled through the outpatient appointment system to prevent Emergency Department congestion.
          </div>
        </div>

      </main>
      <PublicFooter />
    </div>
  );
}
