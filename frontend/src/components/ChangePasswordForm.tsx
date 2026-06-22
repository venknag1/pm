"use client";

import { useState } from "react";
import { changePassword } from "@/lib/api";

type ChangePasswordFormProps = {
  onDone?: () => void;
};

export const ChangePasswordForm = ({ onDone }: ChangePasswordFormProps) => {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (next !== confirm) {
      setError("New passwords do not match.");
      return;
    }
    if (next.length < 6) {
      setError("New password must be at least 6 characters.");
      return;
    }
    setSaving(true);
    try {
      await changePassword(current, next);
      setSuccess(true);
      setCurrent("");
      setNext("");
      setConfirm("");
      onDone?.();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to change password");
    } finally {
      setSaving(false);
    }
  };

  if (success) {
    return (
      <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
        Password changed successfully.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {error && (
        <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </p>
      )}
      {[
        { id: "current-pw", label: "Current password", value: current, onChange: setCurrent, auto: "current-password" },
        { id: "new-pw", label: "New password", value: next, onChange: setNext, auto: "new-password" },
        { id: "confirm-pw", label: "Confirm new password", value: confirm, onChange: setConfirm, auto: "new-password" },
      ].map(({ id, label, value, onChange, auto }) => (
        <div key={id} className="flex flex-col gap-1.5">
          <label htmlFor={id} className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
            {label}
          </label>
          <input
            id={id}
            type="password"
            autoComplete={auto}
            value={value}
            onChange={(e) => { onChange(e.target.value); setError(null); }}
            className="rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)] focus:ring-2 focus:ring-[var(--primary-blue)]/20"
          />
        </div>
      ))}
      <button
        type="submit"
        disabled={saving}
        className="self-start rounded-xl bg-[var(--secondary-purple)] px-6 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
      >
        {saving ? "Updating..." : "Update password"}
      </button>
    </form>
  );
};
