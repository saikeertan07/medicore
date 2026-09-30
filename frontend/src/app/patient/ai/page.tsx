"use client";

import React, { useState, useEffect, useRef } from "react";
import { PatientLayout } from "@/components/layout/patient-layout";
import { api } from "@/lib/api";
import { AIChatMessage } from "@/types";
import { 
  Bot, Send, User, Sparkles, AlertCircle, 
  CheckCircle2, Clock, Trash2, ArrowRight, ShieldAlert 
} from "lucide-react";

export default function PatientAIChatPage() {
  const [messages, setMessages] = useState<AIChatMessage[]>([
    {
      id: "welcome",
      sender: "assistant",
      content: "Hello! I am your MediCore AI Patient Assistant. I can help you search for specialists, check live availability, manage your appointments, or answer hospital policy and insurance questions. How may I assist you today?",
      created_at: new Date().toISOString()
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const suggestedPrompts = [
    "I need a cardiologist tomorrow morning.",
    "Show my upcoming appointments.",
    "What are your inpatient visiting hours?",
    "What insurance carriers are accepted at MediCore?",
    "What documents do I need for my first visit?"
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

      if (res.conversation_id) {
        setConversationId(res.conversation_id);
      }

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
        content: "⚠️ I encountered an issue connecting to the hospital operations system: " + (err.message || "Unknown error"),
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: "welcome-reset",
        sender: "assistant",
        content: "Chat conversation cleared. How can I help you today?",
        created_at: new Date().toISOString()
      }
    ]);
    setConversationId(null);
  };

  return (
    <PatientLayout>
      <div className="h-[calc(100vh-8rem)] flex flex-col bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
        
        {/* Chat Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-medicore-600 flex items-center justify-center text-white shadow-sm">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-bold text-slate-900 text-sm">MediCore AI Patient Assistant</h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Live Operations
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Strictly verified database scheduling & hospital policy RAG</p>
            </div>
          </div>

          <button
            onClick={clearChat}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition"
            title="Clear Conversation"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>

        {/* Messages Scroll Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((m) => {
            const isUser = m.sender === "user";
            return (
              <div
                key={m.id}
                className={`flex gap-3.5 ${isUser ? "justify-end" : "justify-start"}`}
              >
                {!isUser && (
                  <div className="w-8 h-8 rounded-xl bg-medicore-50 border border-medicore-100 text-medicore-600 flex items-center justify-center shrink-0 text-xs">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div className={`max-w-2xl space-y-2.5 ${isUser ? "items-end" : "items-start"}`}>
                  
                  {/* Tool Execution Badges Indicator */}
                  {m.tool_calls && m.tool_calls.length > 0 && (
                    <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1 text-slate-600">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Backend Operations Executed</span>
                      {m.tool_calls.map((t: any, idx: number) => (
                        <div key={idx} className="flex items-center gap-1.5 text-slate-700 font-mono text-[11px]">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                          <span>{t.tool}({JSON.stringify(t.parameters)})</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Message Bubble */}
                  <div
                    className={`p-4 rounded-2xl text-xs sm:text-sm leading-relaxed whitespace-pre-line shadow-xs ${
                      isUser
                        ? "bg-medicore-600 text-white rounded-br-none"
                        : "bg-slate-50 border border-slate-200 text-slate-800 rounded-bl-none"
                    }`}
                  >
                    {m.content}
                  </div>

                  {/* Sources Cited */}
                  {m.sources && m.sources.length > 0 && (
                    <div className="text-[11px] text-slate-400 flex items-center gap-1 px-1">
                      <span>Sources:</span>
                      {m.sources.map((s: any, idx: number) => (
                        <span key={idx} className="font-semibold text-slate-600">{s.title || s.document_title}</span>
                      ))}
                    </div>
                  )}
                </div>

                {isUser && (
                  <div className="w-8 h-8 rounded-xl bg-slate-900 text-white flex items-center justify-center shrink-0 text-xs">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })}

          {isLoading && (
            <div className="flex gap-3.5 items-start">
              <div className="w-8 h-8 rounded-xl bg-medicore-50 border border-medicore-100 text-medicore-600 flex items-center justify-center shrink-0 text-xs">
                <Bot className="w-4 h-4" />
              </div>
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-xs text-slate-500 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-medicore-600 animate-bounce"></span>
                <span className="w-2 h-2 rounded-full bg-medicore-600 animate-bounce [animation-delay:0.2s]"></span>
                <span className="w-2 h-2 rounded-full bg-medicore-600 animate-bounce [animation-delay:0.4s]"></span>
                <span className="ml-1 font-medium">Checking live hospital database & policies...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Prompts */}
        <div className="px-6 py-2.5 bg-slate-50 border-t border-slate-100 flex items-center gap-2 overflow-x-auto no-scrollbar">
          <Sparkles className="w-3.5 h-3.5 text-amber-500 shrink-0" />
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider shrink-0">Try Asking:</span>
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
              placeholder="Ask about appointments, doctors, hospital policies, or lab tests..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
              className="flex-1 px-4 py-3 rounded-2xl border border-slate-300 text-xs sm:text-sm outline-none focus:border-medicore-500 focus:ring-1 focus:ring-medicore-500 bg-slate-50/50"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="bg-medicore-600 hover:bg-medicore-700 disabled:opacity-50 text-white p-3 rounded-2xl transition shadow-sm shrink-0"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
          <p className="text-[10px] text-slate-400 text-center mt-2">
            MediCore AI provides administrative scheduling and document digestion. Clinical decisions require physician review.
          </p>
        </div>

      </div>
    </PatientLayout>
  );
}
