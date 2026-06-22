"use client";

import { useEffect, useState } from "react";
import { adminListUsers, adminDeleteUser, adminPromoteUser, type UserSummary } from "@/lib/api";

type AdminPanelProps = {
  currentUsername: string;
  onBack: () => void;
};

export const AdminPanel = ({ currentUsername, onBack }: AdminPanelProps) => {
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    adminListUsers()
      .then(setUsers)
      .catch(() => setError("Failed to load users"))
      .finally(() => setLoading(false));
  }, []);

  const handleDelete = async (user: UserSummary) => {
    if (!confirm(`Delete user "${user.username}"? This will also delete all their boards.`)) return;
    setActionError(null);
    try {
      await adminDeleteUser(user.id);
      setUsers((prev) => prev.filter((u) => u.id !== user.id));
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to delete user");
    }
  };

  const handlePromote = async (user: UserSummary) => {
    if (!confirm(`Promote "${user.username}" to admin?`)) return;
    setActionError(null);
    try {
      await adminPromoteUser(user.id);
      setUsers((prev) => prev.map((u) => (u.id === user.id ? { ...u, is_admin: true } : u)));
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to promote user");
    }
  };

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[900px] flex-col gap-6 px-5 pb-10 pt-6">
        <header className="flex items-center justify-between rounded-2xl border border-[var(--stroke)] bg-white/80 px-6 py-4 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex items-center gap-4">
            <div className="h-8 w-1.5 rounded-full bg-[var(--primary-blue)]" />
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Administration
              </p>
              <h1 className="font-display text-xl font-semibold text-[var(--navy-dark)]">
                User Management
              </h1>
            </div>
          </div>
          <button
            onClick={onBack}
            className="flex items-center gap-2 rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)]"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M9 2L5 7l4 5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Back to Boards
          </button>
        </header>

        {error && (
          <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
        )}

        {actionError && (
          <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">{actionError}</p>
        )}

        <div className="rounded-2xl border border-[var(--stroke)] bg-white/80 shadow-[var(--shadow)] backdrop-blur overflow-hidden">
          <div className="border-b border-[var(--stroke)] px-6 py-4">
            <h2 className="font-semibold text-[var(--navy-dark)]">
              All Users ({users.length})
            </h2>
          </div>

          {loading ? (
            <div className="p-8 text-center text-sm text-[var(--gray-text)]">Loading...</div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--stroke)]">
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)]">Username</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)]">Role</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)]">Boards</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)]">Joined</th>
                  <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)]">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id} className="border-b border-[var(--stroke)] last:border-0 hover:bg-[var(--surface)]/50">
                    <td className="px-6 py-4">
                      <span className="font-medium text-[var(--navy-dark)]">{user.username}</span>
                      {user.username === currentUsername && (
                        <span className="ml-2 text-xs text-[var(--gray-text)]">(you)</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {user.is_admin ? (
                        <span className="inline-block rounded-full bg-[var(--primary-blue)]/10 px-2.5 py-0.5 text-xs font-semibold text-[var(--primary-blue)]">
                          Admin
                        </span>
                      ) : (
                        <span className="inline-block rounded-full bg-[var(--surface)] px-2.5 py-0.5 text-xs font-semibold text-[var(--gray-text)]">
                          User
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-[var(--gray-text)]">{user.board_count}</td>
                    <td className="px-6 py-4 text-sm text-[var(--gray-text)]">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {!user.is_admin && user.username !== currentUsername && (
                          <button
                            onClick={() => handlePromote(user)}
                            className="rounded-lg border border-[var(--primary-blue)] px-3 py-1 text-xs font-semibold text-[var(--primary-blue)] transition hover:bg-[var(--primary-blue)] hover:text-white"
                          >
                            Promote
                          </button>
                        )}
                        {user.username !== currentUsername && (
                          <button
                            onClick={() => handleDelete(user)}
                            className="rounded-lg border border-red-200 px-3 py-1 text-xs font-semibold text-red-500 transition hover:bg-red-50"
                          >
                            Delete
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  );
};
