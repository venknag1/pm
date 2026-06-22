"use client";

import { useEffect, useState } from "react";
import { getMyWorkCards, type MyWorkCard } from "@/lib/api";

const PRIORITY_COLORS = {
  high: "text-red-600 bg-red-50 border-red-200",
  medium: "text-amber-600 bg-amber-50 border-amber-200",
  low: "text-emerald-600 bg-emerald-50 border-emerald-200",
};

const CARD_COLOR_MAP: Record<string, string> = {
  red: "#ef4444", orange: "#f97316", yellow: "#eab308",
  green: "#22c55e", blue: "#3b82f6", purple: "#a855f7",
};

type MyWorkViewProps = {
  onSelectBoard: (boardId: number, boardTitle: string) => void;
  onBack: () => void;
};

export const MyWorkView = ({ onSelectBoard, onBack }: MyWorkViewProps) => {
  const [cards, setCards] = useState<MyWorkCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMyWorkCards()
      .then(setCards)
      .catch(() => setError("Failed to load assigned cards"))
      .finally(() => setLoading(false));
  }, []);

  const overdue = cards.filter((c) => c.is_overdue);
  const upcoming = cards.filter((c) => !c.is_overdue && c.due_date);
  const noDueDate = cards.filter((c) => !c.due_date);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Loading...
        </p>
      </div>
    );
  }

  const CardRow = ({ card }: { card: MyWorkCard }) => (
    <div
      className="flex cursor-pointer items-start gap-3 rounded-xl border border-[var(--stroke)] bg-white/80 p-3 shadow-sm transition hover:border-[var(--primary-blue)] hover:shadow"
      onClick={() => onSelectBoard(card.board_id, card.board_title)}
    >
      {card.color && CARD_COLOR_MAP[card.color] && (
        <div className="mt-0.5 h-4 w-1 shrink-0 rounded-full" style={{ backgroundColor: CARD_COLOR_MAP[card.color] }} />
      )}
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-[var(--navy-dark)]">{card.title}</p>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-[10px]">
          <span className="text-[var(--gray-text)]">{card.board_title} &rsaquo; {card.column_title}</span>
          <span className={`rounded-full border px-2 py-0.5 font-semibold ${PRIORITY_COLORS[card.priority]}`}>
            {card.priority}
          </span>
          {card.label && (
            <span className="rounded-full border border-[var(--stroke)] bg-[var(--surface)] px-2 py-0.5 font-semibold text-[var(--gray-text)]">
              {card.label}
            </span>
          )}
          {card.due_date && (
            <span className={card.is_overdue ? "font-semibold text-red-500" : "text-[var(--gray-text)]"}>
              {card.is_overdue ? "Overdue: " : "Due: "}
              {new Date(card.due_date + "T00:00:00").toLocaleDateString()}
            </span>
          )}
          {card.story_points != null && (
            <span className="rounded-full border border-[var(--stroke)] bg-[var(--surface)] px-2 py-0.5 font-semibold text-[var(--gray-text)]">
              {card.story_points} pts
            </span>
          )}
        </div>
      </div>
    </div>
  );

  const Section = ({ title, items, accent }: { title: string; items: MyWorkCard[]; accent?: string }) => (
    items.length === 0 ? null : (
      <section>
        <h3 className={`mb-3 text-xs font-semibold uppercase tracking-[0.2em] ${accent ?? "text-[var(--gray-text)]"}`}>
          {title} ({items.length})
        </h3>
        <div className="flex flex-col gap-2">
          {items.map((c) => <CardRow key={c.id} card={c} />)}
        </div>
      </section>
    )
  );

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[800px] flex-col gap-6 px-5 pb-10 pt-6">
        <header className="flex items-center justify-between rounded-2xl border border-[var(--stroke)] bg-white/80 px-6 py-4 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] transition hover:text-[var(--primary-blue)]"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M9 2L4 7l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Back
            </button>
            <div className="h-5 w-px bg-[var(--stroke)]" />
            <h1 className="font-display text-xl font-semibold text-[var(--navy-dark)]">My Work</h1>
          </div>
          <p className="text-xs text-[var(--gray-text)]">{cards.length} assigned card{cards.length !== 1 ? "s" : ""}</p>
        </header>

        {error && (
          <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
        )}

        {cards.length === 0 && !error && (
          <div className="rounded-2xl border border-dashed border-[var(--stroke)] p-10 text-center">
            <p className="text-sm text-[var(--gray-text)]">No cards are assigned to you.</p>
          </div>
        )}

        <div className="flex flex-col gap-6">
          <Section title="Overdue" items={overdue} accent="text-red-500" />
          <Section title="Upcoming" items={upcoming} />
          <Section title="No Due Date" items={noDueDate} />
        </div>
      </main>
    </div>
  );
};
