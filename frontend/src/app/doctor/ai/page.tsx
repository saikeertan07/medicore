"use client";

import React, { useState, useEffect, useRef } from "react";
import { DoctorLayout } from "@/components/layout/doctor-layout";
import { api } from "@/lib/api";
import { AIChatMessage } from "@/types";
import { 
  Bot, Send, Sparkles, CheckCircle2, Trash2, 
  Stethoscope, AlertTriangle, ShieldCheck 
} from "lucide-react";

export default function DoctorAIChatPage() {
  const [messages, setMessages] = useState<AIChatMessage[]>([
    {
      id: "welcome-doc",
      sender: "assistant",
      content: "Welcome, Doctor. I am your MediCore MD Clinical Assistant. I can assist you with patient history digests, diagnostic document analysis, clinical guidelines consultation, and drafting consultation notes.\n\n⚠️ **Clinical Notice**: All AI outputs are intended for clinical workflow assistance only and require your independent clinical verification.",
      created_at: new Date().toISOString()
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const suggestedPrompts = [
    "Summarize medical history for patient Sarah Jenkins.",
    "Review clinical findings for ECG and CMP documents.",
    "Search hospital clinical guideline for Emergency Department triage.",
    "Draft consultation notes for hypertension follow-up."
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSend = async (textToSend?: string) => {
    const messageText = (textToSend || input).trim();
    if (!messageText || isLoading) return;

    const userMsg: AIChatMessage = {
      id: Date.now().toString(),
      sender: "user",
      content: messageText,
      created_at: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await api.post<any>("/ai/chat", {
        message: messageText,
        conversation_id: conversationId
      });

      if (res.conversation_id) setConversationId(res.conversation_id);

      const assistantMsg: AIChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: "assistant",
        content: res.message,
        tool_calls: res.tool_calls,
        sources: res.sources,
        created_at: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: AIChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: "assistant",
        content: "⚠️ Clinical service query error: " + (err.message || "Unknown error"),
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <DoctorLayout>
      <div className="h-[calc(100vh-8rem)] flex flex-col bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-slate-900 flex items-center justify-center text-medicore-400 shadow-sm">
              <Stethoscope className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-bold text-slate-900 text-sm">Physician Clinical Intelligence Copilot</h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-medicore-50 text-medicore-700 border border-medicore-200">
                  Provider Mode
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Strictly verified EHR synthesis & clinical guidelines</p>
            </div>
          </div>

          <button
            onClick={() => setMessages([{
              id: "welcome-reset",
              sender: "assistant",
              content: "Clinical assistant session reset. How may I assist your workflow?",
              created_at: new Date().toISOString()
            }])}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition"
            title="Reset Session"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((m) => {
            const isUser = m.sender === "user";
            return (
              <div key={m.id} className={`flex gap-3.5 ${isUser ? "justify-end" : "justify-start"}`}>
                {!isUser && (
                  <div className="w-8 h-8 rounded-xl bg-slate-900 text-medicore-400 flex items-center justify-center shrink-0 text-xs">
                    <Stethoscope className="w-4 h-4" />
                  </div>
                )}

                <div className={`max-w-2xl space-y-2.5 ${isUser ? "items-end" : "items-start"}`}>
                  
                  {m.tool_calls && m.tool_calls.length > 0 && (
                    <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Clinical Tool Executed</span>
                      {m.tool_calls.map((t: any, idx: number) => (
                        <div key={idx} className="flex items-center gap-1.5 text-slate-700 font-mono text-[11px]">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                          <span>{t.tool}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className={`p-4 rounded-2xl text-xs sm:text-sm leading-relaxed whitespace-pre-line shadow-xs ${
                    isUser
                      ? "bg-slate-900 text-white rounded-br-none"
                      : "bg-slate-50 border border-slate-200 text-slate-800 rounded-bl-none"
                  }`}>
                    {m.content}
                  </div>
                </div>
              </div>
            );
          })}

          {isLoading && (
            <div className="flex gap-3.5 items-start">
              <div className="w-8 h-8 rounded-xl bg-slate-900 text-medicore-400 flex items-center justify-center shrink-0 text-xs">
                <Stethoscope className="w-4 h-4" />
              </div>
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-xs text-slate-500 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-medicore-600 animate-bounce"></span>
                <span className="w-2 h-2 rounded-full bg-medicore-600 animate-bounce [animation-delay:0.2s]"></span>
                <span className="w-2 h-2 rounded-full bg-medicore-600 animate-bounce [animation-delay:0.4s]"></span>
                <span className="ml-1 font-medium">Synthesizing clinical records...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Prompts */}
        <div className="px-6 py-2.5 bg-slate-50 border-t border-slate-100 flex items-center gap-2 overflow-x-auto no-scrollbar">
          <Sparkles className="w-3.5 h-3.5 text-amber-500 shrink-0" />
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider shrink-0">Clinical Queries:</span>
          {suggestedPrompts.map((p, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(p)}
              className="text-[11px] font-semibold text-slate-600 bg-white hover:bg-slate-100 border border-slate-200 px-2.5 py-1 rounded-lg shrink-0 transition"
            >
              {p}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-4 bg-white border-t border-slate-200">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-3"
          >
            <input
              type="text"
              placeholder="Query patient history, summarize documents, or search hospital clinical guidelines..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
              className="flex-1 px-4 py-3 rounded-2xl border border-slate-300 text-xs sm:text-sm outline-none focus:border-medicore-500 focus:ring-1 focus:ring-medicore-500 bg-slate-50/50"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white p-3 rounded-2xl transition shadow-sm shrink-0"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
          <div className="flex items-center justify-center gap-1.5 mt-2 text-[10px] text-amber-600 font-semibold">
            <AlertTriangle className="w-3 h-3 shrink-0" />
            <span>AI assistant output is for workflow efficiency and requires physician clinical sign-off.</span>
          </div>
        </div>

      </div>
    </DoctorLayout>
  );
}
