"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { 
  Activity, LayoutDashboard, Calendar, Users, Clock, 
  FileText, FileCheck, Bot, LogOut, Menu, X, Stethoscope
} from "lucide-react";

export function DoctorLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && (!isAuthenticated || (user?.role !== "DOCTOR" && user?.role !== "ADMIN"))) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, user, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-500 text-sm">
        Verifying physician credentials...
      </div>
    );
  }

  const navItems = [
    { name: "Clinical Dashboard", href: "/doctor/dashboard", icon: LayoutDashboard },
    { name: "My Appointments", href: "/doctor/appointments", icon: Calendar },
    { name: "Assigned Patients", href: "/doctor/patients", icon: Users },
    { name: "Weekly Schedule", href: "/doctor/schedule", icon: Clock },
    { name: "Patient Documents", href: "/doctor/documents", icon: FileText },
    { name: "Diagnostic Reports", href: "/doctor/reports", icon: FileCheck },
    { name: "Clinical AI Assistant", href: "/doctor/ai", icon: Bot, highlight: true },
  ];

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex flex-col w-64 bg-slate-900 border-r border-slate-800 fixed inset-y-0 z-40 text-slate-300">
        <div className="h-16 px-6 flex items-center gap-3 border-b border-slate-800">
          <div className="w-9 h-9 rounded-xl bg-medicore-500 flex items-center justify-center text-white shadow-sm">
            <Stethoscope className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-white text-base tracking-tight">MediCore<span className="text-medicore-400">MD</span></span>
            <p className="text-[10px] text-slate-400 font-semibold tracking-wider uppercase">Physician EHR</p>
          </div>
        </div>

        {/* Doctor Identity */}
        <div className="p-4 border-b border-slate-800 bg-slate-850">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-medicore-600 text-white font-bold flex items-center justify-center text-sm shadow-xs">
              {user?.full_name ? user.full_name.replace("Dr. ", "").split(" ").map(n => n[0]).join("") : "MD"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold text-white truncate">{user?.full_name}</p>
              <p className="text-[11px] text-medicore-400 font-medium truncate">Board Certified Specialist</p>
            </div>
          </div>
        </div>

        {/* Nav Links */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition ${
                  isActive
                    ? "bg-medicore-600 text-white font-bold shadow-xs"
                    : item.highlight
                    ? "text-medicore-400 hover:bg-slate-800"
                    : "text-slate-400 hover:bg-slate-800 hover:text-white"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-white" : item.highlight ? "text-medicore-400" : "text-slate-400"}`} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>

        <div className="p-3 border-t border-slate-800">
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold text-rose-400 hover:bg-slate-800 transition"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out of EHR</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 lg:pl-64 flex flex-col min-h-screen">
        <header className="lg:hidden h-16 bg-slate-900 border-b border-slate-800 px-4 flex items-center justify-between sticky top-0 z-30 text-white">
          <div className="flex items-center gap-2">
            <button onClick={() => setMobileNavOpen(!mobileNavOpen)} className="p-2 text-slate-300">
              {mobileNavOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
            <span className="font-bold text-white text-sm">Physician EHR</span>
          </div>
          <button onClick={logout} className="text-xs text-rose-400 font-semibold">Sign Out</button>
        </header>

        {mobileNavOpen && (
          <div className="lg:hidden bg-slate-900 border-b border-slate-800 p-4 space-y-2 text-slate-300">
            {navItems.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                onClick={() => setMobileNavOpen(false)}
                className="block p-2 rounded-lg text-sm font-medium hover:bg-slate-800 text-slate-200"
              >
                {item.name}
              </Link>
            ))}
          </div>
        )}

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
