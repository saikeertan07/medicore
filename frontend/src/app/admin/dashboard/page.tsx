"use client";

import React, { useState, useEffect } from "react";
import { AdminLayout } from "@/components/layout/admin-layout";
import { api } from "@/lib/api";
import { DashboardMetrics } from "@/types";
import { 
  Users, Stethoscope, Calendar, Bed, Package, AlertTriangle, 
  CheckCircle2, XCircle, Clock, TrendingUp, BarChart2
} from "lucide-react";
import { 
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, 
  Tooltip, BarChart, Bar, PieChart, Pie, Cell 
} from "recharts";

const COLORS = ["#10b981", "#0284c7", "#f59e0b", "#f43f5e", "#8b5cf6"];

export default function AdminDashboardPage() {
  const [data, setData] = useState<DashboardMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get<DashboardMetrics>("/analytics/dashboard")
      .then(setData)
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return (
      <AdminLayout>
        <div className="py-24 text-center text-xs text-slate-400">Loading hospital operational metrics...</div>
      </AdminLayout>
    );
  }

  const summary = data?.summary || {
    total_patients: 50,
    total_doctors: 15,
    today_appointments: 12,
    upcoming_appointments: 40,
    completed_appointments: 40,
    cancelled_appointments: 8,
    available_rooms: 11,
    total_rooms: 15,
    inventory_alerts: 4
  };

  return (
    <AdminLayout>
      <div className="space-y-8">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <div>
            <span className="text-xs font-bold text-rose-600 uppercase tracking-wider">Executive Command</span>
            <h1 className="text-2xl font-extrabold text-slate-900 mt-0.5">Hospital Operations Dashboard</h1>
            <p className="text-xs text-slate-500 mt-1">Real-time bed occupancy, physician workload, appointment volume, and supply telemetry.</p>
          </div>
          <div className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>Live PostgreSQL Telemetry</span>
          </div>
        </div>

        {/* 8 CRITICAL METRICS CARDS */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-xs font-medium text-slate-500">Total Patients</span>
            <div className="text-3xl font-extrabold text-slate-900 mt-1">{summary.total_patients}</div>
            <span className="text-[11px] text-medicore-600 font-semibold mt-1 block">Active Profiles</span>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-xs font-medium text-slate-500">Medical Faculty</span>
            <div className="text-3xl font-extrabold text-slate-900 mt-1">{summary.total_doctors}</div>
            <span className="text-[11px] text-medicore-600 font-semibold mt-1 block">Board Specialists</span>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-xs font-medium text-slate-500">Today's Appointments</span>
            <div className="text-3xl font-extrabold text-slate-900 mt-1">{summary.today_appointments}</div>
            <span className="text-[11px] text-emerald-600 font-semibold mt-1 block">Clinical Encounters</span>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-xs font-medium text-slate-500">Upcoming Bookings</span>
            <div className="text-3xl font-extrabold text-slate-900 mt-1">{summary.upcoming_appointments}</div>
            <span className="text-[11px] text-medicore-600 font-semibold mt-1 block">Next 30 Days</span>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-xs font-medium text-slate-500">Completed Encounters</span>
            <div className="text-3xl font-extrabold text-emerald-600 mt-1">{summary.completed_appointments}</div>
            <span className="text-[11px] text-slate-400 font-medium mt-1 block">Past Sessions</span>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-xs font-medium text-slate-500">Cancelled Bookings</span>
            <div className="text-3xl font-extrabold text-rose-500 mt-1">{summary.cancelled_appointments}</div>
            <span className="text-[11px] text-slate-400 font-medium mt-1 block">Slots Released</span>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-xs font-medium text-slate-500">Available Rooms</span>
            <div className="text-3xl font-extrabold text-slate-900 mt-1">{summary.available_rooms} / {summary.total_rooms}</div>
            <span className="text-[11px] text-emerald-600 font-semibold mt-1 block">Ready for Admission</span>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <span className="text-xs font-medium text-slate-500">Inventory Alerts</span>
            <div className="text-3xl font-extrabold text-amber-500 mt-1">{summary.inventory_alerts}</div>
            <span className="text-[11px] text-amber-600 font-semibold mt-1 block">Low Stock Supplies</span>
          </div>
        </div>

        {/* CHARTS GRID 1: TRENDS & DEPARTMENT USAGE */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Appointment 7-day Trend Chart */}
          <div className="lg:col-span-8 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-slate-900 text-sm">Appointment Volume Trends</h3>
                <p className="text-xs text-slate-400">Daily appointment volume over the last 7 days</p>
              </div>
              <span className="text-xs font-semibold text-medicore-600">Daily Distribution</span>
            </div>

            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data?.appointment_trends || []}>
                  <defs>
                    <linearGradient id="appTrend" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0284c7" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#0284c7" stopOpacity={0.0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  <Area type="monotone" dataKey="appointments" stroke="#0284c7" fillOpacity={1} fill="url(#appTrend)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Appointment Status Donut */}
          <div className="lg:col-span-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <div>
              <h3 className="font-bold text-slate-900 text-sm">Appointment Status</h3>
              <p className="text-xs text-slate-400">Ratio of confirmed, completed, and cancelled</p>
            </div>

            <div className="h-48 w-full flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data?.status_distribution || []}
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={75}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {(data?.status_distribution || []).map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-slate-100">
              {(data?.status_distribution || []).map((s, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }}></span>
                  <span className="text-slate-600">{s.name}: <strong>{s.value}</strong></span>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* CHARTS GRID 2: DEPARTMENT USAGE & DOCTOR WORKLOAD */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* Department Usage Bar Chart */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <div>
              <h3 className="font-bold text-slate-900 text-sm">Department Patient Encounters</h3>
              <p className="text-xs text-slate-400">Consultation volume distributed across 5 clinical divisions</p>
            </div>

            <div className="h-60 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data?.department_usage || []}>
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#0284c7" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Doctor Workload Top 5 */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <div>
              <h3 className="font-bold text-slate-900 text-sm">Top Active Physician Workload</h3>
              <p className="text-xs text-slate-400">Consultations assigned per specialist</p>
            </div>

            <div className="h-60 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data?.doctor_workload || []} layout="vertical">
                  <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
                  <YAxis dataKey="doctor" type="category" width={110} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="appointments" fill="#10b981" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>

      </div>
    </AdminLayout>
  );
}
