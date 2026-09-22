"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { api } from "@/lib/api";
import { Doctor, Department } from "@/types";
import { 
  Activity, Calendar, Search, ShieldCheck, Clock, Award, 
  ArrowRight, PhoneCall, Heart, Brain, Bone, Baby, ShieldAlert,
  Star, CheckCircle2, Stethoscope, ChevronRight
} from "lucide-react";

export default function HomePage() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [featuredDoctors, setFeaturedDoctors] = useState<Doctor[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDept, setSelectedDept] = useState("");

  useEffect(() => {
    // Fetch departments and featured doctors from backend
    api.get<Department[]>("/departments")
      .then(res => setDepartments(res))
      .catch(() => {});

    api.get<Doctor[]>("/doctors")
      .then(res => setFeaturedDoctors(res.slice(0, 4)))
      .catch(() => {});
  }, []);

  const getDeptIcon = (name: string) => {
    switch (name.toLowerCase()) {
      case "cardiology": return <Heart className="w-6 h-6 text-rose-500" />;
      case "neurology": return <Brain className="w-6 h-6 text-indigo-500" />;
      case "orthopedics": return <Bone className="w-6 h-6 text-amber-500" />;
      case "pediatrics": return <Baby className="w-6 h-6 text-emerald-500" />;
      case "oncology": return <ShieldAlert className="w-6 h-6 text-purple-500" />;
      default: return <Activity className="w-6 h-6 text-medicore-500" />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <PublicNav />

      <main className="flex-1">
        {/* HERO SECTION */}
        <section className="relative overflow-hidden bg-gradient-to-b from-medicore-50/60 via-white to-slate-50 pt-16 pb-24 border-b border-slate-200/60">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
              
              {/* Hero Left Content */}
              <div className="lg:col-span-7 space-y-6">
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-medicore-100/80 border border-medicore-200 text-medicore-800 text-xs font-semibold tracking-wide">
                  <Activity className="w-3.5 h-3.5 text-medicore-600" />
                  <span>Next-Generation Intelligent Hospital Care</span>
                </div>

                <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 tracking-tight leading-[1.12]">
                  World-Class Healthcare. <br />
                  <span className="text-medicore-600">Zero Wait Time Friction.</span>
                </h1>

                <p className="text-lg text-slate-600 leading-relaxed max-w-2xl">
                  MediCore AI bridges board-certified physician expertise with real-time appointment scheduling, instant clinical document intelligence, and unified patient records.
                </p>

                {/* Instant Search Bar */}
                <div className="bg-white p-3 rounded-2xl shadow-lg shadow-slate-200/60 border border-slate-200 flex flex-col sm:flex-row gap-3">
                  <div className="flex-1 flex items-center gap-3 px-3 py-1">
                    <Search className="w-5 h-5 text-slate-400 shrink-0" />
                    <input 
                      type="text"
                      placeholder="Search doctor, specialty, or condition..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full text-sm outline-none text-slate-800 placeholder-slate-400 bg-transparent"
                    />
                  </div>
                  <div className="sm:w-48 border-t sm:border-t-0 sm:border-l border-slate-200 px-3 py-1 flex items-center">
                    <select
                      value={selectedDept}
                      onChange={(e) => setSelectedDept(e.target.value)}
                      className="w-full text-sm outline-none text-slate-700 bg-transparent cursor-pointer"
                    >
                      <option value="">All Departments</option>
                      {departments.map(d => (
                        <option key={d.id} value={d.id}>{d.name}</option>
                      ))}
                    </select>
                  </div>
                  <Link
                    href={`/doctors?search=${encodeURIComponent(searchQuery)}&dept=${selectedDept}`}
                    className="bg-medicore-600 hover:bg-medicore-700 text-white font-medium px-6 py-3 rounded-xl text-sm flex items-center justify-center gap-2 transition"
                  >
                    <span>Find Care</span>
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>

                {/* Trust Badges */}
                <div className="pt-4 flex flex-wrap items-center gap-6 text-xs text-slate-500 font-medium">
                  <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-500" /> Instant Real-Time Booking</span>
                  <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-500" /> Board-Certified Specialists</span>
                  <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-500" /> HIPAA & JCI Compliant</span>
                </div>
              </div>

              {/* Hero Right Visual / Live Metrics Card */}
              <div className="lg:col-span-5">
                <div className="relative">
                  <div className="bg-white rounded-3xl p-6 shadow-2xl border border-slate-200/80 space-y-6">
                    <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                      <div>
                        <h3 className="font-semibold text-slate-900">Hospital Operating Status</h3>
                        <p className="text-xs text-slate-400">Live Campus Diagnostics</p>
                      </div>
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-semibold">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                        Normal Operations
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
                        <span className="text-xs font-medium text-slate-500">Emergency Wait</span>
                        <div className="text-2xl font-bold text-slate-900 mt-1">&lt; 8 min</div>
                        <span className="text-[11px] text-emerald-600 font-medium">Trauma Level 1 Active</span>
                      </div>
                      <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
                        <span className="text-xs font-medium text-slate-500">Available Slots Today</span>
                        <div className="text-2xl font-bold text-medicore-600 mt-1">42 Slots</div>
                        <span className="text-[11px] text-slate-500">Across 5 Specialties</span>
                      </div>
                      <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
                        <span className="text-xs font-medium text-slate-500">Active Physicians</span>
                        <div className="text-2xl font-bold text-slate-900 mt-1">15 On Duty</div>
                        <span className="text-[11px] text-slate-500">Consulting & Surgery</span>
                      </div>
                      <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
                        <span className="text-xs font-medium text-slate-500">Patient Satisfaction</span>
                        <div className="text-2xl font-bold text-amber-500 mt-1">4.94 / 5</div>
                        <span className="text-[11px] text-slate-500">Verified Reviews</span>
                      </div>
                    </div>

                    <div className="pt-2">
                      <Link
                        href="/appointments"
                        className="w-full flex items-center justify-center gap-2 bg-slate-900 hover:bg-slate-800 text-white font-medium py-3 rounded-xl text-sm transition"
                      >
                        <Calendar className="w-4 h-4" />
                        <span>Reserve an Appointment Online</span>
                      </Link>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </section>

        {/* CLINICAL DEPARTMENTS SECTION */}
        <section className="py-20 bg-white border-b border-slate-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end mb-12 gap-4">
              <div>
                <span className="text-xs font-bold tracking-wider uppercase text-medicore-600">Centers of Excellence</span>
                <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight mt-1">Clinical Departments</h2>
                <p className="text-slate-500 text-sm mt-1 max-w-xl">Advanced specialized care equipped with state-of-the-art diagnostic facilities and dedicated surgical teams.</p>
              </div>
              <Link href="/departments" className="inline-flex items-center gap-1.5 text-sm font-semibold text-medicore-600 hover:text-medicore-700">
                <span>View All Departments</span>
                <ChevronRight className="w-4 h-4" />
              </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6">
              {departments.map((dept) => (
                <Link
                  key={dept.id}
                  href={`/doctors?dept=${dept.id}`}
                  className="group bg-slate-50 hover:bg-white hover:shadow-xl hover:border-medicore-300 transition duration-300 p-6 rounded-2xl border border-slate-200 flex flex-col justify-between"
                >
                  <div>
                    <div className="w-12 h-12 rounded-xl bg-white shadow-sm border border-slate-100 flex items-center justify-center mb-4 group-hover:scale-110 transition">
                      {getDeptIcon(dept.name)}
                    </div>
                    <h3 className="font-bold text-slate-900 text-base group-hover:text-medicore-600 transition">{dept.name}</h3>
                    <p className="text-xs text-slate-500 mt-1 line-clamp-2">{dept.description}</p>
                  </div>
                  <div className="mt-4 pt-4 border-t border-slate-200/60 flex items-center justify-between text-xs font-semibold text-medicore-600">
                    <span>{dept.floor || "Main Building"}</span>
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition" />
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* FEATURED DOCTORS SECTION */}
        <section className="py-20 bg-slate-50 border-b border-slate-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end mb-12 gap-4">
              <div>
                <span className="text-xs font-bold tracking-wider uppercase text-medicore-600">Specialist Faculty</span>
                <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight mt-1">Featured Doctors</h2>
                <p className="text-slate-500 text-sm mt-1 max-w-xl">Meet our leading clinicians, board-certified surgeons, and department heads.</p>
              </div>
              <Link href="/doctors" className="inline-flex items-center gap-1.5 text-sm font-semibold text-medicore-600 hover:text-medicore-700">
                <span>Browse All Doctors</span>
                <ChevronRight className="w-4 h-4" />
              </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {featuredDoctors.map((doc) => (
                <div key={doc.id} className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col justify-between shadow-sm hover:shadow-md transition">
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <div className="w-12 h-12 rounded-full bg-medicore-100 text-medicore-700 font-bold flex items-center justify-center text-base">
                        {doc.full_name.replace("Dr. ", "").split(" ").map(n => n[0]).join("")}
                      </div>
                      <div className="flex items-center gap-1 text-amber-500 text-xs font-bold bg-amber-50 px-2 py-1 rounded-md border border-amber-200/50">
                        <Star className="w-3.5 h-3.5 fill-amber-400" />
                        <span>{doc.rating}</span>
                      </div>
                    </div>

                    <h3 className="font-bold text-slate-900 text-base">{doc.full_name}</h3>
                    <p className="text-xs text-medicore-600 font-semibold mt-0.5">{doc.specialization}</p>
                    <p className="text-[11px] text-slate-400 mt-1">{doc.qualification}</p>
                    <p className="text-xs text-slate-500 mt-3 line-clamp-2">{doc.bio}</p>
                  </div>

                  <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] text-slate-400 uppercase font-medium">Consultation</span>
                      <div className="text-sm font-bold text-slate-900">${doc.consultation_fee}</div>
                    </div>
                    <Link
                      href={`/appointments?doctor_id=${doc.id}`}
                      className="bg-medicore-50 hover:bg-medicore-100 text-medicore-700 text-xs font-semibold px-3 py-2 rounded-lg transition border border-medicore-200 flex items-center gap-1"
                    >
                      <Calendar className="w-3 h-3" />
                      <span>Book</span>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* WHY CHOOSE US & HOSPITAL STATISTICS */}
        <section className="py-20 bg-white border-b border-slate-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
              <div>
                <span className="text-xs font-bold tracking-wider uppercase text-medicore-600">Excellence in Operation</span>
                <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight mt-1">Why Choose MediCore AI Health System</h2>
                <p className="text-slate-600 text-base mt-4 leading-relaxed">
                  We engineered our hospital operating system from the ground up to eliminate medical delays. Every patient appointment, lab test, and physician note is synchronized in real time.
                </p>

                <div className="mt-8 space-y-6">
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-xl bg-medicore-50 border border-medicore-100 flex items-center justify-center text-medicore-600 shrink-0">
                      <Clock className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="font-bold text-slate-900 text-base">Guaranteed Zero Double-Booking</h4>
                      <p className="text-sm text-slate-500 mt-1">Our transactional scheduling engine prevents appointment overlaps at the database tier with real-time verification.</p>
                    </div>
                  </div>

                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-xl bg-medicore-50 border border-medicore-100 flex items-center justify-center text-medicore-600 shrink-0">
                      <ShieldCheck className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="font-bold text-slate-900 text-base">Medical Document Intelligence</h4>
                      <p className="text-sm text-slate-500 mt-1">Instant structured clinical extraction and summarization for lab reports, ECGs, and diagnostic imaging.</p>
                    </div>
                  </div>

                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-xl bg-medicore-50 border border-medicore-100 flex items-center justify-center text-medicore-600 shrink-0">
                      <PhoneCall className="w-5 h-5 text-rose-500" />
                    </div>
                    <div>
                      <h4 className="font-bold text-slate-900 text-base">24/7 ESI Level 1-5 Emergency Response</h4>
                      <p className="text-sm text-slate-500 mt-1">Comprehensive round-the-clock emergency triage, resuscitation bays, and on-call specialist surgeons.</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Statistics Grid */}
              <div className="bg-slate-900 text-white rounded-3xl p-8 lg:p-10 space-y-8 shadow-2xl">
                <div>
                  <span className="text-xs font-bold tracking-wider uppercase text-medicore-400">Validated Impact</span>
                  <h3 className="text-2xl font-bold tracking-tight text-white mt-1">Hospital Operational Statistics</h3>
                </div>

                <div className="grid grid-cols-2 gap-6">
                  <div className="border-l-2 border-medicore-500 pl-4">
                    <div className="text-4xl font-extrabold text-white">50,000+</div>
                    <div className="text-xs text-slate-400 mt-1">Patients Treated Annually</div>
                  </div>
                  <div className="border-l-2 border-medicore-500 pl-4">
                    <div className="text-4xl font-extrabold text-white">99.4%</div>
                    <div className="text-xs text-slate-400 mt-1">Patient Satisfaction Rate</div>
                  </div>
                  <div className="border-l-2 border-emerald-500 pl-4">
                    <div className="text-4xl font-extrabold text-emerald-400">12 min</div>
                    <div className="text-xs text-slate-400 mt-1">Average Check-in Time</div>
                  </div>
                  <div className="border-l-2 border-emerald-500 pl-4">
                    <div className="text-4xl font-extrabold text-emerald-400">100%</div>
                    <div className="text-xs text-slate-400 mt-1">Digital Record Security</div>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700 text-xs text-slate-300 leading-relaxed">
                  "MediCore AI has streamlined clinical scheduling and document retrieval across our entire cardiology wing, allowing our physicians to spend more time directly with patients."
                  <div className="mt-2 text-slate-400 font-semibold">— Dr. Marcus Chen, Chief of Interventional Cardiology</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* EMERGENCY & APPOINTMENT CTAs */}
        <section className="py-16 bg-gradient-to-r from-medicore-700 to-slate-900 text-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col md:flex-row items-center justify-between gap-8">
              <div>
                <h3 className="text-2xl sm:text-3xl font-bold">Need Immediate Medical Attention?</h3>
                <p className="text-slate-300 text-sm mt-2 max-w-xl">
                  Our Emergency Department is fully staffed with board-certified trauma surgeons and acute care teams 24 hours a day, 7 days a week.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-4">
                <Link
                  href="/emergency"
                  className="bg-red-600 hover:bg-red-700 text-white font-bold px-6 py-3.5 rounded-xl text-sm transition flex items-center gap-2 shadow-lg shadow-red-900/30"
                >
                  <PhoneCall className="w-4 h-4" />
                  <span>Call Emergency: (555) 911-CORE</span>
                </Link>
                <Link
                  href="/appointments"
                  className="bg-white text-slate-900 hover:bg-slate-100 font-bold px-6 py-3.5 rounded-xl text-sm transition flex items-center gap-2 shadow-md"
                >
                  <Calendar className="w-4 h-4 text-medicore-600" />
                  <span>Book Consultation</span>
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>

      <PublicFooter />
    </div>
  );
}
