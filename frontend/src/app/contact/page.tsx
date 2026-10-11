"use client";

import React, { useState } from "react";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { MapPin, Phone, Mail, Clock, CheckCircle2 } from "lucide-react";

export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <PublicNav />
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 w-full">
        <div className="max-w-3xl mb-12">
          <span className="text-xs font-bold uppercase tracking-wider text-medicore-600">Patient Relations & Inquiries</span>
          <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight mt-1">Contact MediCore AI</h1>
          <p className="text-slate-600 text-base mt-2">
            Reach our administrative team, patient advocates, or specialized clinical department coordinators.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
          {/* Contact Details */}
          <div className="lg:col-span-5 space-y-6">
            <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm space-y-6">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-medicore-50 border border-medicore-100 flex items-center justify-center text-medicore-600 shrink-0">
                  <MapPin className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="font-bold text-slate-900 text-sm">Main Medical Campus</h4>
                  <p className="text-xs text-slate-500 mt-0.5">100 Medical Plaza, Metro City, NY 10001</p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-medicore-50 border border-medicore-100 flex items-center justify-center text-medicore-600 shrink-0">
                  <Phone className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="font-bold text-slate-900 text-sm">General Inquiries & Appointments</h4>
                  <p className="text-xs text-slate-500 mt-0.5">(555) 234-CORE (Mon–Sat, 8am–7pm)</p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-rose-50 border border-rose-100 flex items-center justify-center text-rose-600 shrink-0">
                  <Phone className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="font-bold text-slate-900 text-sm">Emergency Department (24/7)</h4>
                  <p className="text-xs text-rose-600 font-semibold mt-0.5">(555) 911-CORE</p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-medicore-50 border border-medicore-100 flex items-center justify-center text-medicore-600 shrink-0">
                  <Mail className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="font-bold text-slate-900 text-sm">Patient Concierge Email</h4>
                  <p className="text-xs text-slate-500 mt-0.5">patientcare@medicore.ai</p>
                </div>
              </div>
            </div>
          </div>

          {/* Contact Inquiry Form */}
          <div className="lg:col-span-7">
            <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm">
              {submitted ? (
                <div className="py-12 text-center space-y-4">
                  <div className="w-14 h-14 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
                    <CheckCircle2 className="w-8 h-8" />
                  </div>
                  <h3 className="text-xl font-bold text-slate-900">Message Received</h3>
                  <p className="text-sm text-slate-500 max-w-md mx-auto">
                    Thank you for reaching out. A patient care representative will review your inquiry and follow up within 24 business hours.
                  </p>
                </div>
              ) : (
                <form onSubmit={(e) => { e.preventDefault(); setSubmitted(true); }} className="space-y-4">
                  <h3 className="text-lg font-bold text-slate-900 mb-2">Send an Inquiry</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name</label>
                      <input type="text" required placeholder="Sarah Jenkins" className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm outline-none focus:border-medicore-500" />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address</label>
                      <input type="email" required placeholder="sarah@example.com" className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm outline-none focus:border-medicore-500" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Subject</label>
                    <input type="text" required placeholder="Billing inquiry, feedback, or appointment assistance" className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm outline-none focus:border-medicore-500" />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Message</label>
                    <textarea rows={4} required placeholder="How can our clinical or administrative team assist you?" className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm outline-none focus:border-medicore-500"></textarea>
                  </div>
                  <button type="submit" className="bg-medicore-600 hover:bg-medicore-700 text-white font-medium px-6 py-3 rounded-xl text-sm transition">
                    Send Message
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
