"use client";

import { useEffect, useRef, useState } from "react";
import type { Card, ChecklistItem } from "@/lib/kanban";
import type { UserBrief } from "@/lib/api";
import {
  updateCard,
  assignCard,
  archiveCard,
  duplicateCard,
  moveCardToBoard,
  getChecklist,
  addChecklistItem,
  updateChecklistItem,
  deleteChecklistItem,
  getComments,
  addComment,
  deleteComment,
  listBoards,
  type CardComment,
  type BoardSummary,
} from "@/lib/api";

const PRIORITY_OPTIONS: Array<{ value: "low" | "medium" | "high"; label: string; color: string }> = [
  { value: "low", label: "Low", color: "text-emerald-600 bg-emerald-50 border-emerald-200" },
  { value: "medium", label: "Medium", color: "text-amber-600 bg-amber-50 border-amber-200" },
  { value: "high", label: "High", color: "text-red-600 bg-red-50 border-red-200" },
];

const LABEL_OPTIONS = ["bug", "feature", "chore", "design", "docs", ""];

type CardModalProps = {
  card: Card;
  users: UserBrief[];
  currentBoardId: number;
  onClose: () => void;
  onUpdate: (cardId: string, updates: Partial<Card>) => void;
  onDuplicate?: (newCardId: string) => void;
  onArchive?: (cardId: string) => void;
};

