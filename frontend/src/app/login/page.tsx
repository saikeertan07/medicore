"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Activity, Lock, Mail, AlertCircle, ArrowRight, Shield } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const user = await login(email.trim(), password);
      if (user.role === "PATIENT") {
        router.push("/patient/dashboard");
      } else if (user.role === "DOCTOR") {
        router.push("/doctor/dashboard");
      } else if (user.role === "RECEPTIONIST") {
        router.push("/reception/dashboard");
      } else if (user.role === "NURSE") {
        router.push("/nurse/dashboard");
      } else if (user.role === "ADMIN" || user.role === "STAFF") {
        router.push("/admin/dashboard");
      } else {
        router.push("/");
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Invalid email address or password.");
    } finally {
      setIsLoading(false);
    }
  };

  const fillDemoAccount = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <Link href="/" className="inline-flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-medicore-600 flex items-center justify-center text-white shadow-md shadow-medicore-500/20">
            <Activity className="w-7 h-7" />
          </div>
          <span className="text-2xl font-bold tracking-tight text-slate-900">MediCore<span className="text-medicore-600">AI</span></span>
        </Link>
        <h2 className="mt-4 text-2xl font-extrabold text-slate-900">Hospital Portal Sign In</h2>
        <p className="mt-1 text-xs text-slate-500">Secure access for Patients, Physicians, Nurses, Receptionists, and Administrators</p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-lg">
        <div className="bg-white py-8 px-6 shadow-xl shadow-slate-200/60 rounded-3xl border border-slate-200 sm:px-10 space-y-6">
          
          {/* Quick Demo Credentials Switcher */}
          <div className="bg-slate-50 p-3.5 rounded-2xl border border-slate-200/80 space-y-2">
            <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-slate-500">
              <span>Demo Quick-Fill (Step 2 Roles)</span>
              <span className="text-[10px] text-medicore-600 lowercase font-medium">click to test</span>
            </div>
            <div className="grid grid-cols-3 sm:grid-cols-5 gap-1.5">
              <button
                type="button"
                onClick={() => fillDemoAccount("patient.sarah@medicore.ai", "Patient@123")}
                className="py-1.5 px-2 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:border-medicore-500 hover:text-medicore-600 transition text-center shadow-2xs"
              >
                Patient
              </button>
              <button
                type="button"
                onClick={() => fillDemoAccount("doctor.chen@medicore.ai", "Doctor@123")}
                className="py-1.5 px-2 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:border-medicore-500 hover:text-medicore-600 transition text-center shadow-2xs"
              >
                Doctor
              </button>
              <button
                type="button"
                onClick={() => fillDemoAccount("receptionist@medicore.ai", "Reception@123")}
                className="py-1.5 px-2 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:border-medicore-500 hover:text-medicore-600 transition text-center shadow-2xs"
              >
                Reception
              </button>
              <button
                type="button"
                onClick={() => fillDemoAccount("nurse.sarah@medicore.ai", "Nurse@123")}
                className="py-1.5 px-2 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:border-medicore-500 hover:text-medicore-600 transition text-center shadow-2xs"
              >
                Nurse
              </button>
              <button
                type="button"
                onClick={() => fillDemoAccount("admin@medicore.ai", "Admin@123")}
                className="py-1.5 px-2 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:border-medicore-500 hover:text-medicore-600 transition text-center shadow-2xs"
              >
                Admin
              </button>
            </div>
          </div>

          {errorMessage && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1">
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                <input
                  type="email"
                  required
                  placeholder="name@medicore.ai"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-slate-300 text-sm outline-none focus:border-medicore-500 focus:ring-1 focus:ring-medicore-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-slate-300 text-sm outline-none focus:border-medicore-500 focus:ring-1 focus:ring-medicore-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-medicore-600 hover:bg-medicore-700 disabled:opacity-50 text-white font-bold py-3 rounded-xl text-sm transition shadow-md shadow-medicore-600/20 flex items-center justify-center gap-2 mt-2"
            >
              <span>{isLoading ? "Verifying Credentials..." : "Sign In to Portal"}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="pt-4 border-t border-slate-100 text-center text-xs text-slate-500 flex items-center justify-between">
            <span>Don't have a patient account?</span>
            <Link href="/register" className="font-semibold text-medicore-600 hover:text-medicore-700">
              Register Online
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
