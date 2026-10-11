"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { PublicNav } from "@/components/layout/public-nav";
import { PublicFooter } from "@/components/layout/public-footer";
import { api } from "@/lib/api";
import { Department } from "@/types";
import { Heart, Brain, Bone, Baby, ShieldAlert, Activity, ArrowRight } from "lucide-react";

export default function DepartmentsPage() {
  const [departments, setDepartments] = useState<Department[]>([]);

  useEffect(() => {
    api.get<Department[]>("/departments").then(setDepartments).catch(() => {});
  }, []);

  const getDeptIcon = (name: string) => {
    switch (name.toLowerCase()) {
      case "cardiology": return <Heart className="w-8 h-8 text-rose-500" />;
      case "neurology": return <Brain className="w-8 h-8 text-indigo-500" />;
      case "orthopedics": return <Bone className="w-8 h-8 text-amber-500" />;
      case "pediatrics": return <Baby className="w-8 h-8 text-emerald-500" />;
      case "oncology": return <ShieldAlert className="w-8 h-8 text-purple-500" />;
      default: return <Activity className="w-8 h-8 text-medicore-500" />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <PublicNav />
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 w-full">
        <div className="max-w-3xl mb-12">
          <span className="text-xs font-bold uppercase tracking-wider text-medicore-600">Centers of Excellence</span>
          <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight mt-1">Clinical Departments</h1>
          <p className="text-slate-600 text-base mt-2">
            Explore our specialized clinical wings equipped with modern diagnostic imaging, surgical suites, and multidisciplinary specialist care.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {departments.map((dept) => (
            <div key={dept.id} className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm hover:shadow-md transition flex flex-col justify-between">
              <div>
                <div className="w-16 h-16 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center mb-6">
                  {getDeptIcon(dept.name)}
                </div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xl font-bold text-slate-900">{dept.name}</h3>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600">{dept.code}</span>
                </div>
                <p className="text-sm text-slate-600 leading-relaxed mt-2">{dept.description}</p>
              </div>

              <div className="mt-8 pt-6 border-t border-slate-100 flex items-center justify-between">
                <span className="text-xs text-slate-400 font-medium">{dept.floor || "Main Tower"}</span>
                <Link
                  href={`/doctors?dept=${dept.id}`}
                  className="inline-flex items-center gap-1.5 text-xs font-bold text-medicore-600 hover:text-medicore-700"
                >
                  <span>View Specialists</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      </main>
      <PublicFooter />
    </div>
  );
}
