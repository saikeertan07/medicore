"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { 
  Activity, LayoutDashboard, Calendar, Stethoscope, FileText, 
  FileCheck, Pill, Bell, User, Bot, LogOut, Menu, X, ChevronRight
} from "lucide-react";

export function PatientLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      api.get<{ unread_count: number }>("/notifications/unread-count")
        .then(res => setUnreadCount(res.unread_count))
        .catch(() => {});
    }
  }, [isAuthenticated, pathname]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-500 text-sm">
        Verifying patient authentication...
      </div>
    );
  }

  const navItems = [
    { name: "Dashboard", href: "/patient/dashboard", icon: LayoutDashboard },
    { name: "Appointments", href: "/patient/appointments", icon: Calendar },
    { name: "Clinical Records", href: "/patient/records", icon: FileCheck },
    { name: "Find Doctors", href: "/patient/doctors", icon: Stethoscope },
    { name: "Medical Documents", href: "/patient/documents", icon: FileText },
    { name: "Clinical Reports", href: "/patient/reports", icon: FileText },
    { name: "Prescriptions", href: "/patient/prescriptions", icon: Pill },
    { name: "Notifications", href: "/patient/notifications", icon: Bell, badge: unreadCount },
    { name: "Medical Profile", href: "/patient/profile", icon: User },
    { name: "AI Health Assistant", href: "/patient/ai", icon: Bot, highlight: true },
  ];

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex flex-col w-64 bg-white border-r border-slate-200 fixed inset-y-0 z-40">
        <div className="h-16 px-6 flex items-center gap-3 border-b border-slate-100">
          <div className="w-9 h-9 rounded-xl bg-medicore-600 flex items-center justify-center text-white shadow-sm">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-slate-900 text-base">MediCore<span className="text-medicore-600">AI</span></span>
            <p className="text-[10px] text-slate-400 font-semibold tracking-wider uppercase">Patient Portal</p>
          </div>
        </div>

        {/* User Card */}
        <div className="p-4 border-b border-slate-100 bg-slate-50/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-medicore-100 text-medicore-700 font-bold flex items-center justify-center text-sm">
              {user?.full_name ? user.full_name.split(" ").map(n => n[0]).join("") : "P"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold text-slate-900 truncate">{user?.full_name}</p>
              <p className="text-[11px] text-slate-400 truncate">{user?.email}</p>
            </div>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition ${
                  isActive
                    ? "bg-medicore-50 text-medicore-700 font-bold"
                    : item.highlight
                    ? "text-medicore-600 hover:bg-medicore-50/60"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? "text-medicore-600" : item.highlight ? "text-medicore-500" : "text-slate-400"}`} />
                  <span>{item.name}</span>
                </div>
                {item.badge && item.badge > 0 ? (
                  <span className="px-2 py-0.5 rounded-full text-[10px] bg-rose-500 text-white font-bold">
                    {item.badge}
                  </span>
                ) : null}
              </Link>
            );
          })}
        </nav>

        <div className="p-3 border-t border-slate-100">
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold text-rose-600 hover:bg-rose-50 transition"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 lg:pl-64 flex flex-col min-h-screen">
        {/* Mobile Header */}
        <header className="lg:hidden h-16 bg-white border-b border-slate-200 px-4 flex items-center justify-between sticky top-0 z-30">
          <div className="flex items-center gap-2">
            <button onClick={() => setMobileNavOpen(!mobileNavOpen)} className="p-2 text-slate-600">
              {mobileNavOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
            <span className="font-bold text-slate-900 text-sm">MediCore Patient</span>
          </div>
          <button onClick={logout} className="text-xs text-rose-600 font-semibold">Sign Out</button>
        </header>

        {/* Mobile Nav Dropdown */}
        {mobileNavOpen && (
          <div className="lg:hidden bg-white border-b border-slate-200 p-4 space-y-2">
            {navItems.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                onClick={() => setMobileNavOpen(false)}
                className="flex items-center justify-between p-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                <span>{item.name}</span>
                {item.badge && item.badge > 0 && <span className="bg-rose-500 text-white px-2 py-0.5 rounded-full text-xs">{item.badge}</span>}
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
