"use client";

import React, { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { api } from "@/lib/api";
import { Doctor } from "@/types";
import { Star, Calendar, MapPin, Clock, Award, CheckCircle2, ArrowRight } from "lucide-react";

export default function DoctorDetailPage() {
  const params = useParams();
  const doctorId = params.id as string;
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (doctorId) {
      api.get<Doctor>(`/doctors/${doctorId}`)
        .then(setDoctor)
        .catch(() => {})
        .finally(() => setIsLoading(false));
    }
  }, [doctorId]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex flex-col bg-slate-50">
        <PublicNav />
        <div className="flex-1 flex items-center justify-center text-sm text-slate-400">Loading physician profile...</div>
        <PublicFooter />
      </div>
    );
  }

  if (!doctor) {
    return (
      <div className="min-h-screen flex flex-col bg-slate-50">
        <PublicNav />
        <div className="flex-1 flex flex-col items-center justify-center p-4">
          <h2 className="text-xl font-bold text-slate-900">Doctor Not Found</h2>
          <p className="text-slate-500 text-sm mt-1">The requested physician record does not exist.</p>
          <Link href="/doctors" className="mt-4 text-medicore-600 font-semibold text-sm">Return to Doctors Directory</Link>
        </div>
        <PublicFooter />
      </div>
    );
  }

  const daysMap = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <PublicNav />
      <main className="flex-1 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16 w-full">
        <div className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm space-y-8">
          
          {/* Header Card */}
          <div className="flex flex-col sm:flex-row gap-6 items-start justify-between pb-8 border-b border-slate-100">
            <div className="flex gap-5 items-start">
              <div className="w-20 h-20 rounded-2xl bg-medicore-100 text-medicore-700 font-bold flex items-center justify-center text-2xl shadow-sm">
                {doctor.full_name.replace("Dr. ", "").split(" ").map(n => n[0]).join("")}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-medicore-600 uppercase tracking-wide">{doctor.department_name}</span>
                  <span className="text-slate-300">•</span>
                  <span className="text-xs text-amber-500 font-bold flex items-center gap-1">
                    <Star className="w-3.5 h-3.5 fill-amber-400" /> {doctor.rating} Rating
                  </span>
                </div>
                <h1 className="text-3xl font-extrabold text-slate-900 mt-1">{doctor.full_name}</h1>
                <p className="text-sm font-semibold text-slate-700 mt-0.5">{doctor.specialization}</p>
                <p className="text-xs text-slate-400 mt-1">{doctor.qualification} • {doctor.experience_years} Years Experience</p>
                <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
                  <span className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5 text-slate-400" /> Room {doctor.room_number || "OPD"}</span>
                  <span>Consultation Fee: <strong className="text-slate-900">${doctor.consultation_fee}</strong></span>
                </div>
              </div>
            </div>

            <Link
              href={`/appointments?doctor_id=${doctor.id}`}
              className="bg-medicore-600 hover:bg-medicore-700 text-white font-bold px-6 py-3 rounded-xl text-sm transition shadow-md shadow-medicore-600/20 flex items-center gap-2 self-stretch sm:self-auto justify-center"
            >
              <Calendar className="w-4 h-4" />
              <span>Book Appointment</span>
            </Link>
          </div>

          {/* Biography */}
          <div className="space-y-3">
            <h3 className="text-base font-bold text-slate-900">Physician Biography</h3>
            <p className="text-sm text-slate-600 leading-relaxed">{doctor.bio}</p>
          </div>

          {/* Weekly Schedule Table */}
          <div className="space-y-3">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Clock className="w-4 h-4 text-medicore-600" />
              <span>Consultation Schedule</span>
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
              {doctor.schedules && doctor.schedules.length > 0 ? (
                doctor.schedules.map((s) => (
                  <div key={s.id} className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 text-xs">
                    <span className="font-bold text-slate-900 block">{daysMap[s.day_of_week]}</span>
                    <span className="text-slate-500 mt-1 block">{s.start_time.substring(0, 5)} - {s.end_time.substring(0, 5)}</span>
                    <span className="text-[10px] text-emerald-600 font-semibold mt-2 inline-block">Active Schedule</span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-400">Regular outpatient hours: Monday - Friday, 09:00 - 17:00.</p>
              )}
            </div>
          </div>
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
