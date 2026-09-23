"use client";

import React from "react";
import { DoctorLayout } from "@/components/layout/doctor-layout";
import { Clock, Calendar, CheckCircle2 } from "lucide-react";

export default function DoctorSchedulePage() {
  const days = [
    { day: "Monday", hours: "09:00 - 17:00", duration: "30 mins", room: "301-A", active: true },
    { day: "Tuesday", hours: "09:00 - 17:00", duration: "30 mins", room: "301-A", active: true },
    { day: "Wednesday", hours: "09:00 - 17:00", duration: "30 mins", room: "301-A", active: true },
    { day: "Thursday", hours: "09:00 - 17:00", duration: "30 mins", room: "301-A", active: true },
    { day: "Friday", hours: "09:00 - 17:00", duration: "30 mins", room: "301-A", active: true },
    { day: "Saturday", hours: "On-Call Trauma Rotation", duration: "Emergency", room: "ER Bay", active: false },
    { day: "Sunday", hours: "Off-Duty", duration: "-", room: "-", active: false }
  ];

  return (
    <DoctorLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Weekly Clinical Schedule</h1>
          <p className="text-xs text-slate-500 mt-1">Configured outpatient consultation hours, slot durations, and assigned examination rooms.</p>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                <th className="p-4">Day</th>
                <th className="p-4">Consultation Hours</th>
                <th className="p-4">Slot Duration</th>
                <th className="p-4">Room</th>
                <th className="p-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {days.map((d, idx) => (
                <tr key={idx} className="hover:bg-slate-50/60 transition">
                  <td className="p-4 font-bold text-slate-900">{d.day}</td>
                  <td className="p-4 text-slate-700 font-medium">{d.hours}</td>
                  <td className="p-4 text-slate-500">{d.duration}</td>
                  <td className="p-4 font-mono text-slate-600">{d.room}</td>
                  <td className="p-4">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      d.active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"
                    }`}>
                      {d.active ? "Active OPD" : "Closed / On-Call"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </DoctorLayout>
  );
}
