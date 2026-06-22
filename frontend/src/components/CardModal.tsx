"use client";

import { useEffect, useRef, useState } from "react";
import type { Card } from "@/lib/kanban";
import { updateCard } from "@/lib/api";

const PRIORITY_OPTIONS: Array<{ value: "low" | "medium" | "high"; label: string; color: string }> = [
  { value: "low", label: "Low", color: "text-emerald-600 bg-emerald-50 border-emerald-200" },
  { value: "medium", label: "Medium", color: "text-amber-600 bg-amber-50 border-amber-200" },
  { value: "high", label: "High", color: "text-red-600 bg-red-50 border-red-200" },
];

const LABEL_OPTIONS = ["bug", "feature", "chore", "design", "docs", ""];

type CardModalProps = {
  card: Card;
  onClose: () => void;
  onUpdate: (cardId: string, updates: Partial<Card>) => void;
};

export const CardModal = ({ card, onClose, onUpdate }: CardModalProps) => {
  const [title, setTitle] = useState(card.title);
  const [details, setDetails] = useState(card.details);
  const [dueDate, setDueDate] = useState(card.due_date ?? "");
  const [priority, setPriority] = useState<"low" | "medium" | "high">(card.priority ?? "medium");
  const [label, setLabel] = useState(card.label ?? "");
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  const titleRef = useRef<HTMLInputElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    titleRef.current?.focus();
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const handleClose = async () => {
    if (dirty) await handleSave();
    onClose();
  };

  const handleSave = async () => {
    if (!title.trim()) return;
    setSaving(true);
    const updates = {
      title: title.trim(),
      details: details.trim(),
      due_date: dueDate || null,
      priority,
      label: label || null,
    };
    try {
      await updateCard(card.id, updates as Parameters<typeof updateCard>[1]);
      onUpdate(card.id, { ...updates, due_date: dueDate || undefined, label: label || undefined });
      setDirty(false);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const mark = () => setDirty(true);

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === overlayRef.current) handleClose(); }}
    >
      <div className="absolute inset-0 bg-[var(--navy-dark)]/50 backdrop-blur-sm" />

      <div className="relative w-full max-w-lg rounded-3xl border border-[var(--stroke)] bg-white shadow-2xl">
        <div className="flex items-start justify-between border-b border-[var(--stroke)] px-6 pt-6 pb-4">
          <div className="flex-1 pr-4">
            <input
              ref={titleRef}
              value={title}
              onChange={(e) => { setTitle(e.target.value); mark(); }}
              className="w-full bg-transparent font-display text-lg font-semibold text-[var(--navy-dark)] outline-none placeholder:text-[var(--gray-text)]"
              placeholder="Card title"
            />
          </div>
          <button
            onClick={handleClose}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[var(--gray-text)] transition hover:bg-[var(--surface)] hover:text-[var(--navy-dark)]"
            aria-label="Close card"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        <div className="flex flex-col gap-5 px-6 py-5">
          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
              Details
            </label>
            <textarea
              value={details}
              onChange={(e) => { setDetails(e.target.value); mark(); }}
              rows={4}
              placeholder="Add more context, links, or notes..."
              className="w-full resize-none rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)] focus:ring-2 focus:ring-[var(--primary-blue)]/20"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                Priority
              </label>
              <div className="flex gap-2">
                {PRIORITY_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => { setPriority(opt.value); mark(); }}
                    className={`flex-1 rounded-lg border px-2 py-1.5 text-[11px] font-semibold transition ${
                      priority === opt.value
                        ? opt.color
                        : "border-[var(--stroke)] bg-[var(--surface)] text-[var(--gray-text)] hover:border-[var(--primary-blue)]"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label htmlFor="due-date" className="mb-1.5 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                Due Date
              </label>
              <input
                id="due-date"
                type="date"
                value={dueDate}
                onChange={(e) => { setDueDate(e.target.value); mark(); }}
                className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
              />
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
              Label
            </label>
            <div className="flex flex-wrap gap-2">
              {LABEL_OPTIONS.map((opt) => (
                <button
                  key={opt || "none"}
                  type="button"
                  onClick={() => { setLabel(opt); mark(); }}
                  className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${
                    label === opt
                      ? "border-[var(--secondary-purple)] bg-[var(--secondary-purple)] text-white"
                      : "border-[var(--stroke)] bg-[var(--surface)] text-[var(--gray-text)] hover:border-[var(--secondary-purple)]"
                  }`}
                >
                  {opt || "None"}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 border-t border-[var(--stroke)] px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-[var(--stroke)] px-5 py-2 text-sm text-[var(--gray-text)] transition hover:border-[var(--secondary-purple)]"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={async () => { await handleSave(); onClose(); }}
            disabled={saving || !title.trim()}
            className="rounded-xl bg-[var(--secondary-purple)] px-5 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
};
