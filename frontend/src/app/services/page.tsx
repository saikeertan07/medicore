"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { Activity, Clock, DollarSign, Calendar, ArrowRight } from "lucide-react";

export default function ServicesPage() {
  const services = [
    { name: "Comprehensive Cardiac Screening", dept: "Cardiology", price: 250, duration: 45, desc: "Complete cardiac assessment with 12-lead ECG, lipid panel, and doctor consultation." },
    { name: "Advanced Echocardiography (TTE)", dept: "Cardiology", price: 450, duration: 45, desc: "Transthoracic ultrasound evaluating cardiac chamber structure and valve dynamics." },
    { name: "Brain & Spinal Diagnostic Consult", dept: "Neurology", price: 220, duration: 40, desc: "Specialist neurological evaluation with reflex and sensory nerve testing." },
    { name: "Sleep Study Polysomnography", dept: "Neurology", price: 850, duration: 480, desc: "Overnight diagnostic evaluation measuring sleep stages and respiratory patterns." },
    { name: "Total Joint Mobility Consultation", dept: "Orthopedics", price: 180, duration: 30, desc: "Orthopedic assessment with digital range-of-motion mapping and rehab planning." },
    { name: "Pediatric Annual Wellness Exam", dept: "Pediatrics", price: 150, duration: 30, desc: "Comprehensive growth, vaccination status, vision, and hearing screening." },
    { name: "Pediatric Allergy & Immunology Panel", dept: "Pediatrics", price: 320, duration: 60, desc: "Skin prick and blood antigen testing for common food and environmental triggers." },
    { name: "Oncological Multi-Disciplinary Review", dept: "Oncology", price: 500, duration: 60, desc: "Tumor board consultation formulating customized molecular treatment pathways." },
    { name: "Outpatient Minor Infusion Therapy", dept: "Oncology", price: 350, duration: 120, desc: "Hydration, electrolyte replacement, and monitored intravenous infusion." },
    { name: "Executive Preventive Health Checkup", dept: "Cardiology", price: 1200, duration: 240, desc: "Full-day executive screening encompassing cardiology, imaging, and biochemistry." }
  ];

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <PublicNav />
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 w-full">
        <div className="max-w-3xl mb-12">
          <span className="text-xs font-bold uppercase tracking-wider text-medicore-600">Clinical Procedures & Diagnostics</span>
          <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight mt-1">Hospital Services & Diagnostics</h1>
          <p className="text-slate-600 text-base mt-2">
            Transparent clinical pricing, comprehensive testing packages, and outpatient specialty procedures.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {services.map((s, idx) => (
            <div key={idx} className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col justify-between shadow-sm hover:shadow-md transition">
              <div>
                <span className="text-xs font-semibold text-medicore-600 uppercase tracking-wide">{s.dept}</span>
                <h3 className="font-bold text-slate-900 text-lg mt-1">{s.name}</h3>
                <p className="text-xs text-slate-500 mt-2 leading-relaxed">{s.desc}</p>
                <div className="flex items-center gap-4 text-xs text-slate-400 mt-4">
                  <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" /> {s.duration} mins</span>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-slate-400 uppercase font-medium">Standard Price</span>
                  <div className="text-lg font-bold text-slate-900">${s.price}</div>
                </div>
                <Link
                  href="/appointments"
                  className="bg-medicore-50 hover:bg-medicore-100 text-medicore-700 text-xs font-semibold px-3.5 py-2 rounded-lg transition border border-medicore-200 flex items-center gap-1"
                >
                  <Calendar className="w-3 h-3" />
                  <span>Schedule</span>
                </Link>
              </div>
            </div>
          ))}
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
