import React from "react";
import Link from "next/link";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { ShieldCheck, Award, HeartHandshake, Users, ArrowRight } from "lucide-react";

export default function AboutPage() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <PublicNav />
      <main className="flex-1 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16 w-full space-y-16">
        
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-medicore-600">Institutional Profile</span>
          <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight mt-1">About MediCore AI Health System</h1>
          <p className="text-slate-600 text-base mt-4 leading-relaxed max-w-3xl">
            Established as an integrated tertiary medical center, MediCore AI combines world-class clinical expertise across 5 specialized departments with an advanced AI hospital operating architecture designed to eliminate operational friction and deliver compassionate patient care.
          </p>
        </div>

        {/* Pillars */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm space-y-4">
            <div className="w-12 h-12 rounded-xl bg-medicore-50 border border-medicore-100 flex items-center justify-center text-medicore-600">
              <Award className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-slate-900">Clinical Leadership</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Our 15 board-certified department heads and specialists are drawn from leading institutions with decades of experience in complex medical interventions.
            </p>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm space-y-4">
            <div className="w-12 h-12 rounded-xl bg-medicore-50 border border-medicore-100 flex items-center justify-center text-medicore-600">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-slate-900">Zero Wait Time Infrastructure</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Proprietary transactional scheduling ensures patient appointments are verified and locked instantaneously without double-bookings or extended waiting room delays.
            </p>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm space-y-4">
            <div className="w-12 h-12 rounded-xl bg-medicore-50 border border-medicore-100 flex items-center justify-center text-medicore-600">
              <HeartHandshake className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-slate-900">Compassionate Ethics</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Patient safety and clinical dignity remain central to every diagnostic workflow. AI assists administrative and digestion speed, while clinical decisions remain strictly in physician hands.
            </p>
          </div>
        </div>

        {/* Accreditation */}
        <div className="bg-slate-900 text-white rounded-3xl p-8 sm:p-10 flex flex-col sm:flex-row justify-between items-center gap-6">
          <div>
            <h3 className="text-2xl font-bold">Joint Commission International (JCI) Accredited</h3>
            <p className="text-sm text-slate-400 mt-1 max-w-xl">
              MediCore AI adheres to the most rigorous international clinical benchmarks for infection prevention, patient safety protocols, and medication management.
            </p>
          </div>
          <Link
            href="/appointments"
            className="bg-medicore-600 hover:bg-medicore-700 text-white font-bold px-6 py-3 rounded-xl text-sm transition shrink-0"
          >
            Experience MediCore
          </Link>
        </div>

      </main>
      <PublicFooter />
    </div>
  );
}
