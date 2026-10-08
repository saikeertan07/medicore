"use client";

import React, { useState, useEffect } from "react";
import { AdminLayout } from "@/components/layout/admin-layout";
import { api } from "@/lib/api";
import { Bed, CheckCircle2, AlertCircle } from "lucide-react";

export default function AdminRoomsPage() {
  const [rooms, setRooms] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get<any[]>("/rooms")
      .then(setRooms)
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Hospital Bed & Room Management</h1>
          <p className="text-xs text-slate-500 mt-1">Real-time room occupancy, ICU beds, general wards, and surgical theater tracking.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {rooms.map((r) => (
            <div key={r.id} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="font-mono font-bold text-lg text-slate-900">{r.room_number}</span>
                  <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold ${
                    r.status === "AVAILABLE" ? "bg-emerald-50 text-emerald-700 border border-emerald-200" :
                    r.status === "OCCUPIED" ? "bg-rose-50 text-rose-700 border border-rose-200" : "bg-amber-50 text-amber-700 border border-amber-200"
                  }`}>
                    {r.status}
                  </span>
                </div>

                <span className="text-xs font-semibold text-medicore-600 block">{r.room_type}</span>
                <p className="text-xs text-slate-500 mt-1">{r.floor || "Main Tower"} • {r.bed_count} Bed(s)</p>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                <span>Department Assigned</span>
                <span className="font-semibold text-slate-700">{r.department_name || "General"}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </AdminLayout>
  );
}
