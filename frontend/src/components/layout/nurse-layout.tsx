"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { 
  Activity, Users, Calendar, Clock, LogOut, 
  Menu, X, HeartPulse, Stethoscope, Sparkles
} from "lucide-react";

export function NurseLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && (!isAuthenticated || (user?.role !== "NURSE" && user?.role !== "ADMIN" && user?.role !== "STAFF"))) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, user, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-500 text-sm">
        Verifying clinical nurse credentials...
      </div>
    );
  }

  const navItems = [
    { name: "Triage & Patient Queue", href: "/nurse/dashboard", icon: HeartPulse },
    { name: "Nurse Clinical AI", href: "/nurse/ai", icon: Sparkles },
    { name: "Laboratory Workbench", href: "/nurse/lab", icon: Activity },
    { name: "Patient Records", href: "/admin/patients", icon: Users },
    { name: "Physician Schedules", href: "/doctors", icon: Calendar },
  ];

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex flex-col w-64 bg-slate-900 border-r border-slate-800 fixed inset-y-0 z-40 text-slate-300">
        <div className="h-16 px-6 flex items-center gap-3 border-b border-slate-800">
          <div className="w-9 h-9 rounded-xl bg-teal-500 flex items-center justify-center text-white shadow-sm">
            <HeartPulse className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-white text-base tracking-tight">MediCore<span className="text-teal-400">TRIAGE</span></span>
            <p className="text-[10px] text-slate-400 font-semibold tracking-wider uppercase">Nursing Operations</p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition ${
                  isActive
                    ? "bg-teal-500 text-white shadow-sm"
                    : "text-slate-400 hover:text-white hover:bg-slate-800/60"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </div>

        <div className="p-4 border-t border-slate-800 bg-slate-950/40">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-teal-500/20 text-teal-400 border border-teal-500/30 flex items-center justify-center text-xs font-bold">
              {user?.full_name?.charAt(0) || "N"}
            </div>
            <div className="overflow-hidden">
              <p className="text-xs font-bold text-white truncate">{user?.full_name}</p>
              <p className="text-[10px] text-teal-400 font-medium uppercase tracking-wider">{user?.role}</p>
            </div>
          </div>
          <button
            onClick={() => { logout(); router.push("/login"); }}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-rose-400 text-xs font-semibold transition"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 lg:pl-64 flex flex-col min-h-screen">
        {/* Mobile Navbar */}
        <header className="lg:hidden h-16 bg-slate-900 text-white flex items-center justify-between px-6 sticky top-0 z-30 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-teal-500 flex items-center justify-center text-white">
              <HeartPulse className="w-4 h-4" />
            </div>
            <span className="font-bold text-sm">MediCore Nurse Station</span>
          </div>
          <button onClick={() => setMobileNavOpen(!mobileNavOpen)} className="p-2 text-slate-300">
            {mobileNavOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </header>

        {mobileNavOpen && (
          <div className="lg:hidden bg-slate-900 border-b border-slate-800 px-4 py-4 space-y-2">
            {navItems.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                onClick={() => setMobileNavOpen(false)}
                className="block px-4 py-2 rounded-lg text-sm text-slate-300 hover:bg-slate-800"
              >
                {item.name}
              </Link>
            ))}
            <button
              onClick={() => { logout(); router.push("/login"); }}
              className="w-full text-left px-4 py-2 text-sm text-rose-400 hover:bg-slate-800"
            >
              Sign Out
            </button>
          </div>
        )}

        <main className="flex-1 p-6 lg:p-8 max-w-7xl mx-auto w-full">
          {children}
        </main>
      </div>
    </div>
  );
}
