import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";
import { CardModal } from "@/components/CardModal";

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

type KanbanCardProps = {
  card: Card;
  onDelete: (cardId: string) => void;
  onUpdate: (cardId: string, updates: Partial<Card>) => void;
};

export const KanbanCard = ({ card, onDelete, onUpdate }: KanbanCardProps) => {
  const [modalOpen, setModalOpen] = useState(false);
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const isOverdue =
    card.due_date && new Date(card.due_date) < new Date(new Date().toDateString());

  return (
    <>
      <article
        ref={setNodeRef}
        style={style}
        className={clsx(
          "group relative rounded-2xl border border-transparent bg-white px-4 py-3 shadow-[0_12px_24px_rgba(3,33,71,0.08)]",
          "transition-all duration-150 cursor-pointer",
          isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
        )}
        {...attributes}
        {...listeners}
        onClick={() => !isDragging && setModalOpen(true)}
        data-testid={`card-${card.id}`}
      >
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
        {card.due_date && (
          <p className={clsx("mt-2 text-[10px] font-semibold", isOverdue ? "text-red-500" : "text-[var(--gray-text)]")}>
            Due {new Date(card.due_date + "T00:00:00").toLocaleDateString()}
            {isOverdue && " (overdue)"}
          </p>
        )}
      </article>

      {modalOpen && (
        <CardModal
          card={card}
          onClose={() => setModalOpen(false)}
          onUpdate={onUpdate}
        />
      )}
    </>
  );
};
