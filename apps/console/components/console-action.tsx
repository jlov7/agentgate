"use client";

import { CheckCircle, LockKey, WarningCircle } from "@phosphor-icons/react";
import { useMutation } from "@tanstack/react-query";

type ConsoleActionProps = {
  label: string;
  endpoint: string;
  payload: Record<string, unknown>;
  requiredRole: "operator" | "policy_editor";
  disabled?: boolean;
};

export function ConsoleAction({
  label,
  endpoint,
  payload,
  requiredRole,
  disabled = false,
}: ConsoleActionProps) {
  const mutation = useMutation({
    mutationFn: async () => {
      const response = await fetch(`/api/agentgate/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(typeof body.error === "string" ? body.error : "Action failed");
      }
      return body;
    },
  });

  return (
    <div className="flex flex-wrap items-center gap-3">
      <button
        type="button"
        disabled={disabled || mutation.isPending}
        onClick={() => mutation.mutate()}
        className="inline-flex min-h-10 items-center gap-2 rounded-full border border-graphite-950 bg-graphite-950 px-4 py-2 text-sm font-semibold text-bone-50 transition hover:bg-graphite-800 disabled:cursor-not-allowed disabled:border-graphite-300 disabled:bg-graphite-200 disabled:text-graphite-600"
        data-role-required={requiredRole}
      >
        <LockKey size={16} weight="bold" />
        {mutation.isPending ? "Submitting" : label}
      </button>
      <span className="inline-flex items-center gap-1.5 rounded-full border border-graphite-900/10 bg-bone-100 px-3 py-1 text-xs font-medium text-graphite-650">
        {mutation.isError ? (
          <WarningCircle size={14} weight="bold" className="text-red-700" />
        ) : (
          <CheckCircle size={14} weight="bold" className="text-verdigris-800" />
        )}
        {mutation.isSuccess ? "Audit recorded" : `Requires ${requiredRole}`}
      </span>
    </div>
  );
}
