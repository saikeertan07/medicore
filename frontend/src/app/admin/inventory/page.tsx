"use client";

import React, { useState, useEffect } from "react";
import { AdminLayout } from "@/components/layout/admin-layout";
import { api } from "@/lib/api";
import { Package, AlertTriangle, CheckCircle2, Search } from "lucide-react";

export default function AdminInventoryPage() {
  const [items, setItems] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get<any[]>("/inventory")
      .then(setItems)
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  const filtered = items.filter(i =>
    i.item_name?.toLowerCase().includes(search.toLowerCase()) ||
    i.category?.toLowerCase().includes(search.toLowerCase()) ||
    i.supplier?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Hospital Supply & Inventory</h1>
          <p className="text-xs text-slate-500 mt-1">Pharmaceuticals, emergency medications, surgical consumables, and PPE stock monitoring.</p>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-3">
          <Search className="w-5 h-5 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Search items by name, category, or supplier..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full text-xs sm:text-sm outline-none text-slate-800 placeholder-slate-400 bg-transparent"
          />
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                <th className="p-4">Item Name</th>
                <th className="p-4">Category</th>
                <th className="p-4">Quantity on Hand</th>
                <th className="p-4">Reorder Level</th>
                <th className="p-4">Supplier</th>
                <th className="p-4">Stock Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/60 transition">
                  <td className="p-4 font-bold text-slate-900">{item.item_name}</td>
                  <td className="p-4 text-slate-600">{item.category}</td>
                  <td className="p-4 font-bold text-slate-900">{item.quantity} {item.unit}</td>
                  <td className="p-4 text-slate-500">{item.reorder_level} {item.unit}</td>
                  <td className="p-4 text-slate-600">{item.supplier || "Standard Supply"}</td>
                  <td className="p-4">
                    <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold ${
                      item.status === "IN_STOCK" ? "bg-emerald-50 text-emerald-700 border border-emerald-200" :
                      item.status === "LOW_STOCK" ? "bg-amber-50 text-amber-700 border border-amber-200" : "bg-rose-50 text-rose-700 border border-rose-200"
                    }`}>
                      {item.status}
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
