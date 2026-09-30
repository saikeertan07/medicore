"use client";

import React, { useState, useEffect } from "react";
import { PatientLayout } from "@/components/layout/patient-layout";
import { api } from "@/lib/api";
import { NotificationItem } from "@/types";
import { Bell, Check, CheckCheck, Clock } from "lucide-react";

export default function PatientNotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadNotifications = () => {
    setIsLoading(true);
    api.get<NotificationItem[]>("/notifications")
      .then(setNotifications)
      .catch(() => {})
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    loadNotifications();
  }, []);

  const markAllRead = async () => {
    await api.post("/notifications/mark-all-read");
    loadNotifications();
  };

  const markRead = async (id: number) => {
    await api.post(`/notifications/${id}/read`);
    loadNotifications();
  };

  return (
    <PatientLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Notifications & Alerts</h1>
            <p className="text-xs text-slate-500 mt-1">Real-time alerts for appointment confirmations, diagnostic test completions, and reminders.</p>
          </div>
          <button
            onClick={markAllRead}
            className="text-xs font-semibold text-medicore-600 hover:text-medicore-700 flex items-center gap-1.5 px-3 py-2 rounded-lg hover:bg-medicore-50 transition border border-medicore-200"
          >
            <CheckCheck className="w-4 h-4" />
            <span>Mark All as Read</span>
          </button>
        </div>

        {isLoading ? (
          <div className="text-center py-12 text-xs text-slate-400">Loading notifications...</div>
        ) : notifications.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-xs text-slate-500">
            No notifications at this time.
          </div>
        ) : (
          <div className="space-y-3">
            {notifications.map((n) => (
              <div
                key={n.id}
                className={`p-4 rounded-2xl border transition flex items-start justify-between gap-4 ${
                  n.is_read ? "bg-white border-slate-200" : "bg-medicore-50/40 border-medicore-200 ring-1 ring-medicore-400/20"
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 text-xs ${
                    n.is_read ? "bg-slate-100 text-slate-500" : "bg-medicore-600 text-white shadow-sm"
                  }`}>
                    <Bell className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className={`text-xs font-bold ${n.is_read ? "text-slate-700" : "text-slate-900 font-extrabold"}`}>
                      {n.title}
                    </h3>
                    <p className="text-xs text-slate-600 mt-0.5">{n.message}</p>
                    <span className="text-[10px] text-slate-400 mt-1.5 block">
                      {new Date(n.created_at).toLocaleDateString()} at {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>

                {!n.is_read && (
                  <button
                    onClick={() => markRead(n.id)}
                    className="p-1.5 text-slate-400 hover:text-medicore-600 rounded-lg hover:bg-white transition"
                    title="Mark as Read"
                  >
                    <Check className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </PatientLayout>
  );
}
