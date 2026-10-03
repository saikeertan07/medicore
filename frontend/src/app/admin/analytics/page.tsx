'use client';

import React, { useState, useEffect } from 'react';
import { 
  BarChart3, TrendingUp, Users, Calendar, Activity,
  Bed, ShieldAlert, CheckCircle2, Clock, RefreshCw,
  DollarSign, Stethoscope, ArrowUpRight, ArrowDownRight, Layers
} from 'lucide-react';
import { 
  ResponsiveContainer, BarChart, Bar, LineChart, Line, 
  PieChart, Pie, Cell, XAxis, YAxis, Tooltip, Legend, CartesianGrid 
} from 'recharts';
import api from '@/lib/api';

const COLORS = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

export default function AdminAnalyticsPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('7d');

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const res: any = await api.get('/analytics/dashboard');
      setData(res);
    } catch (err) {
      console.error('Failed to load analytics', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  const summary = data?.summary || {};
  const statusDistribution = data?.status_distribution || [];
  const deptUsage = data?.department_usage || [];
  const trends = data?.appointment_trends || [];
  const doctorWorkload = data?.doctor_workload || [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Executive Hospital Analytics</h1>
          <p className="text-gray-500 text-sm mt-1">
            Real-time telemetry, operational metrics, clinical throughput, and capacity utilization.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select 
            value={timeRange} 
            onChange={(e) => setTimeRange(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white font-medium shadow-sm focus:ring-2 focus:ring-primary-500"
          >
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
            <option value="90d">This Quarter</option>
          </select>
          <button
            onClick={fetchAnalytics}
            className="flex items-center gap-2 bg-white border border-gray-300 px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 shadow-sm"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between text-gray-500 text-sm font-medium">
            <span>Total Patients</span>
            <Users className="h-5 w-5 text-blue-600" />
          </div>
          <p className="text-3xl font-bold text-gray-900 mt-2">{summary.total_patients || 0}</p>
          <div className="flex items-center gap-1.5 text-xs text-emerald-600 mt-2 font-medium">
            <ArrowUpRight className="h-3.5 w-3.5" />
            <span>Active registered registry</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between text-gray-500 text-sm font-medium">
            <span>Today's Encounters</span>
            <Calendar className="h-5 w-5 text-indigo-600" />
          </div>
          <p className="text-3xl font-bold text-gray-900 mt-2">{summary.today_appointments || 0}</p>
          <div className="flex items-center gap-1.5 text-xs text-gray-500 mt-2 font-medium">
            <Clock className="h-3.5 w-3.5 text-indigo-500" />
            <span>Scheduled for today</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between text-gray-500 text-sm font-medium">
            <span>Bed & Room Occupancy</span>
            <Bed className="h-5 w-5 text-amber-600" />
          </div>
          <p className="text-3xl font-bold text-gray-900 mt-2">
            {summary.total_rooms ? Math.round(((summary.total_rooms - summary.available_rooms) / summary.total_rooms) * 100) : 0}%
          </p>
          <div className="text-xs text-gray-500 mt-2 font-medium">
            <span>{summary.available_rooms || 0} of {summary.total_rooms || 0} rooms currently vacant</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between text-gray-500 text-sm font-medium">
            <span>Pharmacy / Stock Alerts</span>
            <ShieldAlert className="h-5 w-5 text-rose-600" />
          </div>
          <p className="text-3xl font-bold text-gray-900 mt-2">{summary.inventory_alerts || 0}</p>
          <div className="text-xs text-rose-600 mt-2 font-medium">
            <span>Critical or Low Stock items requiring reorder</span>
          </div>
        </div>
      </div>

      {/* Chart Grid 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trend line */}
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-base font-semibold text-gray-900 mb-1">Appointment Volume & Throughput (7-Day Trend)</h2>
          <p className="text-xs text-gray-500 mb-6">Daily patient bookings across all clinical services</p>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trends} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="date" tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} />
                <YAxis tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} allowDecimals={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', borderRadius: '8px', border: 'none', color: '#fff' }} 
                  itemStyle={{ color: '#fff' }}
                />
                <Line 
                  type="monotone" 
                  dataKey="appointments" 
                  name="Appointments" 
                  stroke="#2563eb" 
                  strokeWidth={3} 
                  dot={{ r: 4, fill: '#2563eb', strokeWidth: 2, stroke: '#fff' }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Appointment Status Pie */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-base font-semibold text-gray-900 mb-1">Appointment Status Breakdown</h2>
          <p className="text-xs text-gray-500 mb-4">Cumulative distribution</p>
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={statusDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={85}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {statusDistribution.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs pt-3 border-t border-gray-100">
            {statusDistribution.map((item: any, idx: number) => (
              <div key={idx} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }} />
                <span className="text-gray-600 truncate">{item.name}:</span>
                <span className="font-semibold text-gray-900">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Chart Grid 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Department Distribution Bar Chart */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-base font-semibold text-gray-900 mb-1">Department Encounters & Caseload</h2>
          <p className="text-xs text-gray-500 mb-6">Patient volume by specialty division</p>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={deptUsage} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="name" tickLine={false} tick={{ fill: '#64748b', fontSize: 11 }} />
                <YAxis tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} allowDecimals={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', borderRadius: '8px', border: 'none', color: '#fff' }} 
                  itemStyle={{ color: '#fff' }}
                />
                <Bar dataKey="value" name="Appointments" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Doctor Workload Table & Ranking */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-base font-semibold text-gray-900 mb-1">Top Attending Clinicians by Workload</h2>
          <p className="text-xs text-gray-500 mb-4">Highest caseload assignments</p>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 text-gray-600 text-xs font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3">Physician</th>
                  <th className="px-4 py-3">Specialty</th>
                  <th className="px-4 py-3 text-right">Appointments</th>
                  <th className="px-4 py-3 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {doctorWorkload.map((doc: any, i: number) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900 flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold">
                        {i + 1}
                      </div>
                      {doc.doctor}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{doc.department}</td>
                    <td className="px-4 py-3 text-right font-semibold text-gray-900">{doc.appointments}</td>
                    <td className="px-4 py-3 text-right">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                        Active
                      </span>
                    </td>
                  </tr>
                ))}
                {doctorWorkload.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-gray-400">No physician workload data found</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
