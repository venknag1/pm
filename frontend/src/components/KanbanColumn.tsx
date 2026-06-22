import { useState } from "react";
import clsx from "clsx";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { Card, Column } from "@/lib/kanban";
import type { UserBrief } from "@/lib/api";
import { setWipLimit } from "@/lib/api";
import { KanbanCard } from "@/components/KanbanCard";
import { NewCardForm } from "@/components/NewCardForm";

type KanbanColumnProps = {
  column: Column;
  cards: Card[];
  boardId: number;
  users: UserBrief[];
  onRename: (columnId: string, title: string) => void;
  onAddCard: (columnId: string, title: string, details: string) => void;
  onDeleteCard: (columnId: string, cardId: string) => void;
  onUpdateCard: (cardId: string, updates: Partial<Card>) => void;
  onDuplicateCard: (sourceCardId: string, newCard: Card) => void;
  onArchiveCard: (cardId: string) => void;
  onDeleteColumn?: (columnId: string) => void;
  onWipChange?: (columnId: string, limit: number | null) => void;
  canDelete?: boolean;
};

export const KanbanColumn = ({
  column,
  cards,
  boardId,
  users,
  onRename,
  onAddCard,
  onDeleteCard,
  onUpdateCard,
  onDuplicateCard,
  onArchiveCard,
  onDeleteColumn,
  onWipChange,
  canDelete = false,
}: KanbanColumnProps) => {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });
  const [editingWip, setEditingWip] = useState(false);
  const [wipInput, setWipInput] = useState(column.wip_limit?.toString() ?? "");

  const isOverWip = column.wip_limit != null && cards.length > column.wip_limit;

  const handleWipSave = async () => {
    const val = wipInput.trim() === "" ? null : parseInt(wipInput, 10);
    const limit = val === null || isNaN(val) || val < 1 ? null : val;
    setEditingWip(false);
    try {
      await setWipLimit(boardId, column.id, limit);
      onWipChange?.(column.id, limit);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <section
      ref={setNodeRef}
      className={clsx(
        "flex min-h-[480px] flex-col rounded-2xl border border-[var(--stroke)] bg-[var(--surface-strong)] p-3 shadow-[var(--shadow)] transition",
        isOver && "ring-2 ring-[var(--accent-yellow)]"
      )}
      data-testid={`column-${column.id}`}
    >
      <div className="flex items-center justify-between gap-2 pb-2">
        <input
          value={column.title}
          onChange={(event) => onRename(column.id, event.target.value)}
          className="min-w-0 flex-1 bg-transparent font-display text-sm font-semibold text-[var(--navy-dark)] outline-none"
          aria-label="Column title"
        />
        <div className="flex items-center gap-1">
          <span className={clsx(
            "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.15em]",
            isOverWip
              ? "bg-red-100 text-red-600"
              : "bg-[var(--surface)] text-[var(--gray-text)]"
          )}>
            {cards.length}{column.wip_limit != null ? `/${column.wip_limit}` : ""}
          </span>
          <button
            onClick={() => { setWipInput(column.wip_limit?.toString() ?? ""); setEditingWip(true); }}
            className="flex h-5 w-5 items-center justify-center rounded-full text-[var(--gray-text)] transition hover:bg-[var(--surface)] hover:text-[var(--navy-dark)]"
            title="Set WIP limit"
            aria-label={`Set WIP limit for column ${column.title}`}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
              <circle cx="5" cy="5" r="4" stroke="currentColor" strokeWidth="1.2"/>
              <path d="M5 3v2.5L6.5 7" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
            </svg>
          </button>
          {canDelete && onDeleteColumn && (
            <button
              onClick={() => onDeleteColumn(column.id)}
              className="flex h-5 w-5 items-center justify-center rounded-full text-[var(--gray-text)] transition hover:bg-red-50 hover:text-red-400"
              title="Delete column"
              aria-label={`Delete column ${column.title}`}
            >
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
                <path d="M1 1l8 8M9 1L1 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </button>
          )}
        </div>
      </div>

      {editingWip && (
        <div className="mb-2 flex items-center gap-1.5 rounded-lg border border-[var(--stroke)] bg-white px-2 py-1.5">
          <span className="text-[10px] text-[var(--gray-text)]">WIP limit:</span>
          <input
            autoFocus
            type="number"
            min="1"
            value={wipInput}
            onChange={(e) => setWipInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleWipSave(); if (e.key === "Escape") setEditingWip(false); }}
            placeholder="None"
            className="w-14 bg-transparent text-xs text-[var(--navy-dark)] outline-none"
          />
          <button onClick={handleWipSave} className="text-[10px] font-semibold text-[var(--primary-blue)]">Set</button>
          <button
            onClick={() => { setWipInput(""); handleWipSave(); }}
            className="text-[10px] text-[var(--gray-text)]"
          >
            Clear
          </button>
        </div>
      )}

      <div className="h-0.5 w-8 rounded-full bg-[var(--accent-yellow)] mb-3" />
      <div className="flex flex-1 flex-col gap-2">
        <SortableContext items={column.cardIds} strategy={verticalListSortingStrategy}>
          {cards.map((card) => (
            <KanbanCard
              key={card.id}
              card={card}
              users={users}
              onDelete={(cardId) => onDeleteCard(column.id, cardId)}
              onUpdate={onUpdateCard}
              onDuplicate={(sourceId, newCard) => onDuplicateCard(sourceId, newCard)}
              onArchive={onArchiveCard}
            />
          ))}
        </SortableContext>
        {cards.length === 0 && (
          <div className="flex flex-1 items-center justify-center rounded-xl border border-dashed border-[var(--stroke)] px-3 py-6 text-center text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
            Drop here
          </div>
        )}
      </div>
      <NewCardForm
        onAdd={(title, details) => onAddCard(column.id, title, details)}
      />
    </section>
  );
};
