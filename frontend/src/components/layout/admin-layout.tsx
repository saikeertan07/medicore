"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { 
  Activity, LayoutDashboard, Users, Stethoscope, Building2, 
  Calendar, Bed, Package, BarChart3, Shield, History, LogOut, 
  Menu, X, FileText
} from "lucide-react";

export function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && (!isAuthenticated || (user?.role !== "ADMIN" && user?.role !== "STAFF"))) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, user, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-500 text-sm">
        Verifying administrator permissions...
      </div>
    );
  }

  const navItems = [
    { name: "Executive Dashboard", href: "/admin/dashboard", icon: LayoutDashboard },
    { name: "Patients Registry", href: "/admin/patients", icon: Users },
    { name: "Medical Staff / Doctors", href: "/admin/doctors", icon: Stethoscope },
    { name: "Clinical Departments", href: "/admin/departments", icon: Building2 },
    { name: "Master Appointments", href: "/admin/appointments", icon: Calendar },
    { name: "Bed & Room Management", href: "/admin/rooms", icon: Bed },
    { name: "Supply & Inventory", href: "/admin/inventory", icon: Package },
    { name: "Hospital Reports", href: "/admin/reports", icon: FileText },
    { name: "Operations Analytics", href: "/admin/analytics", icon: BarChart3 },
    { name: "User Access & Roles", href: "/admin/users", icon: Shield },
    { name: "Security Audit Logs", href: "/admin/audit-logs", icon: History, highlight: true },
  ];

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex flex-col w-64 bg-slate-900 border-r border-slate-800 fixed inset-y-0 z-40 text-slate-300">
        <div className="h-16 px-6 flex items-center gap-3 border-b border-slate-800">
          <div className="w-9 h-9 rounded-xl bg-rose-600 flex items-center justify-center text-white shadow-sm">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-white text-base tracking-tight">MediCore<span className="text-rose-400">ADMIN</span></span>
            <p className="text-[10px] text-slate-400 font-semibold tracking-wider uppercase">Hospital Operations</p>
          </div>
        </div>

        {/* Identity */}
        <div className="p-4 border-b border-slate-800 bg-slate-850">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-rose-700 text-white font-bold flex items-center justify-center text-sm">
              {user?.full_name ? user.full_name.split(" ").map(n => n[0]).join("") : "AD"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold text-white truncate">{user?.full_name}</p>
              <p className="text-[11px] text-rose-300 font-medium truncate">Chief Hospital Admin</p>
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
                    ? "bg-rose-600 text-white font-bold shadow-xs"
                    : item.highlight
                    ? "text-rose-400 hover:bg-slate-800"
                    : "text-slate-400 hover:bg-slate-800 hover:text-white"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-white" : item.highlight ? "text-rose-400" : "text-slate-400"}`} />
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
            <span>Sign Out of Console</span>
          </button>
        </div>
      </aside>

      {/* Content */}
      <div className="flex-1 lg:pl-64 flex flex-col min-h-screen">
        <header className="lg:hidden h-16 bg-slate-900 border-b border-slate-800 px-4 flex items-center justify-between sticky top-0 z-30 text-white">
          <div className="flex items-center gap-2">
            <button onClick={() => setMobileNavOpen(!mobileNavOpen)} className="p-2 text-slate-300">
              {mobileNavOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
            <span className="font-bold text-white text-sm">Hospital Admin</span>
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
