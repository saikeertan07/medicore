"use client";

import React, { useState, useEffect } from "react";
import { AdminLayout } from "@/components/layout/admin-layout";
import { api } from "@/lib/api";
import { AuditLogItem } from "@/types";
import { History, Shield, Filter, Search } from "lucide-react";

export default function AdminAuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [searchAction, setSearchAction] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get<AuditLogItem[]>("/audit-logs?limit=100")
      .then(setLogs)
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  const filteredLogs = logs.filter(l =>
    l.action?.toLowerCase().includes(searchAction.toLowerCase()) ||
    l.resource_type?.toLowerCase().includes(searchAction.toLowerCase()) ||
    l.user_email?.toLowerCase().includes(searchAction.toLowerCase())
  );

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Security & Compliance Audit Trail</h1>
          <p className="text-xs text-slate-500 mt-1">Tamper-resistant append-only security logs for user authentication, bookings, and AI tool operations.</p>
        </div>

        {/* Filter Bar */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-3">
          <Search className="w-5 h-5 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Filter audit logs by action (e.g. APPOINTMENT_CREATE, USER_LOGIN, AI_TOOL_EXECUTE)..."
            value={searchAction}
            onChange={(e) => setSearchAction(e.target.value)}
            className="w-full text-xs sm:text-sm outline-none text-slate-800 placeholder-slate-400 bg-transparent"
          />
        </div>

        {isLoading ? (
          <div className="text-center py-12 text-xs text-slate-400">Loading audit records...</div>
        ) : (
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                    <th className="p-4">Timestamp (UTC)</th>
                    <th className="p-4">Action</th>
                    <th className="p-4">Actor</th>
                    <th className="p-4">Resource</th>
                    <th className="p-4">Resource ID</th>
                    <th className="p-4">IP Address</th>
                    <th className="p-4">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {filteredLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50/60 transition">
                      <td className="p-4 text-slate-500 text-[11px] whitespace-nowrap">
                        {new Date(log.created_at).toISOString().replace("T", " ").substring(0, 19)}
                      </td>
                      <td className="p-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          log.action.includes("CREATE") || log.action.includes("REGISTER") ? "bg-emerald-50 text-emerald-700" :
                          log.action.includes("CANCEL") ? "bg-rose-50 text-rose-700" :
                          log.action.includes("AI") ? "bg-purple-50 text-purple-700" : "bg-slate-100 text-slate-700"
                        }`}>
                          {log.action}
                        </span>
                      </td>
                      <td className="p-4 text-slate-800 font-sans">{log.user_email || "System"}</td>
                      <td className="p-4 text-slate-600">{log.resource_type}</td>
                      <td className="p-4 text-slate-500">#{log.resource_id || "-"}</td>
                      <td className="p-4 text-slate-400 text-[11px]">{log.ip_address || "127.0.0.1"}</td>
                      <td className="p-4 text-slate-500 text-[11px] font-sans max-w-xs truncate">
                        {log.details ? JSON.stringify(log.details) : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