export const CardModal = ({ card, users, currentBoardId, onClose, onUpdate, onDuplicate, onArchive }: CardModalProps) => {
  const [title, setTitle] = useState(card.title);
  const [details, setDetails] = useState(card.details);
  const [dueDate, setDueDate] = useState(card.due_date ?? "");
  const [priority, setPriority] = useState<"low" | "medium" | "high">(card.priority ?? "medium");
  const [label, setLabel] = useState(card.label ?? "");
  const [assignedUserId, setAssignedUserId] = useState<number | null>(() => {
    if (!card.assigned_to_username) return null;
    return users.find((u) => u.username === card.assigned_to_username)?.id ?? null;
  });
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [duplicating, setDuplicating] = useState(false);
  const [showMoveMenu, setShowMoveMenu] = useState(false);
  const [otherBoards, setOtherBoards] = useState<BoardSummary[]>([]);
  const [moving, setMoving] = useState(false);

  // Checklist state
  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [checklistLoaded, setChecklistLoaded] = useState(false);
  const [newItemTitle, setNewItemTitle] = useState("");
  const [addingItem, setAddingItem] = useState(false);

  // Comments state
  const [comments, setComments] = useState<CardComment[]>([]);
  const [newComment, setNewComment] = useState("");
  const [addingComment, setAddingComment] = useState(false);

  const titleRef = useRef<HTMLInputElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    titleRef.current?.focus();
    getChecklist(card.id).then((items) => {
      setChecklist(items);
      setChecklistLoaded(true);
    }).catch(() => setChecklistLoaded(true));
    getComments(card.id).then(setComments).catch(() => {});
  }, [card.id]);

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
      // Assign separately if changed
      const originalId = users.find((u) => u.username === card.assigned_to_username)?.id ?? null;
      if (assignedUserId !== originalId) {
        await assignCard(card.id, assignedUserId);
      }
      const assignedUsername = users.find((u) => u.id === assignedUserId)?.username ?? null;
      onUpdate(card.id, {
        ...updates,
        due_date: dueDate || undefined,
        label: label || undefined,
        assigned_to_username: assignedUsername,
      });
      setDirty(false);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleDuplicate = async () => {
    setDuplicating(true);
    try {
      const { id: newId } = await duplicateCard(card.id);
      onDuplicate?.(newId);
      onClose();
    } catch (err) {
      console.error(err);
    } finally {
      setDuplicating(false);
    }
  };

  const handleArchive = async () => {
    try {
      await archiveCard(card.id);
      onArchive?.(card.id);
      onClose();
    } catch (err) {
      console.error(err);
    }
  };

  const handleOpenMoveMenu = async () => {
    if (!showMoveMenu) {
      try {
        const boards = await listBoards();
        setOtherBoards(boards.filter((b) => b.id !== currentBoardId));
      } catch (err) {
        console.error(err);
      }
    }
    setShowMoveMenu((s) => !s);
  };

  const handleMoveToBoard = async (targetBoardId: number) => {
    setMoving(true);
    try {
      await moveCardToBoard(card.id, targetBoardId);
      onArchive?.(card.id); // remove from current board state
      onClose();
    } catch (err) {
      console.error(err);
    } finally {
      setMoving(false);
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    try {
      const comment = await addComment(card.id, newComment.trim());
      setComments((prev) => [...prev, comment]);
      setNewComment("");
      setAddingComment(false);
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteComment = async (commentId: string) => {
    try {
      await deleteComment(card.id, commentId);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItemTitle.trim()) return;
    try {
      const item = await addChecklistItem(card.id, newItemTitle.trim());
      setChecklist((prev) => [...prev, item]);
      setNewItemTitle("");
      setAddingItem(false);
      onUpdate(card.id, { checklist_count: checklist.length + 1, checklist_done: checklist.filter((i) => i.completed).length });
    } catch (err) {
      console.error(err);
    }
  };

  const handleToggleItem = async (item: ChecklistItem) => {
    const updated = await updateChecklistItem(card.id, item.id, { completed: !item.completed });
    setChecklist((prev) => prev.map((i) => (i.id === item.id ? updated : i)));
    const newItems = checklist.map((i) => (i.id === item.id ? updated : i));
    onUpdate(card.id, {
      checklist_count: newItems.length,
      checklist_done: newItems.filter((i) => i.completed).length,
    });
  };

  const handleDeleteItem = async (itemId: string) => {
    await deleteChecklistItem(card.id, itemId);
    const newItems = checklist.filter((i) => i.id !== itemId);
    setChecklist(newItems);
    onUpdate(card.id, {
      checklist_count: newItems.length,
      checklist_done: newItems.filter((i) => i.completed).length,
    });
  };

  const mark = () => setDirty(true);
  const doneCount = checklist.filter((i) => i.completed).length;

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 pt-12"
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
              rows={3}
              placeholder="Add more context, links, or notes..."
              className="w-full resize-none rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)] focus:ring-2 focus:ring-[var(--primary-blue)]/20"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                Priority
              </label>
              <div className="flex gap-1.5">
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

          {users.length > 0 && (
            <div>
              <label htmlFor="assignee" className="mb-1.5 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                Assigned to
              </label>
              <select
                id="assignee"
                value={assignedUserId ?? ""}
                onChange={(e) => { setAssignedUserId(e.target.value ? Number(e.target.value) : null); mark(); }}
                className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
              >
                <option value="">Unassigned</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.username}</option>
                ))}
              </select>
            </div>
          )}

          {/* Checklist */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                Checklist
                {checklist.length > 0 && (
                  <span className="ml-2 font-normal normal-case tracking-normal text-[var(--gray-text)]">
                    {doneCount}/{checklist.length}
                  </span>
                )}
              </label>
              {!addingItem && (
                <button
                  type="button"
                  onClick={() => setAddingItem(true)}
                  className="text-xs text-[var(--primary-blue)] transition hover:underline"
                >
                  + Add item
                </button>
              )}
            </div>

            {checklist.length > 0 && (
              <div className="mb-2 h-1.5 w-full overflow-hidden rounded-full bg-[var(--surface)]">
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all"
                  style={{ width: `${Math.round((doneCount / checklist.length) * 100)}%` }}
                />
              </div>
            )}

            {checklistLoaded && checklist.length === 0 && !addingItem && (
              <p className="text-xs text-[var(--gray-text)]">No items yet.</p>
            )}

            <div className="flex flex-col gap-1">
              {checklist.map((item) => (
                <div key={item.id} className="group flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={item.completed}
                    onChange={() => handleToggleItem(item)}
                    className="h-4 w-4 shrink-0 cursor-pointer accent-[var(--secondary-purple)]"
                  />
                  <span className={`flex-1 text-sm ${item.completed ? "line-through text-[var(--gray-text)]" : "text-[var(--navy-dark)]"}`}>
                    {item.title}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleDeleteItem(item.id)}
                    className="flex h-5 w-5 items-center justify-center rounded text-[var(--gray-text)] opacity-0 transition hover:text-red-400 group-hover:opacity-100"
                    aria-label={`Delete checklist item ${item.title}`}
                  >
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                      <path d="M1 1l8 8M9 1L1 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                    </svg>
                  </button>
                </div>
              ))}
            </div>

            {addingItem && (
              <form onSubmit={handleAddItem} className="mt-2 flex gap-2">
                <input
                  autoFocus
                  type="text"
                  placeholder="Item title"
                  value={newItemTitle}
                  onChange={(e) => setNewItemTitle(e.target.value)}
                  className="flex-1 rounded-lg border border-[var(--stroke)] bg-[var(--surface)] px-3 py-1.5 text-sm outline-none focus:border-[var(--primary-blue)]"
                />
                <button type="submit" className="text-xs font-semibold text-[var(--primary-blue)]">
                  Add
                </button>
                <button
                  type="button"
                  onClick={() => { setAddingItem(false); setNewItemTitle(""); }}
                  className="text-xs text-[var(--gray-text)]"
                >
                  Cancel
                </button>
              </form>
            )}
          </div>

          {/* Comments */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                Comments {comments.length > 0 && <span className="font-normal normal-case tracking-normal">({comments.length})</span>}
              </label>
              {!addingComment && (
                <button
                  type="button"
                  onClick={() => setAddingComment(true)}
                  className="text-xs text-[var(--primary-blue)] transition hover:underline"
                >
                  + Add comment
                </button>
              )}
            </div>

            {comments.length > 0 && (
              <div className="mb-2 flex flex-col gap-2">
                {comments.map((c) => (
                  <div key={c.id} className="group flex gap-2 rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--secondary-purple)] text-[9px] font-bold text-white">
                      {c.username.slice(0, 2).toUpperCase()}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-[var(--navy-dark)]">{c.username}</span>
                        <span className="text-[10px] text-[var(--gray-text)]">
                          {new Date(c.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="mt-0.5 text-xs text-[var(--gray-text)] break-words">{c.content}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleDeleteComment(c.id)}
                      className="flex h-5 w-5 shrink-0 items-center justify-center rounded text-[var(--gray-text)] opacity-0 transition hover:text-red-400 group-hover:opacity-100"
                      aria-label="Delete comment"
                    >
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                        <path d="M1 1l8 8M9 1L1 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}

            {addingComment && (
              <form onSubmit={handleAddComment} className="flex flex-col gap-2">
                <textarea
                  autoFocus
                  rows={2}
                  placeholder="Write a comment..."
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  className="w-full resize-none rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm outline-none focus:border-[var(--primary-blue)]"
                />
                <div className="flex gap-2">
                  <button type="submit" className="text-xs font-semibold text-[var(--primary-blue)]">Post</button>
                  <button type="button" onClick={() => { setAddingComment(false); setNewComment(""); }} className="text-xs text-[var(--gray-text)]">Cancel</button>
                </div>
              </form>
            )}

            {comments.length === 0 && !addingComment && (
              <p className="text-xs text-[var(--gray-text)]">No comments yet.</p>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-[var(--stroke)] px-6 py-4">
          <div className="relative flex gap-2">
            <button
              type="button"
              onClick={handleDuplicate}
              disabled={duplicating}
              className="flex items-center gap-1.5 rounded-xl border border-[var(--stroke)] px-3 py-2 text-xs font-semibold text-[var(--gray-text)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)] disabled:opacity-50"
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                <rect x="1" y="3" width="7" height="8" rx="1.2" stroke="currentColor" strokeWidth="1.3"/>
                <path d="M4 3V2a1 1 0 011-1h5a1 1 0 011 1v7a1 1 0 01-1 1h-1" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
              </svg>
              {duplicating ? "Copying..." : "Duplicate"}
            </button>
            <button
              type="button"
              onClick={handleArchive}
              className="flex items-center gap-1.5 rounded-xl border border-[var(--stroke)] px-3 py-2 text-xs font-semibold text-[var(--gray-text)] transition hover:border-amber-400 hover:text-amber-600"
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                <rect x="1" y="3.5" width="10" height="7" rx="1.2" stroke="currentColor" strokeWidth="1.3"/>
                <path d="M1 3.5h10M4.5 1.5h3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
                <path d="M4.5 6.5l1 1 2-2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Archive
            </button>
            <div className="relative">
              <button
                type="button"
                onClick={handleOpenMoveMenu}
                disabled={moving}
                className="flex items-center gap-1.5 rounded-xl border border-[var(--stroke)] px-3 py-2 text-xs font-semibold text-[var(--gray-text)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)] disabled:opacity-50"
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                  <path d="M6 1L10 6H7v5H5V6H2L6 1z" fill="currentColor" opacity="0.7"/>
                </svg>
                {moving ? "Moving..." : "Move to"}
              </button>
              {showMoveMenu && (
                <div className="absolute bottom-full left-0 mb-1 w-48 rounded-xl border border-[var(--stroke)] bg-white shadow-lg">
                  {otherBoards.length === 0 ? (
                    <p className="px-3 py-2 text-xs text-[var(--gray-text)]">No other boards</p>
                  ) : (
                    otherBoards.map((b) => (
                      <button
                        key={b.id}
                        type="button"
                        onClick={() => handleMoveToBoard(b.id)}
                        className="w-full px-3 py-2 text-left text-xs text-[var(--navy-dark)] transition hover:bg-[var(--surface)] first:rounded-t-xl last:rounded-b-xl"
                      >
                        {b.title}
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
          <div className="flex gap-3">
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
    </div>
  );
};
