"use client";

import { useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { LoginPage } from "@/components/LoginPage";
import { BoardSelector } from "@/components/BoardSelector";
import { AdminPanel } from "@/components/AdminPanel";
import { checkAuth, logout, type AuthUser } from "@/lib/auth";
import { listBoards } from "@/lib/api";

type View =
  | { kind: "loading" }
  | { kind: "login" }
  | { kind: "boards" }
  | { kind: "board"; boardId: number; boardTitle: string }
  | { kind: "admin" };

export default function Home() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [view, setView] = useState<View>({ kind: "loading" });

  useEffect(() => {
    checkAuth().then((u) => {
      if (u) {
        setUser(u);
        setView({ kind: "boards" });
      } else {
        setView({ kind: "login" });
      }
    });
  }, []);

  const handleLogin = async (u: AuthUser) => {
    setUser(u);
    // If user has exactly one board, go straight to it
    try {
      const boards = await listBoards();
      if (boards.length === 1) {
        setView({ kind: "board", boardId: boards[0].id, boardTitle: boards[0].title });
      } else {
        setView({ kind: "boards" });
      }
    } catch {
      setView({ kind: "boards" });
    }
  };

  const handleLogout = async () => {
    await logout();
    setUser(null);
    setView({ kind: "login" });
  };

  if (view.kind === "loading") return null;

  if (view.kind === "login") {
    return <LoginPage onLogin={handleLogin} />;
  }

  if (view.kind === "admin") {
    return (
      <AdminPanel
        currentUsername={user?.username ?? ""}
        onBack={() => setView({ kind: "boards" })}
      />
    );
  }

  if (view.kind === "boards") {
    return (
      <BoardSelector
        username={user?.username ?? ""}
        isAdmin={user?.is_admin ?? false}
        onSelectBoard={(boardId, boardTitle) =>
          setView({ kind: "board", boardId, boardTitle })
        }
        onLogout={handleLogout}
        onAdminPanel={() => setView({ kind: "admin" })}
      />
    );
  }

  if (view.kind === "board") {
    return (
      <KanbanBoard
        boardId={view.boardId}
        boardTitle={view.boardTitle}
        onBack={() => setView({ kind: "boards" })}
        onLogout={handleLogout}
      />
    );
  }

  return null;
}
