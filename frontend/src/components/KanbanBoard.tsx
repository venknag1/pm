"use client";

import { useEffect, useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { AISidebar } from "@/components/AISidebar";
import { moveCard, type BoardData } from "@/lib/kanban";
import {
  getBoard,
  renameColumn,
  createCard,
  deleteCard,
  moveCard as moveCardApi,
} from "@/lib/api";

type KanbanBoardProps = {
  onLogout: () => void;
};

export const KanbanBoard = ({ onLogout }: KanbanBoardProps) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  useEffect(() => {
    getBoard().then(setBoard).catch(console.error);
  }, []);

  const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);
    if (!over || active.id === over.id || !board) return;

    const newColumns = moveCard(board.columns, active.id as string, over.id as string);
    setBoard((prev) => (prev ? { ...prev, columns: newColumns } : null));

    const targetCol = newColumns.find((col) => col.cardIds.includes(active.id as string));
    if (targetCol) {
      moveCardApi(
        active.id as string,
        targetCol.id,
        targetCol.cardIds.indexOf(active.id as string)
      ).catch(console.error);
    }
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    setBoard((prev) =>
      prev
        ? { ...prev, columns: prev.columns.map((col) => (col.id === columnId ? { ...col, title } : col)) }
        : null
    );
    renameColumn(columnId, title).catch(console.error);
  };

  const handleAddCard = async (columnId: string, title: string, details: string) => {
    const id = await createCard(columnId, title, details);
    setBoard((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        cards: { ...prev.cards, [id]: { id, title, details } },
        columns: prev.columns.map((col) =>
          col.id === columnId ? { ...col, cardIds: [...col.cardIds, id] } : col
        ),
      };
    });
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    setBoard((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        cards: Object.fromEntries(Object.entries(prev.cards).filter(([id]) => id !== cardId)),
        columns: prev.columns.map((col) =>
          col.id === columnId
            ? { ...col, cardIds: col.cardIds.filter((id) => id !== cardId) }
            : col
        ),
      };
    });
    deleteCard(cardId).catch(console.error);
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  if (!board) {
    return (
      <div className="relative overflow-hidden">
        <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
        <main className="relative mx-auto flex min-h-screen max-w-[1600px] items-center justify-center">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
            Loading board...
          </p>
        </main>
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1600px] flex-col gap-5 px-5 pb-10 pt-6">
        <header className="flex items-center justify-between rounded-2xl border border-[var(--stroke)] bg-white/80 px-6 py-4 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex items-center gap-4">
            <div className="h-8 w-1.5 rounded-full bg-[var(--accent-yellow)]" />
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="font-display text-xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="flex items-center gap-2 rounded-xl border border-[var(--secondary-purple)] bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-white transition hover:bg-[var(--secondary-purple)]/80"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.4"/>
                <path d="M4.5 5.5C4.5 4.12 5.62 3 7 3s2.5 1.12 2.5 2.5c0 1.24-.9 2.27-2.1 2.47V9" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                <circle cx="7" cy="11" r=".7" fill="currentColor"/>
              </svg>
              AI Chat
            </button>
            <button
              onClick={onLogout}
              className="flex items-center gap-2 rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] transition hover:border-[var(--secondary-purple)] hover:text-[var(--secondary-purple)]"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <path d="M5 2H2.5A1.5 1.5 0 001 3.5v7A1.5 1.5 0 002.5 12H5M9 10l3-3-3-3M12 7H5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Log out
            </button>
          </div>
        </header>

        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <section className="grid gap-4 lg:grid-cols-5">
            {board.columns.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                cards={column.cardIds.map((cardId) => board.cards[cardId]).filter(Boolean)}
                onRename={handleRenameColumn}
                onAddCard={handleAddCard}
                onDeleteCard={handleDeleteCard}
              />
            ))}
          </section>
          <DragOverlay>
            {activeCard ? (
              <div className="w-[260px]">
                <KanbanCardPreview card={activeCard} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </main>

      {sidebarOpen && (
        <AISidebar
          onClose={() => setSidebarOpen(false)}
          onBoardUpdate={(updatedBoard) => setBoard(updatedBoard)}
        />
      )}
    </div>
  );
};
