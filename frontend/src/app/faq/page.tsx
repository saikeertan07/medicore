"use client";

import React, { useState } from "react";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { ChevronDown, ChevronUp, HelpCircle } from "lucide-react";

export default function FAQPage() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  const faqs = [
    {
      q: "How does the MediCore AI appointment scheduling engine prevent double-booking?",
      a: "Our scheduling system utilizes transactional concurrency control backed by PostgreSQL partial unique indexing. When a time slot is reserved, an atomic database transaction locks the slot; if another patient attempts to book the exact same slot concurrently, the database constraint rejects the second request with a 409 Conflict, ensuring zero double-bookings."
    },
    {
      q: "What insurance carriers are accepted at MediCore AI Health System?",
      a: "MediCore AI is in-network with major national and regional commercial carriers including Blue Cross Blue Shield, Aetna, UnitedHealthcare, Cigna, Humana, and Medicare. In-network preventative wellness examinations are covered at 100% under standard policy guidelines."
    },
    {
      q: "What are the hospital inpatient and ICU visiting hours?",
      a: "General inpatient visiting hours are from 09:00 AM to 08:00 PM daily. A maximum of two visitors are permitted in a patient room at any one time. Intensive Care Unit (ICU) visiting hours are strictly restricted to 10:00 AM – 11:30 AM and 05:00 PM – 06:30 PM."
    },
    {
      q: "How is patient medical document privacy protected?",
      a: "All medical documents, imaging files, and lab results are encrypted at rest and in transit. Object-level authorization checks are strictly enforced on every request: a patient can only access their own documents, and doctors can only access records of patients under their clinical care."
    },
    {
      q: "What is the appointment cancellation and rescheduling policy?",
      a: "Appointments can be cancelled or rescheduled up to 24 hours prior to the consultation time through the patient portal. When an appointment is cancelled, the system automatically releases the slot back to the live availability pool."
    },
    {
      q: "Can the AI Assistant diagnose medical conditions autonomously?",
      a: "No. MediCore AI assistant features are designed strictly for administrative scheduling, document intelligence digestion, and operational insights. All AI-generated clinical summaries and document extractions clearly indicate that they require professional review by a licensed physician."
    }
  ];

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <PublicNav />
      <main className="flex-1 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 w-full">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <span className="text-xs font-bold uppercase tracking-wider text-medicore-600">Knowledge & Support</span>
          <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight mt-1">Frequently Asked Questions</h1>
          <p className="text-slate-600 text-sm mt-2">
            Find immediate answers regarding hospital policies, visiting hours, insurance billing, and AI technology.
          </p>
        </div>

        <div className="space-y-4">
          {faqs.map((faq, idx) => (
            <div
              key={idx}
              className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm transition"
            >
              <button
                onClick={() => setOpenIndex(openIndex === idx ? null : idx)}
                className="w-full px-6 py-5 text-left flex items-center justify-between gap-4 font-bold text-slate-900 hover:text-medicore-600 transition text-sm sm:text-base"
              >
                <span>{faq.q}</span>
                {openIndex === idx ? (
                  <ChevronUp className="w-5 h-5 text-medicore-600 shrink-0" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-slate-400 shrink-0" />
                )}
              </button>

              {openIndex === idx && (
                <div className="px-6 pb-6 text-sm text-slate-600 leading-relaxed border-t border-slate-100 pt-4">
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
