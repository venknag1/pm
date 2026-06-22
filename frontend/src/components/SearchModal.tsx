"use client";

import { useEffect, useRef, useState } from "react";
import { searchCards, type CardSearchResult } from "@/lib/api";

type SearchModalProps = {
  onClose: () => void;
  onSelectBoard: (boardId: number, boardTitle: string) => void;
};

export const SearchModal = ({ onClose, onSelectBoard }: SearchModalProps) => {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CardSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await searchCards(query.trim());
        setResults(data);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const grouped = results.reduce<Record<string, { boardId: number; boardTitle: string; cards: CardSearchResult[] }>>(
    (acc, r) => {
      if (!acc[r.board_title]) acc[r.board_title] = { boardId: r.board_id, boardTitle: r.board_title, cards: [] };
      acc[r.board_title].cards.push(r);
      return acc;
    },
    {}
  );

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-16"
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
    >
      <div className="absolute inset-0 bg-[var(--navy-dark)]/40 backdrop-blur-sm" />
      <div className="relative w-full max-w-lg rounded-3xl border border-[var(--stroke)] bg-white shadow-2xl">
        <div className="flex items-center gap-3 border-b border-[var(--stroke)] px-4 py-3">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="shrink-0 text-[var(--gray-text)]" aria-hidden="true">
            <circle cx="6.5" cy="6.5" r="5" stroke="currentColor" strokeWidth="1.4"/>
            <path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
          </svg>
          <input
            ref={inputRef}
            type="search"
            placeholder="Search cards across all boards..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Escape") onClose(); }}
            className="flex-1 bg-transparent text-sm text-[var(--navy-dark)] outline-none placeholder:text-[var(--gray-text)]"
            aria-label="Search cards"
          />
          {loading && (
            <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)]">
              Searching...
            </span>
          )}
          <button
            onClick={onClose}
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[var(--gray-text)] transition hover:bg-[var(--surface)]"
            aria-label="Close search"
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M1 1l10 10M11 1L1 11" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        <div className="max-h-[60vh] overflow-y-auto">
          {query.trim().length >= 2 && !loading && results.length === 0 && (
            <p className="px-5 py-8 text-center text-sm text-[var(--gray-text)]">No cards found.</p>
          )}

          {Object.values(grouped).map(({ boardId, boardTitle, cards }) => (
            <div key={boardId} className="border-b border-[var(--stroke)] last:border-0">
              <button
                type="button"
                onClick={() => { onSelectBoard(boardId, boardTitle); onClose(); }}
                className="flex w-full items-center gap-2 bg-[var(--surface)] px-5 py-2 text-left transition hover:bg-[var(--stroke)]/30"
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="text-[var(--secondary-purple)]" aria-hidden="true">
                  <rect x="1" y="1" width="10" height="10" rx="2" stroke="currentColor" strokeWidth="1.3"/>
                  <path d="M3 4h6M3 6.5h4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
                </svg>
                <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-[var(--secondary-purple)]">
                  {boardTitle}
                </span>
              </button>
              {cards.map((card) => (
                <button
                  key={card.id}
                  type="button"
                  onClick={() => { onSelectBoard(card.board_id, card.board_title); onClose(); }}
                  className="flex w-full items-start gap-3 px-5 py-3 text-left transition hover:bg-[var(--surface)]"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-[var(--navy-dark)] leading-5">{card.title}</p>
                    <p className="text-[10px] text-[var(--gray-text)]">{card.column_title}</p>
                    {card.details && (
                      <p className="mt-0.5 text-xs text-[var(--gray-text)] line-clamp-1">{card.details}</p>
                    )}
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    {card.priority && card.priority !== "medium" && (
                      <span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${
                        card.priority === "high" ? "bg-red-100 text-red-600" : "bg-emerald-100 text-emerald-600"
                      }`}>
                        {card.priority}
                      </span>
                    )}
                    {card.due_date && (
                      <span className="text-[9px] text-[var(--gray-text)]">{new Date(card.due_date + "T00:00:00").toLocaleDateString()}</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          ))}

          {query.trim().length < 2 && (
            <p className="px-5 py-6 text-center text-xs text-[var(--gray-text)]">
              Type at least 2 characters to search
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
