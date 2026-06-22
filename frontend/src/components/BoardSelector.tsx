"use client";

import { useEffect, useState } from "react";
import { listBoards, createBoard, deleteBoard, renameBoard, pinBoard, unpinBoard, type BoardSummary } from "@/lib/api";
import { ChangePasswordForm } from "@/components/ChangePasswordForm";
import { SearchModal } from "@/components/SearchModal";

type BoardSelectorProps = {
  onSelectBoard: (boardId: number, boardTitle: string) => void;
  onLogout: () => void;
  username: string;
  isAdmin: boolean;
  onAdminPanel: () => void;
};

export const BoardSelector = ({
  onSelectBoard,
  onLogout,
  username,
  isAdmin,
  onAdminPanel,
}: BoardSelectorProps) => {
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [creatingBoard, setCreatingBoard] = useState(false);
  const [newBoardTitle, setNewBoardTitle] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameTitle, setRenameTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showProfile, setShowProfile] = useState(false);
  const [showSearch, setShowSearch] = useState(false);

  useEffect(() => {
    listBoards()
      .then(setBoards)
      .catch(() => setError("Failed to load boards"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "/" && !["INPUT", "TEXTAREA"].includes((e.target as HTMLElement).tagName)) {
        e.preventDefault();
        setShowSearch(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newBoardTitle.trim()) return;
    try {
      const created = await createBoard(newBoardTitle.trim(), selectedTemplate || undefined);
      setBoards((prev) => [...prev, { ...created, created_at: new Date().toISOString(), card_count: 0, done_count: 0, pinned: false }]);
      setNewBoardTitle("");
      setSelectedTemplate("");
      setCreatingBoard(false);
      onSelectBoard(created.id, created.title);
    } catch {
      setError("Failed to create board");
    }
  };

  const handleDelete = async (e: React.MouseEvent, boardId: number) => {
    e.stopPropagation();
    try {
      await deleteBoard(boardId);
      setBoards((prev) => prev.filter((b) => b.id !== boardId));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete board");
    }
  };

  const startRename = (e: React.MouseEvent, board: BoardSummary) => {
    e.stopPropagation();
    setRenamingId(board.id);
    setRenameTitle(board.title);
  };

  const handlePin = async (e: React.MouseEvent, board: BoardSummary) => {
    e.stopPropagation();
    try {
      if (board.pinned) {
        await unpinBoard(board.id);
      } else {
        await pinBoard(board.id);
      }
      const updated = await listBoards();
      setBoards(updated);
    } catch {
      setError("Failed to update pin");
    }
  };

  const handleRename = async (e: React.FormEvent, boardId: number) => {
    e.preventDefault();
    if (!renameTitle.trim()) return;
    try {
      await renameBoard(boardId, renameTitle.trim());
      setBoards((prev) =>
        prev.map((b) => (b.id === boardId ? { ...b, title: renameTitle.trim() } : b))
      );
      setRenamingId(null);
    } catch {
      setError("Failed to rename board");
    }
  };

  if (loading) {
    return (
      <div className="relative overflow-hidden">
        <main className="relative mx-auto flex min-h-screen max-w-[1200px] items-center justify-center">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
            Loading boards...
          </p>
        </main>
      </div>
    );
  }

  return (
    <>
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[800px] flex-col gap-6 px-5 pb-10 pt-6">
        <header className="flex items-center justify-between rounded-2xl border border-[var(--stroke)] bg-white/80 px-6 py-4 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex items-center gap-4">
            <div className="h-8 w-1.5 rounded-full bg-[var(--accent-yellow)]" />
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Welcome, {username}
              </p>
              <h1 className="font-display text-xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSearch(true)}
              className="flex items-center gap-2 rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)]"
              title="Search cards (across all boards)"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.4"/>
                <path d="M9.5 9.5L13 13" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
              </svg>
              Search
            </button>
            {isAdmin && (
              <button
                onClick={onAdminPanel}
                className="flex items-center gap-2 rounded-xl border border-[var(--primary-blue)] bg-[var(--primary-blue)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-white transition hover:opacity-90"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                  <circle cx="7" cy="5" r="3" stroke="currentColor" strokeWidth="1.4"/>
                  <path d="M1 12c0-2.5 2.686-4.5 6-4.5s6 2 6 4.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                </svg>
                Admin
              </button>
            )}
            <button
              onClick={() => setShowProfile((p) => !p)}
              className="flex items-center gap-2 rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)]"
              aria-label="Account settings"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <circle cx="7" cy="5" r="2.5" stroke="currentColor" strokeWidth="1.4"/>
                <path d="M2 12c0-2.2 2.239-4 5-4s5 1.8 5 4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
              </svg>
              Profile
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

        {error && (
          <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
            {error}
          </p>
        )}

        {showProfile && (
          <div className="rounded-2xl border border-[var(--stroke)] bg-white/80 p-6 shadow-[var(--shadow)] backdrop-blur">
            <h2 className="mb-4 font-semibold text-[var(--navy-dark)]">Change Password</h2>
            <ChangePasswordForm onDone={() => setShowProfile(false)} />
          </div>
        )}

        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[var(--navy-dark)]">Your Boards</h2>
          <button
            onClick={() => setCreatingBoard(true)}
            className="flex items-center gap-2 rounded-xl border border-[var(--accent-yellow)] bg-[var(--accent-yellow)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-[var(--navy-dark)] transition hover:opacity-90"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
            </svg>
            New Board
          </button>
        </div>

        {creatingBoard && (
          <form
            onSubmit={handleCreate}
            className="flex gap-3 rounded-2xl border border-[var(--stroke)] bg-white/80 p-4 shadow-[var(--shadow)] backdrop-blur"
          >
            <div className="flex flex-1 flex-col gap-2">
              <input
                autoFocus
                type="text"
                placeholder="Board title"
                value={newBoardTitle}
                onChange={(e) => setNewBoardTitle(e.target.value)}
                className="rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)] focus:ring-2 focus:ring-[var(--primary-blue)]/20"
              />
              <div className="flex flex-wrap gap-1.5">
                {[
                  { value: "", label: "Default" },
                  { value: "sprint", label: "Sprint" },
                  { value: "kanban", label: "Kanban" },
                  { value: "marketing", label: "Marketing" },
                  { value: "bug-tracker", label: "Bug Tracker" },
                ].map((t) => (
                  <button
                    key={t.value}
                    type="button"
                    onClick={() => setSelectedTemplate(t.value)}
                    className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${
                      selectedTemplate === t.value
                        ? "border-[var(--secondary-purple)] bg-[var(--secondary-purple)] text-white"
                        : "border-[var(--stroke)] bg-[var(--surface)] text-[var(--gray-text)] hover:border-[var(--secondary-purple)]"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
            <button
              type="submit"
              className="rounded-xl bg-[var(--secondary-purple)] px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
            >
              Create
            </button>
            <button
              type="button"
              onClick={() => { setCreatingBoard(false); setNewBoardTitle(""); setSelectedTemplate(""); }}
              className="rounded-xl border border-[var(--stroke)] px-4 py-2 text-sm text-[var(--gray-text)] transition hover:border-[var(--secondary-purple)]"
            >
              Cancel
            </button>
          </form>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          {boards.map((board) => (
            <div
              key={board.id}
              onClick={() => renamingId !== board.id && onSelectBoard(board.id, board.title)}
              className="group flex cursor-pointer flex-col gap-3 rounded-2xl border border-[var(--stroke)] bg-white/80 p-5 shadow-[var(--shadow)] backdrop-blur transition hover:border-[var(--primary-blue)] hover:shadow-lg"
            >
              {renamingId === board.id ? (
                <form
                  onSubmit={(e) => handleRename(e, board.id)}
                  className="flex gap-2"
                  onClick={(e) => e.stopPropagation()}
                >
                  <input
                    autoFocus
                    type="text"
                    value={renameTitle}
                    onChange={(e) => setRenameTitle(e.target.value)}
                    className="flex-1 rounded-lg border border-[var(--stroke)] bg-[var(--surface)] px-3 py-1.5 text-sm outline-none focus:border-[var(--primary-blue)]"
                  />
                  <button type="submit" className="text-xs font-semibold text-[var(--primary-blue)]">
                    Save
                  </button>
                  <button
                    type="button"
                    onClick={() => setRenamingId(null)}
                    className="text-xs text-[var(--gray-text)]"
                  >
                    Cancel
                  </button>
                </form>
              ) : (
                <div className="flex items-start justify-between">
                  <h3 className="flex items-center gap-1.5 font-semibold text-[var(--navy-dark)]">
                    {board.pinned && (
                      <svg width="12" height="12" viewBox="0 0 14 14" fill="currentColor" className="text-[var(--accent-yellow)]" aria-label="Pinned">
                        <path d="M7 1l1.545 4.054L13 5.236l-3.5 3.09.999 4.674L7 10.618l-3.499 2.382L4.5 8.326 1 5.236l4.455-.182L7 1z"/>
                      </svg>
                    )}
                    {board.title}
                  </h3>
                  <div className="flex gap-1 opacity-0 transition group-hover:opacity-100">
                    <button
                      onClick={(e) => handlePin(e, board)}
                      className={`rounded-lg p-1.5 transition hover:bg-[var(--surface)] ${board.pinned ? "text-[var(--accent-yellow)]" : "text-[var(--gray-text)] hover:text-[var(--accent-yellow)]"}`}
                      title={board.pinned ? "Unpin board" : "Pin board"}
                    >
                      <svg width="14" height="14" viewBox="0 0 14 14" fill={board.pinned ? "currentColor" : "none"} stroke={board.pinned ? "none" : "currentColor"} strokeWidth="1.3">
                        <path d="M7 1l1.545 4.054L13 5.236l-3.5 3.09.999 4.674L7 10.618l-3.499 2.382L4.5 8.326 1 5.236l4.455-.182L7 1z" strokeLinejoin="round"/>
                      </svg>
                    </button>
                    <button
                      onClick={(e) => startRename(e, board)}
                      className="rounded-lg p-1.5 text-[var(--gray-text)] transition hover:bg-[var(--surface)] hover:text-[var(--navy-dark)]"
                      title="Rename board"
                    >
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                        <path d="M9.5 1.5l3 3L4 13H1v-3L9.5 1.5z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/>
                      </svg>
                    </button>
                    <button
                      onClick={(e) => handleDelete(e, board.id)}
                      className="rounded-lg p-1.5 text-[var(--gray-text)] transition hover:bg-red-50 hover:text-red-500"
                      title="Delete board"
                    >
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                        <path d="M2 3.5h10M5.5 3.5V2.5h3v1M5.5 6v5M8.5 6v5M3 3.5l.5 8h7l.5-8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </button>
                  </div>
                </div>
              )}
              <div className="flex items-center gap-4 text-xs text-[var(--gray-text)]">
                <span>{board.card_count} {board.card_count === 1 ? "card" : "cards"}</span>
                <span>{new Date(board.created_at).toLocaleDateString()}</span>
              </div>
              {board.card_count > 0 && (
                <div className="flex items-center gap-2">
                  <div className="h-1 flex-1 overflow-hidden rounded-full bg-[var(--stroke)]">
                    <div
                      className="h-full rounded-full bg-emerald-500 transition-all"
                      style={{ width: `${Math.round((board.done_count / board.card_count) * 100)}%` }}
                    />
                  </div>
                  <span className="text-[10px] font-semibold text-emerald-600">
                    {Math.round((board.done_count / board.card_count) * 100)}%
                  </span>
                </div>
              )}
            </div>
          ))}

          {boards.length === 0 && !creatingBoard && (
            <div className="col-span-2 rounded-2xl border border-dashed border-[var(--stroke)] p-10 text-center">
              <p className="text-sm text-[var(--gray-text)]">No boards yet. Create one to get started.</p>
            </div>
          )}
        </div>
      </main>
    </div>

    {showSearch && (
      <SearchModal
        onClose={() => setShowSearch(false)}
        onSelectBoard={(boardId, boardTitle) => {
          setShowSearch(false);
          onSelectBoard(boardId, boardTitle);
        }}
      />
    )}
    </>
  );
};
