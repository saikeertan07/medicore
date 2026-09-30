"use client";

import React, { useState, useEffect } from "react";
import { PatientLayout } from "@/components/layout/patient-layout";
import { api } from "@/lib/api";
import { MedicalDocument } from "@/types";
import { 
  FileText, Upload, Download, Search, MessageSquare, 
  CheckCircle2, AlertCircle, Clock, X, HelpCircle
} from "lucide-react";

export default function PatientDocumentsPage() {
  const [documents, setDocuments] = useState<MedicalDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  
  // Upload State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [tags, setTags] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Q&A State
  const [activeDocQA, setActiveDocQA] = useState<MedicalDocument | null>(null);
  const [question, setQuestion] = useState("");
  const [qaAnswer, setQaAnswer] = useState<string | null>(null);
  const [isAsking, setIsAsking] = useState(false);

  const loadDocuments = () => {
    setIsLoading(true);
    api.get<MedicalDocument[]>("/documents")
      .then(setDocuments)
      .catch(() => {})
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append("file", selectedFile);
    if (tags) formData.append("tags", tags);

    try {
      await api.upload("/documents/upload", formData);
      setUploadModalOpen(false);
      setSelectedFile(null);
      setTags("");
      loadDocuments();
    } catch (err: any) {
      setUploadError(err.message || "File upload failed.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleAskQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeDocQA || !question.trim()) return;

    setIsAsking(true);
    setQaAnswer(null);

    const formData = new FormData();
    formData.append("question", question.trim());

    try {
      const res = await api.post<{ answer: string }>(`/documents/${activeDocQA.id}/query`, formData);
      setQaAnswer(res.answer);
    } catch (err: any) {
      setQaAnswer("Failed to process question: " + err.message);
    } finally {
      setIsAsking(false);
    }
  };

  return (
    <PatientLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Medical Documents</h1>
            <p className="text-xs text-slate-500 mt-1">Upload lab results, ECGs, and imaging studies for instant AI structured clinical extraction.</p>
          </div>
          <button
            onClick={() => setUploadModalOpen(true)}
            className="bg-medicore-600 hover:bg-medicore-700 text-white font-semibold px-4 py-2.5 rounded-xl text-xs flex items-center gap-2 transition shadow-sm"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload New Document</span>
          </button>
        </div>

        {/* Documents Table / Grid */}
        {isLoading ? (
          <div className="text-center py-12 text-xs text-slate-400">Loading medical records...</div>
        ) : documents.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-xs text-slate-500">
            No medical documents uploaded yet. Click "Upload New Document" to add labs or radiology records.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {documents.map((doc) => (
              <div key={doc.id} className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col justify-between shadow-sm hover:shadow-md transition">
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-10 h-10 rounded-xl bg-medicore-50 text-medicore-600 flex items-center justify-center shrink-0">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="font-bold text-slate-900 text-sm">{doc.file_name}</h3>
                        <span className="text-[11px] text-slate-400">{doc.tags || "Clinical Diagnostic"} • {(doc.file_size / 1024).toFixed(0)} KB</span>
                      </div>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold shrink-0 ${
                      doc.status === "COMPLETED" ? "bg-emerald-50 text-emerald-700" :
                      doc.status === "PROCESSING" ? "bg-amber-50 text-amber-700 animate-pulse" : "bg-rose-50 text-rose-600"
                    }`}>
                      {doc.status}
                    </span>
                  </div>

                  <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-100 text-xs text-slate-600 space-y-1.5 mt-3">
                    <span className="font-bold text-slate-700 block text-[11px] uppercase tracking-wider">AI Clinical Summary</span>
                    <p className="leading-relaxed text-[12px]">{doc.summary || "Extraction pending..."}</p>
                  </div>

                  {doc.extracted_data?.key_findings && (
                    <div className="mt-3 space-y-1">
                      <span className="text-[10px] uppercase font-bold text-slate-400">Extracted Clinical Markers</span>
                      <ul className="text-xs text-slate-600 space-y-0.5">
                        {doc.extracted_data.key_findings.map((f: string, idx: number) => (
                          <li key={idx} className="flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-medicore-500"></span>
                            <span>{f}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
                  <button
                    onClick={() => {
                      setActiveDocQA(doc);
                      setQuestion("");
                      setQaAnswer(null);
                    }}
                    className="text-xs font-semibold text-medicore-600 hover:text-medicore-700 flex items-center gap-1.5 py-1 px-2.5 rounded-lg hover:bg-medicore-50 transition"
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    <span>Ask Document Q&A</span>
                  </button>

                  <a
                    href={`http://localhost:8000/api/v1/documents/${doc.id}/download`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs font-semibold text-slate-600 hover:text-slate-900 flex items-center gap-1.5 py-1 px-2.5 rounded-lg hover:bg-slate-100 transition"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download</span>
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* UPLOAD MODAL */}
        {uploadModalOpen && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-xl border border-slate-200">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-slate-900">Upload Medical Document</h3>
                <button onClick={() => setUploadModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {uploadError && (
                <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                  <span>{uploadError}</span>
                </div>
              )}

              <form onSubmit={handleUpload} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Select File (PDF, PNG, JPG, DOCX up to 15MB)</label>
                  <input
                    type="file"
                    required
                    accept=".pdf,.png,.jpg,.jpeg,.doc,.docx"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    className="w-full text-xs text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-medicore-50 file:text-medicore-700 hover:file:bg-medicore-100 cursor-pointer"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Tags / Category (Optional)</label>
                  <input
                    type="text"
                    placeholder="e.g., Cardiology, Bloodwork, Radiology"
                    value={tags}
                    onChange={(e) => setTags(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl border border-slate-300 text-xs outline-none focus:border-medicore-500"
                  />
                </div>

                <div className="pt-2 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setUploadModalOpen(false)}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isUploading || !selectedFile}
                    className="px-5 py-2 rounded-xl text-xs font-semibold bg-medicore-600 hover:bg-medicore-700 disabled:opacity-50 text-white transition flex items-center gap-2"
                  >
                    <span>{isUploading ? "Extracting Clinical Intelligence..." : "Upload & Analyze"}</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* DOCUMENT Q&A MODAL */}
        {activeDocQA && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-2xl max-w-xl w-full p-6 space-y-4 shadow-xl border border-slate-200">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-slate-900">Document Q&A: {activeDocQA.file_name}</h3>
                  <p className="text-xs text-slate-400">Ask questions directly about this diagnostic report's extracted findings.</p>
                </div>
                <button onClick={() => setActiveDocQA(null)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleAskQuestion} className="space-y-3">
                <div className="flex gap-2">
                  <input
                    type="text"
                    required
                    placeholder="e.g. What were my glucose levels? Is my ECG normal?"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    className="flex-1 px-3.5 py-2 rounded-xl border border-slate-300 text-xs outline-none focus:border-medicore-500"
                  />
                  <button
                    type="submit"
                    disabled={isAsking}
                    className="bg-medicore-600 hover:bg-medicore-700 disabled:opacity-50 text-white text-xs font-semibold px-4 py-2 rounded-xl transition"
                  >
                    {isAsking ? "Querying..." : "Ask"}
                  </button>
                </div>
              </form>

              {qaAnswer && (
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 space-y-2 whitespace-pre-line">
                  {qaAnswer}
                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </PatientLayout>
  );
}
