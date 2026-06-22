import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";
import type { UserBrief } from "@/lib/api";
import { CardModal } from "@/components/CardModal";

const CARD_COLOR_MAP: Record<string, string> = {
  red: "#ef4444",
  orange: "#f97316",
  yellow: "#eab308",
  green: "#22c55e",
  blue: "#3b82f6",
  purple: "#a855f7",
};

const PRIORITY_COLORS = {
  high: "bg-red-100 text-red-600",
  medium: "bg-amber-100 text-amber-600",
  low: "bg-emerald-100 text-emerald-600",
};

const LABEL_COLORS: Record<string, string> = {
  bug: "bg-red-100 text-red-700",
  feature: "bg-blue-100 text-blue-700",
  chore: "bg-gray-100 text-gray-600",
  design: "bg-purple-100 text-purple-700",
  docs: "bg-yellow-100 text-yellow-700",
};

function labelColor(label: string): string {
  return LABEL_COLORS[label.toLowerCase()] ?? "bg-gray-100 text-gray-600";
}

function userInitials(username: string): string {
  return username.slice(0, 2).toUpperCase();
}

type KanbanCardProps = {
  card: Card;
  users: UserBrief[];
  boardId: number;
  onDelete: (cardId: string) => void;
  onUpdate: (cardId: string, updates: Partial<Card>) => void;
  onDuplicate?: (sourceId: string, newCard: Card) => void;
  onArchive?: (cardId: string) => void;
};

export const KanbanCard = ({ card, users, boardId, onDelete, onUpdate, onDuplicate, onArchive }: KanbanCardProps) => {
  const [modalOpen, setModalOpen] = useState(false);
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const today = new Date(new Date().toDateString());
  const dueDate = card.due_date ? new Date(card.due_date + "T00:00:00") : null;
  const isOverdue = dueDate && dueDate < today;
  const isDueToday = dueDate && dueDate.getTime() === today.getTime();
  const isDueSoon = dueDate && !isOverdue && !isDueToday && dueDate <= new Date(today.getTime() + 3 * 86400000);

  const hasChecklist = (card.checklist_count ?? 0) > 0;

  return (
    <>
      <article
        ref={setNodeRef}
        style={style}
        className={clsx(
          "group relative overflow-hidden rounded-2xl border border-transparent bg-white px-4 py-3 shadow-[0_12px_24px_rgba(3,33,71,0.08)]",
          "transition-all duration-150 cursor-pointer",
          isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
        )}
        {...attributes}
        {...listeners}
        onClick={() => !isDragging && setModalOpen(true)}
        data-testid={`card-${card.id}`}
      >
        {card.color && CARD_COLOR_MAP[card.color] && (
          <div
            className="absolute left-0 top-0 h-full w-1 rounded-l-2xl"
            style={{ backgroundColor: CARD_COLOR_MAP[card.color] }}
          />
        )}
        <button
          type="button"
          onPointerDown={(e) => e.stopPropagation()}
          onClick={(e) => { e.stopPropagation(); onDelete(card.id); }}
          className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full text-[var(--gray-text)] opacity-0 transition-all hover:bg-[var(--surface)] hover:text-red-400 group-hover:opacity-100"
          aria-label={`Delete ${card.title}`}
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
            <path d="M1 1l8 8M9 1L1 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </button>

        <div className="mb-1.5 flex flex-wrap gap-1.5 pr-5">
          {card.priority && card.priority !== "medium" && (
            <span className={clsx("rounded-full px-2 py-0.5 text-[10px] font-semibold", PRIORITY_COLORS[card.priority])}>
              {card.priority}
            </span>
          )}
          {card.label && (
            <span className={clsx("rounded-full px-2 py-0.5 text-[10px] font-semibold", labelColor(card.label))}>
              {card.label}
            </span>
          )}
        </div>

        <h4 className="font-display text-sm font-semibold leading-5 text-[var(--navy-dark)] pr-4">
          {card.title}
        </h4>
        {card.details && (
          <p className="mt-1.5 text-xs leading-5 text-[var(--gray-text)] line-clamp-2">
            {card.details}
          </p>
        )}

        <div className="mt-2 flex items-center gap-2">
          {card.due_date && (
            <p className={clsx("text-[10px] font-semibold",
              isOverdue ? "text-red-500" :
              isDueToday ? "text-amber-500" :
              isDueSoon ? "text-[var(--primary-blue)]" :
              "text-[var(--gray-text)]"
            )}>
              {isOverdue ? "Overdue" : isDueToday ? "Due today" : `Due ${new Date(card.due_date + "T00:00:00").toLocaleDateString()}`}
            </p>
          )}
          {card.story_points != null && (
            <span className="flex h-4 w-4 items-center justify-center rounded bg-[var(--secondary-purple)]/10 text-[9px] font-bold text-[var(--secondary-purple)]">
              {card.story_points}
            </span>
          )}
          {hasChecklist && (
            <span className={clsx(
              "flex items-center gap-0.5 text-[10px] font-semibold",
              card.checklist_done === card.checklist_count ? "text-emerald-600" : "text-[var(--gray-text)]"
            )}>
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
                <rect x="1" y="1" width="8" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.2"/>
                <path d="M3 5l1.5 1.5L7 3.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              {card.checklist_done}/{card.checklist_count}
            </span>
          )}
          {card.assigned_to_username && (
            <span
              className="ml-auto flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--secondary-purple)] text-[9px] font-bold text-white"
              title={card.assigned_to_username}
            >
              {userInitials(card.assigned_to_username)}
            </span>
          )}
        </div>
      </article>

      {modalOpen && (
        <CardModal
          card={card}
          users={users}
          currentBoardId={boardId}
          onClose={() => setModalOpen(false)}
          onUpdate={onUpdate}
          onDuplicate={(newId) => onDuplicate?.(card.id, { ...card, id: newId, title: card.title + " (copy)", checklist_count: 0, checklist_done: 0 })}
          onArchive={onArchive}
        />
      )}
    </>
  );
};
