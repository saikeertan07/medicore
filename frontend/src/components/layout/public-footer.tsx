import React from "react";
import Link from "next/link";
import { Activity, Phone, Mail, MapPin, Shield, Award, HeartHandshake } from "lucide-react";

export function PublicFooter() {
  return (
    <footer className="bg-slate-900 text-slate-400 border-t border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12">
          {/* Brand Col */}
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-medicore-600 flex items-center justify-center text-white">
                <Activity className="w-6 h-6" />
              </div>
              <span className="text-xl font-bold tracking-tight text-white">MediCore<span className="text-medicore-400">AI</span></span>
            </div>
            <p className="text-sm leading-relaxed text-slate-400">
              State-of-the-art tertiary care hospital powered by intelligent clinical workflows, predictive scheduling, and dedicated medical specialists.
            </p>
            <div className="flex items-center gap-4 text-xs text-slate-500 pt-2">
              <div className="flex items-center gap-1"><Shield className="w-4 h-4 text-emerald-400" /> JCI Accredited</div>
              <div className="flex items-center gap-1"><Award className="w-4 h-4 text-amber-400" /> Top Ranked 2026</div>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="text-sm font-semibold text-white tracking-wider uppercase mb-4">Medical Services</h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/departments" className="hover:text-white transition">Cardiology & Vascular</Link></li>
              <li><Link href="/departments" className="hover:text-white transition">Neurology & Neurosurgery</Link></li>
              <li><Link href="/departments" className="hover:text-white transition">Orthopedic Surgery</Link></li>
              <li><Link href="/departments" className="hover:text-white transition">Pediatric Acute Care</Link></li>
              <li><Link href="/departments" className="hover:text-white transition">Medical & Surgical Oncology</Link></li>
              <li><Link href="/services" className="hover:text-white transition">Diagnostic Imaging & Lab</Link></li>
            </ul>
          </div>

          {/* Patient Portals */}
          <div>
            <h4 className="text-sm font-semibold text-white tracking-wider uppercase mb-4">Access Portals</h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/login" className="hover:text-white transition">Patient Portal Login</Link></li>
              <li><Link href="/login" className="hover:text-white transition">Physician EHR Access</Link></li>
              <li><Link href="/login" className="hover:text-white transition">Hospital Staff & Admin</Link></li>
              <li><Link href="/appointments" className="hover:text-white transition">Online Slot Booking</Link></li>
              <li><Link href="/faq" className="hover:text-white transition">Insurance & Visiting Policies</Link></li>
              <li><Link href="/emergency" className="text-red-400 hover:text-red-300 transition font-medium">Emergency Triage Guide</Link></li>
            </ul>
          </div>

          {/* Emergency & Contact */}
          <div>
            <h4 className="text-sm font-semibold text-white tracking-wider uppercase mb-4">Contact & Location</h4>
            <div className="space-y-3 text-sm">
              <div className="flex items-start gap-2.5">
                <MapPin className="w-5 h-5 text-medicore-400 shrink-0 mt-0.5" />
                <span>100 Medical Center Plaza, Metro City, NY 10001</span>
              </div>
              <div className="flex items-center gap-2.5">
                <Phone className="w-4 h-4 text-medicore-400 shrink-0" />
                <span>General: (555) 234-CORE</span>
              </div>
              <div className="flex items-center gap-2.5 text-red-400 font-semibold">
                <Phone className="w-4 h-4 shrink-0" />
                <span>24/7 ER: (555) 911-CORE</span>
              </div>
              <div className="flex items-center gap-2.5">
                <Mail className="w-4 h-4 text-medicore-400 shrink-0" />
                <span>patientcare@medicore.ai</span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-12 pt-8 border-t border-slate-800 text-xs text-slate-500 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p>© {new Date().getFullYear()} MediCore AI Health System. All rights reserved. Professional medical disclaimer: AI assistant features are for clinical and administrative workflow support only.</p>
          <div className="flex gap-6">
            <Link href="/faq" className="hover:text-slate-400">Privacy Policy</Link>
            <Link href="/faq" className="hover:text-slate-400">Terms of Care</Link>
            <Link href="/faq" className="hover:text-slate-400">HIPAA Compliance</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
