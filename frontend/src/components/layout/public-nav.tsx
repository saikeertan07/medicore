"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { 
  Activity, Calendar, PhoneCall, ShieldAlert, 
  User, Menu, X, ChevronRight, Stethoscope
} from "lucide-react";

export function PublicNav() {
  const { user, isAuthenticated } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const getDashboardLink = () => {
    if (!user) return "/login";
    if (user.role === "PATIENT") return "/patient/dashboard";
    if (user.role === "DOCTOR") return "/doctor/dashboard";
    if (user.role === "ADMIN") return "/admin/dashboard";
    return "/";
  };

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-slate-200">
      {/* Emergency Hotline Banner */}
      <div className="bg-slate-900 text-slate-200 text-xs py-1.5 px-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-2">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Emergency Department Active 24/7 (ESI Level 1-5 Trauma Center)</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/emergency" className="text-red-400 font-semibold hover:underline flex items-center gap-1">
              <PhoneCall className="w-3 h-3" /> Emergency: (555) 911-CORE
            </Link>
            <span className="hidden sm:inline text-slate-500">|</span>
            <span className="hidden sm:inline text-slate-400">Main Campus: 100 Medical Plaza, Metro City</span>
          </div>
        </div>
      </div>

      {/* Main Navbar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          {/* Brand Logo */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-medicore-600 flex items-center justify-center text-white shadow-md shadow-medicore-500/20 group-hover:bg-medicore-700 transition">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <span className="text-xl font-bold tracking-tight text-slate-900">MediCore<span className="text-medicore-600">AI</span></span>
              <p className="text-[10px] font-medium tracking-wide uppercase text-slate-400 -mt-1">Hospital Operating System</p>
            </div>
          </Link>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center gap-8">
            <Link href="/departments" className="text-sm font-medium text-slate-600 hover:text-medicore-600 transition">Departments</Link>
            <Link href="/doctors" className="text-sm font-medium text-slate-600 hover:text-medicore-600 transition">Doctors</Link>
            <Link href="/services" className="text-sm font-medium text-slate-600 hover:text-medicore-600 transition">Services</Link>
            <Link href="/about" className="text-sm font-medium text-slate-600 hover:text-medicore-600 transition">About</Link>
            <Link href="/faq" className="text-sm font-medium text-slate-600 hover:text-medicore-600 transition">FAQ</Link>
            <Link href="/contact" className="text-sm font-medium text-slate-600 hover:text-medicore-600 transition">Contact</Link>
          </nav>

          {/* Action Buttons */}
          <div className="hidden md:flex items-center gap-3">
            <Link 
              href="/appointments"
              className="inline-flex items-center gap-2 bg-medicore-50 text-medicore-700 hover:bg-medicore-100 font-semibold px-4 py-2 rounded-lg text-sm transition border border-medicore-200"
            >
              <Calendar className="w-4 h-4 text-medicore-600" />
              Book Appointment
            </Link>

            {isAuthenticated ? (
              <Link
                href={getDashboardLink()}
                className="inline-flex items-center gap-2 bg-medicore-600 hover:bg-medicore-700 text-white font-medium px-4 py-2 rounded-lg text-sm transition shadow-sm"
              >
                <User className="w-4 h-4" />
                {user?.role === "PATIENT" ? "Patient Portal" : (user?.role === "DOCTOR" ? "Doctor Portal" : "Admin Portal")}
              </Link>
            ) : (
              <Link
                href="/login"
                className="inline-flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white font-medium px-4 py-2 rounded-lg text-sm transition shadow-sm"
              >
                Portal Login
              </Link>
            )}
          </div>

          {/* Mobile Menu Toggle Button */}
          <div className="flex md:hidden items-center">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 text-slate-600 hover:text-slate-900 focus:outline-none"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-200 bg-white px-4 pt-3 pb-6 space-y-3">
          <Link href="/departments" onClick={() => setMobileMenuOpen(false)} className="block px-3 py-2 rounded-md text-base font-medium text-slate-700 hover:bg-slate-50">Departments</Link>
          <Link href="/doctors" onClick={() => setMobileMenuOpen(false)} className="block px-3 py-2 rounded-md text-base font-medium text-slate-700 hover:bg-slate-50">Doctors</Link>
          <Link href="/services" onClick={() => setMobileMenuOpen(false)} className="block px-3 py-2 rounded-md text-base font-medium text-slate-700 hover:bg-slate-50">Services</Link>
          <Link href="/about" onClick={() => setMobileMenuOpen(false)} className="block px-3 py-2 rounded-md text-base font-medium text-slate-700 hover:bg-slate-50">About</Link>
          <Link href="/faq" onClick={() => setMobileMenuOpen(false)} className="block px-3 py-2 rounded-md text-base font-medium text-slate-700 hover:bg-slate-50">FAQ</Link>
          <Link href="/contact" onClick={() => setMobileMenuOpen(false)} className="block px-3 py-2 rounded-md text-base font-medium text-slate-700 hover:bg-slate-50">Contact</Link>
          <Link href="/emergency" onClick={() => setMobileMenuOpen(false)} className="block px-3 py-2 rounded-md text-base font-semibold text-red-600 hover:bg-red-50">Emergency 24/7</Link>
          
          <div className="pt-2 border-t border-slate-100 flex flex-col gap-2">
            <Link 
              href="/appointments" 
              onClick={() => setMobileMenuOpen(false)}
              className="w-full text-center bg-medicore-600 text-white font-medium py-2 rounded-lg"
            >
              Book Appointment
            </Link>
            <Link 
              href={isAuthenticated ? getDashboardLink() : "/login"} 
              onClick={() => setMobileMenuOpen(false)}
              className="w-full text-center bg-slate-900 text-white font-medium py-2 rounded-lg"
            >
              {isAuthenticated ? "Go to Dashboard" : "Sign In to Portal"}
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
