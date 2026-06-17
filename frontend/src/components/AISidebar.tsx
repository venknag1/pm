"use client";

import { useEffect, useRef, useState } from "react";
import { sendAIMessage, type ChatMessage } from "@/lib/api";
import type { BoardData } from "@/lib/kanban";

type AISidebarProps = {
  onClose: () => void;
  onBoardUpdate: (board: BoardData) => void;
};

export const AISidebar = ({ onClose, onBoardUpdate }: AISidebarProps) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const result = await sendAIMessage(text, messages);
      setMessages((prev) => [...prev, { role: "assistant", content: result.reply }]);
      if (result.board) {
        onBoardUpdate(result.board);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end" data-testid="ai-sidebar">
      <div
        className="absolute inset-0 bg-[var(--navy-dark)]/40 backdrop-blur-[2px]"
        onClick={onClose}
        aria-hidden="true"
        data-testid="ai-sidebar-backdrop"
      />

      <div className="relative flex h-full w-[380px] flex-col bg-[var(--navy-dark)] shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/10 px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-white/40">
              AI Assistant
            </p>
            <h2 className="mt-1 text-sm font-semibold text-white">Board Chat</h2>
          </div>
          <button
            onClick={onClose}
            aria-label="Close AI sidebar"
            className="flex h-8 w-8 items-center justify-center rounded-full text-white/40 transition hover:bg-white/10 hover:text-white"
          >
            ✕
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-5">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center gap-3 pt-12">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--primary-blue)]/20">
                <span className="text-[var(--primary-blue)] text-sm font-bold">AI</span>
              </div>
              <p className="max-w-[220px] text-center text-xs leading-5 text-white/40">
                Ask me anything about your board. I can add, move, or organize your cards.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-5 ${
                      msg.role === "user"
                        ? "rounded-tr-sm bg-[var(--primary-blue)] text-white"
                        : "rounded-tl-sm bg-white/10 text-white/90"
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="rounded-2xl rounded-tl-sm bg-white/10 px-4 py-3">
                    <span className="text-xs text-white/40">Thinking...</span>
                  </div>
                </div>
              )}
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t border-white/10 p-4">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your board..."
              disabled={loading}
              aria-label="AI message input"
              className="min-w-0 flex-1 rounded-xl bg-white/10 px-4 py-3 text-sm text-white placeholder:text-white/30 outline-none focus:ring-1 focus:ring-[var(--primary-blue)] disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="rounded-xl bg-[var(--primary-blue)] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[var(--primary-blue)]/80 disabled:opacity-40"
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
