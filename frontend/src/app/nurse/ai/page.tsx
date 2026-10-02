"use client";

import React, { useState, useEffect, useRef } from "react";
import { NurseLayout } from "@/components/layout/nurse-layout";
import { api } from "@/lib/api";
import { AIChatMessage } from "@/types";
import { 
  HeartPulse, Send, Sparkles, AlertCircle, 
  CheckCircle2, Clock, Trash2, ShieldCheck, Activity, Siren, FileText
} from "lucide-react";

export default function NurseAIChatPage() {
  const [messages, setMessages] = useState<AIChatMessage[]>([
    {
      id: "welcome-nurse",
      sender: "assistant",
      content: "Welcome to the **Nurse Clinical Intelligence AI**. I can assist with:\n\n" +
        "• **NEWS2 Deterioration Scoring**: Calculate early warning scores from acute patient vitals.\n" +
        "• **SBAR Shift Handovers**: Synthesize structured Situation-Background-Assessment-Recommendation transfer reports.\n" +
        "• **ACLS Guidance**: Immediate emergency protocols and drug timer advice for Code Blue scenarios.\n" +
        "• **Triage Roster**: View scheduled and acute patients awaiting nursing intake.\n\n" +
        "⚠️ *Clinical Notice: All AI scores and handover digests require professional nursing clinical verification.*",
      created_at: new Date().toISOString()
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const suggestedPrompts = [
    "Calculate triage score for BP 85, HR 135, RR 26, SpO2 90",
    "Draft SBAR handover for patient 1",
    "Show patients in the triage queue",
    "Review ACLS resuscitation protocol for V-Fib"
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
    <NurseLayout>
      <div className="h-[calc(100vh-8rem)] flex flex-col bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-teal-600 flex items-center justify-center text-white shadow-sm">
              <HeartPulse className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-bold text-slate-900 text-sm">Nursing Clinical Operations AI</h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-teal-50 text-teal-700 border border-teal-200">
                  Triage & SBAR Copilot
                </span>
              </div>
              <p className="text-[11px] text-slate-400">NEWS2 Scoring, ACLS Guidance, & Joint Commission SBAR Handovers</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-[11px] font-semibold">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>Prompt Firewall Active</span>
            </div>
            <button
              onClick={() => setMessages([{
                id: "welcome-reset",
                sender: "assistant",
                content: "Nursing assistant session reset. How may I assist your shift?",
                created_at: new Date().toISOString()
              }])}
              className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition"
              title="Reset Session"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-50/30">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex flex-col ${m.sender === "user" ? "items-end" : "items-start"}`}
            >
              <div
                className={`max-w-2xl px-5 py-3.5 rounded-2xl text-xs leading-relaxed whitespace-pre-wrap shadow-sm ${
                  m.sender === "user"
                    ? "bg-teal-600 text-white rounded-br-none"
                    : "bg-white text-slate-800 border border-slate-200/80 rounded-bl-none"
                }`}
              >
                {m.content}

                {/* Display tool execution pills */}
                {m.tool_calls && m.tool_calls.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-slate-100 flex flex-wrap gap-1.5">
                    {m.tool_calls.map((t: any, idx: number) => (
                      <span
                        key={idx}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-teal-50 text-teal-700 text-[10px] font-semibold border border-teal-200"
                      >
                        <Activity className="w-3 h-3" />
                        Executed: {t.tool}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <span className="text-[10px] text-slate-400 mt-1 px-1">
                {m.sender === "user" ? "You" : "MediCore AI"} • {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          ))}

          {isLoading && (
            <div className="flex items-center gap-2 text-teal-600 bg-teal-50/60 border border-teal-200/50 px-4 py-2.5 rounded-2xl w-fit text-xs font-medium animate-pulse">
              <Sparkles className="w-4 h-4 animate-spin" />
              <span>Analyzing clinical metrics & querying nursing registry...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Prompts */}
        <div className="px-6 py-2.5 bg-white border-t border-slate-100 flex items-center gap-2 overflow-x-auto">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider shrink-0 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-teal-500" /> Suggested:
          </span>
          {suggestedPrompts.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(prompt)}
              className="text-[11px] bg-slate-50 hover:bg-teal-50 hover:text-teal-700 text-slate-600 border border-slate-200 px-3 py-1 rounded-full whitespace-nowrap transition"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-4 bg-white border-t border-slate-100">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-3"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask for NEWS2 calculation, SBAR shift handover, or triage queue..."
              disabled={isLoading}
              className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="p-2.5 bg-teal-600 hover:bg-teal-500 text-white rounded-xl shadow-md transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>

      </div>
    </NurseLayout>
  );
}
