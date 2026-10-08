"use client";

import React, { useState, useEffect } from "react";
import { AdminLayout } from "@/components/layout/admin-layout";
import { api } from "@/lib/api";
import { Department } from "@/types";
import { Building2, Plus, CheckCircle2 } from "lucide-react";

export default function AdminDepartmentsPage() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get<Department[]>("/departments")
      .then(setDepartments)
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Clinical Departments</h1>
            <p className="text-xs text-slate-500 mt-1">Management of hospital divisions, clinical wings, and facilities.</p>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                <th className="p-4">Department Name</th>
                <th className="p-4">Code</th>
                <th className="p-4">Campus Floor / Wing</th>
                <th className="p-4">Description</th>
                <th className="p-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {departments.map((dept) => (
                <tr key={dept.id} className="hover:bg-slate-50/60 transition">
                  <td className="p-4 font-bold text-slate-900">{dept.name}</td>
                  <td className="p-4 font-mono font-bold text-medicore-600">{dept.code}</td>
                  <td className="p-4 text-slate-600">{dept.floor || "Main Tower"}</td>
                  <td className="p-4 text-slate-500 max-w-md">{dept.description}</td>
                  <td className="p-4">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700">
                      Operational
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AdminLayout>
  );
}
