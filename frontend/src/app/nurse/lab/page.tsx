"use client";

import React, { useState, useEffect } from "react";
import { NurseLayout } from "@/components/layout/nurse-layout";
import { api } from "@/lib/api";
import { 
  LabOrder, LabOrderItem, LabSample, LabTestDefinition, 
  LabOrderPriority, AbnormalFlag 
} from "@/types";
import { 
  Activity, TestTube2, FlaskConical, CheckCircle2, AlertTriangle, 
  Clock, ShieldCheck, XCircle, RefreshCw, ChevronRight, Plus, AlertCircle, FileText
} from "lucide-react";

export default function NurseLabWorkbenchPage() {
  const [orders, setOrders] = useState<LabOrder[]>([]);
  const [activeTab, setActiveTab] = useState<"COLLECTION" | "INTAKE" | "ENTRY">("COLLECTION");
  const [isLoading, setIsLoading] = useState(true);
  const [statusMsg, setStatusMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Collection State
  const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null);
  const [selectedItemIds, setSelectedItemIds] = useState<number[]>([]);
  const [specimenType, setSpecimenType] = useState<string>("Venous Blood");
  const [isCollecting, setIsCollecting] = useState(false);

  // Reception / Rejection State
  const [rejectModalSample, setRejectModalSample] = useState<LabSample | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");

  // Result Entry State
  const [entryModalItem, setEntryModalItem] = useState<LabOrderItem | null>(null);
  const [resultValue, setResultValue] = useState("");
  const [resultNumeric, setResultNumeric] = useState("");
  const [resultUnit, setResultUnit] = useState("");
  const [resultRefRange, setResultRefRange] = useState("");
  const [resultFlag, setResultFlag] = useState<AbnormalFlag>("NORMAL");
  const [resultComments, setResultComments] = useState("");
  const [isSubmittingResult, setIsSubmittingResult] = useState(false);

  const loadData = () => {
    setIsLoading(true);
    api.get<LabOrder[]>("/lab/orders")
      .then(res => {
        setOrders(res || []);
        setStatusMsg(null);
      })
      .catch(err => {
        setStatusMsg({ type: "error", text: err.message || "Failed to load laboratory queue." });
      })
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  // Filter items for collection
  const pendingCollectionOrders = orders.filter(o => 
    o.status === "ORDERED" || o.status === "PARTIALLY_COLLECTED" || 
    o.items.some(i => i.status === "PENDING")
  );

  // Samples needing intake (COLLECTED)
  const allSamples: { order: LabOrder; sample: LabSample }[] = [];
  orders.forEach(o => {
    o.samples.forEach(s => {
      allSamples.push({ order: o, sample: s });
    });
  });
  const samplesForIntake = allSamples.filter(item => item.sample.status === "COLLECTED");

  // Items ready for result entry (RECEIVED or PROCESSING)
  const itemsForEntry: { order: LabOrder; item: LabOrderItem }[] = [];
  orders.forEach(o => {
    o.items.forEach(i => {
      if (i.status === "RECEIVED" || i.status === "PROCESSING") {
        itemsForEntry.push({ order: o, item: i });
      }
    });
  });

  const handleCollect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrderId || selectedItemIds.length === 0) return;

    setIsCollecting(true);
    setStatusMsg(null);
    try {
      const res = await api.post<LabSample>(`/lab/orders/${selectedOrderId}/samples`, {
        specimen_type: specimenType,
        item_ids: selectedItemIds
      });
      setStatusMsg({ 
        type: "success", 
        text: `Specimen collected successfully! Accession number: ${res.accession_number}` 
      });
      setSelectedOrderId(null);
      setSelectedItemIds([]);
      loadData();
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Failed to collect specimen." });
    } finally {
      setIsCollecting(false);
    }
  };

  const handleReceiveSample = async (sampleId: number) => {
    try {
      await api.post(`/lab/samples/${sampleId}/receive`, { notes: "Received at central accessioning desk" });
      setStatusMsg({ type: "success", text: "Specimen logged as RECEIVED into laboratory analyzer queue." });
      loadData();
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Failed to receive specimen." });
    }
  };

  const handleRejectSample = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectModalSample || !rejectionReason.trim()) return;

    try {
      await api.post(`/lab/samples/${rejectModalSample.id}/reject`, {
        rejection_reason: rejectionReason.trim()
      });
      setStatusMsg({ type: "success", text: "Specimen rejected. Linked order items reverted for redraw." });
      setRejectModalSample(null);
      setRejectionReason("");
      loadData();
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Failed to reject specimen." });
    }
  };

  const handleOpenResultModal = (item: LabOrderItem) => {
    setEntryModalItem(item);
    setResultValue("");
    setResultNumeric("");
    setResultUnit("");
    setResultRefRange("");
    setResultFlag("NORMAL");
    setResultComments("");
  };

  const handleSubmitResult = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!entryModalItem || !resultValue.trim()) return;

    setIsSubmittingResult(true);
    setStatusMsg(null);
    try {
      await api.post(`/lab/order-items/${entryModalItem.id}/results`, {
        value: resultValue.trim(),
        numeric_value: resultNumeric ? parseFloat(resultNumeric) : undefined,
        unit: resultUnit.trim() || undefined,
        reference_range: resultRefRange.trim() || undefined,
        abnormal_flag: resultFlag,
        comments: resultComments.trim() || undefined
      });
      setStatusMsg({ type: "success", text: "Diagnostic test result entered successfully. Ready for physician verification." });
      setEntryModalItem(null);
      loadData();
    } catch (err: any) {
      setStatusMsg({ type: "error", text: err.message || "Failed to enter laboratory result." });
    } finally {
      setIsSubmittingResult(false);
    }
  };

  return (
    <NurseLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-xl bg-purple-50 text-purple-600">
                <FlaskConical className="w-5 h-5" />
              </span>
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">Clinical Laboratory Workbench</h1>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Phlebotomy specimen collection, laboratory accessioning intake, and analyzer result entry.
            </p>
          </div>
          <button
            onClick={loadData}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-slate-600 bg-slate-50 hover:bg-slate-100 rounded-xl border border-slate-200 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh Queue</span>
          </button>
        </div>

        {statusMsg && (
          <div className={`p-4 rounded-xl text-xs flex items-center gap-2 border ${
            statusMsg.type === "success" ? "bg-emerald-50 text-emerald-800 border-emerald-200" : "bg-rose-50 text-rose-800 border-rose-200"
          }`}>
            {statusMsg.type === "success" ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
            <span>{statusMsg.text}</span>
          </div>
        )}

        {/* Operational Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div 
            onClick={() => setActiveTab("COLLECTION")}
            className={`p-4 rounded-2xl border cursor-pointer transition ${
              activeTab === "COLLECTION" ? "bg-purple-50/50 border-purple-300 ring-2 ring-purple-500/20" : "bg-white border-slate-200 hover:border-slate-300"
            }`}
          >
            <div className="flex justify-between items-start">
              <div>
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Specimen Collection</span>
                <span className="text-2xl font-black text-slate-900 mt-1 block">
                  {pendingCollectionOrders.reduce((acc, o) => acc + o.items.filter(i => i.status === "PENDING").length, 0)}
                </span>
                <span className="text-[11px] text-purple-700 font-medium">Draws pending</span>
              </div>
              <span className="p-2.5 bg-purple-100 text-purple-700 rounded-xl">
                <TestTube2 className="w-5 h-5" />
              </span>
            </div>
          </div>

          <div 
            onClick={() => setActiveTab("INTAKE")}
            className={`p-4 rounded-2xl border cursor-pointer transition ${
              activeTab === "INTAKE" ? "bg-blue-50/50 border-blue-300 ring-2 ring-blue-500/20" : "bg-white border-slate-200 hover:border-slate-300"
            }`}
          >
            <div className="flex justify-between items-start">
              <div>
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Lab Intake & QC</span>
                <span className="text-2xl font-black text-slate-900 mt-1 block">
                  {samplesForIntake.length}
                </span>
                <span className="text-[11px] text-blue-700 font-medium">Samples awaiting reception</span>
              </div>
              <span className="p-2.5 bg-blue-100 text-blue-700 rounded-xl">
                <Activity className="w-5 h-5" />
              </span>
            </div>
          </div>

          <div 
            onClick={() => setActiveTab("ENTRY")}
            className={`p-4 rounded-2xl border cursor-pointer transition ${
              activeTab === "ENTRY" ? "bg-emerald-50/50 border-emerald-300 ring-2 ring-emerald-500/20" : "bg-white border-slate-200 hover:border-slate-300"
            }`}
          >
            <div className="flex justify-between items-start">
              <div>
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Result Entry</span>
                <span className="text-2xl font-black text-slate-900 mt-1 block">
                  {itemsForEntry.length}
                </span>
                <span className="text-[11px] text-emerald-700 font-medium">Tests awaiting result entry</span>
              </div>
              <span className="p-2.5 bg-emerald-100 text-emerald-700 rounded-xl">
                <ShieldCheck className="w-5 h-5" />
              </span>
            </div>
          </div>
        </div>

        {/* Tab 1: Specimen Collection */}
        {activeTab === "COLLECTION" && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <TestTube2 className="w-4 h-4 text-purple-600" />
                <span>Pending Phlebotomy & Specimen Collection</span>
              </h2>
              <p className="text-xs text-slate-500">Collect specimens for ordered lab items and generate accession barcodes.</p>
            </div>

            {pendingCollectionOrders.length === 0 ? (
              <div className="text-center py-8 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-xs text-slate-400">
                No orders pending specimen collection.
              </div>
            ) : (
              <div className="space-y-4">
                {pendingCollectionOrders.map(order => {
                  const pendingItems = order.items.filter(i => i.status === "PENDING");
                  const isSelectedOrder = selectedOrderId === order.id;

                  return (
                    <div key={order.id} className="border border-slate-200 rounded-xl p-4 space-y-3 bg-slate-50/30">
                      <div className="flex flex-wrap justify-between items-center gap-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-slate-900">{order.order_number}</span>
                          <span className="text-xs font-semibold text-slate-800">• Patient: {order.patient_name}</span>
                          <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded ${
                            order.priority === "STAT" ? "bg-rose-100 text-rose-800" :
                            order.priority === "URGENT" ? "bg-amber-100 text-amber-800" :
                            "bg-slate-200 text-slate-700"
                          }`}>
                            {order.priority}
                          </span>
                        </div>
                        <span className="text-[11px] text-slate-500">Ordered by Dr. {order.doctor_name}</span>
                      </div>

                      {order.clinical_indication && (
                        <p className="text-xs text-slate-600 italic">Indication: {order.clinical_indication}</p>
                      )}

                      {/* Pending Items Checkbox List */}
                      <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-2">
                        <span className="text-[11px] font-bold text-slate-700 block">Pending Tests to Draw:</span>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {pendingItems.map(item => {
                            const isChecked = isSelectedOrder && selectedItemIds.includes(item.id);
                            return (
                              <label
                                key={item.id}
                                className={`flex items-center gap-2 p-2 rounded-lg border text-xs cursor-pointer ${
                                  isChecked ? "bg-purple-50 border-purple-300" : "bg-slate-50/50 border-slate-200"
                                }`}
                              >
                                <input
                                  type="checkbox"
                                  checked={isChecked}
                                  onChange={() => {
                                    if (!isSelectedOrder) {
                                      setSelectedOrderId(order.id);
                                      setSelectedItemIds([item.id]);
                                    } else {
                                      setSelectedItemIds(prev => 
                                        isChecked ? prev.filter(id => id !== item.id) : [...prev, item.id]
                                      );
                                    }
                                  }}
                                  className="rounded text-purple-600 focus:ring-purple-500"
                                />
                                <div className="min-w-0">
                                  <strong className="text-slate-800">{item.test_name}</strong>
                                  <span className="font-mono text-[10px] text-slate-500 ml-1.5 bg-slate-200 px-1 rounded">{item.test_code}</span>
                                </div>
                              </label>
                            );
                          })}
                        </div>
                      </div>

                      {/* Collection Action Bar if this order has selections */}
                      {isSelectedOrder && selectedItemIds.length > 0 && (
                        <form onSubmit={handleCollect} className="p-3 bg-purple-50 border border-purple-200 rounded-xl flex flex-wrap items-center justify-between gap-3">
                          <div className="flex items-center gap-3">
                            <span className="text-xs font-bold text-purple-900">Specimen Type:</span>
                            <select
                              value={specimenType}
                              onChange={e => setSpecimenType(e.target.value)}
                              className="px-3 py-1.5 text-xs border border-purple-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                            >
                              <option value="Venous Blood">Venous Blood</option>
                              <option value="Serum">Serum</option>
                              <option value="Plasma">Plasma</option>
                              <option value="Capillary Blood">Capillary Blood</option>
                              <option value="Urine">Urine</option>
                            </select>
                            <span className="text-xs text-purple-700">({selectedItemIds.length} items selected)</span>
                          </div>

                          <button
                            type="submit"
                            disabled={isCollecting}
                            className="bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold px-4 py-2 rounded-xl transition flex items-center gap-1.5 shadow-sm"
                          >
                            <TestTube2 className="w-3.5 h-3.5" />
                            <span>{isCollecting ? "Generating Accession..." : "Confirm Collection & Generate Accession"}</span>
                          </button>
                        </form>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Lab Intake & QC */}
        {activeTab === "INTAKE" && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Activity className="w-4 h-4 text-blue-600" />
                <span>Central Accessioning & Specimen QC Reception</span>
              </h2>
              <p className="text-xs text-slate-500">Log specimen arrival in the laboratory or reject unsuitable specimens (hemolysis, clotting).</p>
            </div>

            {samplesForIntake.length === 0 ? (
              <div className="text-center py-8 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-xs text-slate-400">
                No collected specimens currently in transit.
              </div>
            ) : (
              <div className="space-y-3">
                {samplesForIntake.map(({ order, sample }) => (
                  <div key={sample.id} className="p-4 border border-slate-200 rounded-xl flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-slate-50/50">
                    <div>
                      <div className="flex items-center gap-2">
                        <strong className="font-mono text-xs text-blue-900 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded">
                          {sample.accession_number}
                        </strong>
                        <span className="text-xs font-semibold text-slate-800">{sample.specimen_type}</span>
                        <span className="text-xs text-slate-500">• Order: {order.order_number}</span>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-1">
                        Patient: <strong>{order.patient_name}</strong> • Collected: {sample.collected_at ? new Date(sample.collected_at).toLocaleTimeString() : "N/A"}
                      </p>
                    </div>

                    <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                      <button
                        type="button"
                        onClick={() => handleReceiveSample(sample.id)}
                        className="px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-sm"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Receive into Lab</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setRejectModalSample(sample)}
                        className="px-3.5 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-xl text-xs font-bold transition flex items-center gap-1.5"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        <span>Reject Specimen</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Diagnostic Result Entry */}
        {activeTab === "ENTRY" && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Diagnostic Test Result Entry</span>
              </h2>
              <p className="text-xs text-slate-500">Record measured laboratory test values and abnormal classification flags.</p>
            </div>

            {itemsForEntry.length === 0 ? (
              <div className="text-center py-8 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-xs text-slate-400">
                No laboratory items currently in processing or awaiting result entry.
              </div>
            ) : (
              <div className="space-y-3">
                {itemsForEntry.map(({ order, item }) => (
                  <div key={item.id} className="p-4 border border-slate-200 rounded-xl flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-slate-50/50">
                    <div>
                      <div className="flex items-center gap-2">
                        <strong className="text-xs font-bold text-slate-900">{item.test_name}</strong>
                        <span className="font-mono text-[10px] bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded">
                          {item.test_code}
                        </span>
                        <span className="font-mono text-[10px] bg-purple-50 text-purple-700 border border-purple-200 px-1.5 py-0.5 rounded">
                          {item.sample_accession || "Accession Linked"}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-1">
                        Patient: <strong>{order.patient_name}</strong> • Order: {order.order_number}
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleOpenResultModal(item)}
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-sm"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Enter Measured Result</span>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Specimen Rejection Modal */}
        {rejectModalSample && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
              <div className="flex items-center gap-3 text-rose-600">
                <XCircle className="w-6 h-6" />
                <div>
                  <h3 className="font-bold text-base text-slate-900">Reject Specimen</h3>
                  <p className="text-xs text-slate-500 font-mono">{rejectModalSample.accession_number}</p>
                </div>
              </div>

              <form onSubmit={handleRejectSample} className="space-y-3">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Clinical Reason for Rejection * (Required)</label>
                  <textarea
                    rows={3}
                    required
                    value={rejectionReason}
                    onChange={e => setRejectionReason(e.target.value)}
                    placeholder="Specify defect (e.g. Gross hemolysis, clotted EDTA tube, insufficient volume, incorrect container)..."
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-rose-500"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setRejectModalSample(null)}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-xl text-xs font-bold bg-rose-600 hover:bg-rose-700 text-white transition shadow-sm"
                  >
                    Confirm Rejection
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Result Entry Modal */}
        {entryModalItem && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
              <div className="flex items-center gap-3 text-emerald-600">
                <ShieldCheck className="w-6 h-6" />
                <div>
                  <h3 className="font-bold text-base text-slate-900">Enter Measured Test Result</h3>
                  <p className="text-xs text-slate-500">{entryModalItem.test_name} ({entryModalItem.test_code})</p>
                </div>
              </div>

              <form onSubmit={handleSubmitResult} className="space-y-3 pt-1">
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-700">Measured Value *</label>
                    <input
                      type="text"
                      required
                      value={resultValue}
                      onChange={e => {
                        setResultValue(e.target.value);
                        if (!isNaN(Number(e.target.value)) && e.target.value.trim() !== "") {
                          setResultNumeric(e.target.value);
                        }
                      }}
                      placeholder="e.g. 13.8 or Positive"
                      className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-700">Abnormal Flag</label>
                    <select
                      value={resultFlag}
                      onChange={e => setResultFlag(e.target.value as AbnormalFlag)}
                      className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
                    >
                      <option value="NORMAL">NORMAL</option>
                      <option value="HIGH">HIGH</option>
                      <option value="LOW">LOW</option>
                      <option value="ABNORMAL">ABNORMAL</option>
                      <option value="CRITICAL">CRITICAL</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-700">Unit (Optional)</label>
                    <input
                      type="text"
                      value={resultUnit}
                      onChange={e => setResultUnit(e.target.value)}
                      placeholder="e.g. g/dL or mg/dL"
                      className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-slate-700">Reference Range (Optional)</label>
                    <input
                      type="text"
                      value={resultRefRange}
                      onChange={e => setResultRefRange(e.target.value)}
                      placeholder="e.g. 12.0 - 17.5 g/dL"
                      className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Laboratory Comments / Technologist Notes</label>
                  <textarea
                    rows={2}
                    value={resultComments}
                    onChange={e => setResultComments(e.target.value)}
                    placeholder="e.g. Calibrated automated run, smear confirmed..."
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setEntryModalItem(null)}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmittingResult}
                    className="px-5 py-2 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white transition shadow-sm"
                  >
                    {isSubmittingResult ? "Saving..." : "Save Result (Draft)"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </NurseLayout>
  );
}
