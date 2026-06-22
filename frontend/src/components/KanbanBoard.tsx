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
  getBoardById,
  renameColumn,
  createColumn,
  deleteColumn,
  createCard,
  deleteCard,
  moveCard as moveCardApi,
} from "@/lib/api";

type KanbanBoardProps = {
  boardId: number;
  boardTitle: string;
  onBack: () => void;
  onLogout: () => void;
};

export const KanbanBoard = ({ boardId, boardTitle, onBack, onLogout }: KanbanBoardProps) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [addingColumn, setAddingColumn] = useState(false);
  const [newColumnTitle, setNewColumnTitle] = useState("");

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  useEffect(() => {
    getBoardById(boardId).then(setBoard).catch(console.error);
  }, [boardId]);

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

  const handleAddColumn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newColumnTitle.trim()) return;
    try {
      const col = await createColumn(boardId, newColumnTitle.trim());
      setBoard((prev) =>
        prev
          ? { ...prev, columns: [...prev.columns, { id: col.id, title: col.title, cardIds: [] }] }
          : null
      );
      setNewColumnTitle("");
      setAddingColumn(false);
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteColumn = async (columnId: string) => {
    if (!board) return;
    if (board.columns.length <= 1) return;
    try {
      await deleteColumn(boardId, columnId);
      setBoard((prev) => {
        if (!prev) return null;
        const col = prev.columns.find((c) => c.id === columnId);
        const removedCardIds = new Set(col?.cardIds ?? []);
        return {
          ...prev,
          columns: prev.columns.filter((c) => c.id !== columnId),
          cards: Object.fromEntries(
            Object.entries(prev.cards).filter(([id]) => !removedCardIds.has(id))
          ),
        };
      });
    } catch (err: unknown) {
      console.error(err);
    }
  };

  const handleAddCard = async (columnId: string, title: string, details: string) => {
    const id = await createCard(columnId, title, details);
    setBoard((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        cards: { ...prev.cards, [id]: { id, title, details, priority: "medium" } },
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

      <main className="relative mx-auto flex min-h-screen max-w-[1800px] flex-col gap-5 px-5 pb-10 pt-6">
        <header className="flex items-center justify-between rounded-2xl border border-[var(--stroke)] bg-white/80 px-6 py-4 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="flex h-8 w-8 items-center justify-center rounded-xl border border-[var(--stroke)] text-[var(--gray-text)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)]"
              aria-label="Back to boards"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <path d="M9 2L5 7l4 5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
            <div className="h-8 w-1.5 rounded-full bg-[var(--accent-yellow)]" />
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Kanban Studio
              </p>
              <h1 className="font-display text-xl font-semibold text-[var(--navy-dark)]">
                {boardTitle}
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setAddingColumn(true)}
              className="flex items-center gap-2 rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)]"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
              </svg>
              Add Column
            </button>
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

        {addingColumn && (
          <form
            onSubmit={handleAddColumn}
            className="flex gap-3 rounded-2xl border border-[var(--stroke)] bg-white/80 p-4 shadow-[var(--shadow)] backdrop-blur"
          >
            <input
              autoFocus
              type="text"
              placeholder="Column title"
              value={newColumnTitle}
              onChange={(e) => setNewColumnTitle(e.target.value)}
              className="flex-1 rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)] focus:ring-2 focus:ring-[var(--primary-blue)]/20"
            />
            <button
              type="submit"
              className="rounded-xl bg-[var(--secondary-purple)] px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
            >
              Add
            </button>
            <button
              type="button"
              onClick={() => { setAddingColumn(false); setNewColumnTitle(""); }}
              className="rounded-xl border border-[var(--stroke)] px-4 py-2 text-sm text-[var(--gray-text)] transition hover:border-[var(--secondary-purple)]"
            >
              Cancel
            </button>
          </form>
        )}

        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <section className="flex gap-4 overflow-x-auto pb-2">
            {board.columns.map((column) => (
              <div key={column.id} className="min-w-[260px] flex-1">
                <KanbanColumn
                  column={column}
                  cards={column.cardIds.map((cardId) => board.cards[cardId]).filter(Boolean)}
                  onRename={handleRenameColumn}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                  onDeleteColumn={handleDeleteColumn}
                  canDelete={board.columns.length > 1}
                />
              </div>
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
          boardId={boardId}
          onClose={() => setSidebarOpen(false)}
          onBoardUpdate={(updatedBoard) => setBoard(updatedBoard)}
        />
      )}
    </div>
  );
};
