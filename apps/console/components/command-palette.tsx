"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { MagnifyingGlass, ShieldCheck, Siren, X } from "@phosphor-icons/react";
import Link from "next/link";
import { useMemo, useState } from "react";

const actions = [
  { href: "/console", label: "Open command center", detail: "Risk, sessions, SLOs, approvals" },
  { href: "/sessions/sess-containment-8241", label: "Inspect contained session", detail: "Timeline, policy decisions, evidence" },
  { href: "/policies", label: "Review policy revision", detail: "Replay drift, publish gate, rollback" },
  { href: "/operations", label: "Open operations board", detail: "Incidents, rollouts, support bundle" },
  { href: "/reference", label: "Read reference", detail: "MkDocs migration surface" },
];

export function CommandPalette() {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return actions;
    return actions.filter((action) => `${action.label} ${action.detail}`.toLowerCase().includes(normalized));
  }, [query]);

  return (
    <Dialog.Root>
      <Dialog.Trigger className="group inline-flex items-center gap-2 rounded-full bg-graphite-950 px-4 py-2.5 text-sm font-semibold text-bone-50 shadow-[0_18px_40px_-28px_oklch(0.12_0.01_180_/_0.8)] transition duration-300 ease-cockpit hover:-translate-y-0.5 active:scale-[0.98]">
        <MagnifyingGlass size={17} />
        Command K
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-graphite-950/45 backdrop-blur-md" />
        <Dialog.Content
          aria-describedby={undefined}
          className="fixed left-1/2 top-24 z-50 w-[calc(100vw-2rem)] max-w-2xl -translate-x-1/2 rounded-[2rem] border border-bone-50/60 bg-bone-50 p-2 shadow-[0_40px_120px_-45px_oklch(0.12_0.01_180_/_0.72)]"
        >
          <div className="rounded-[calc(2rem-0.5rem)] border border-graphite-900/10 bg-bone-100/70">
            <div className="flex items-center gap-3 border-b border-graphite-900/10 px-5 py-4">
              <ShieldCheck className="text-verdigris-800" size={22} />
              <Dialog.Title className="text-base font-semibold text-graphite-950">Command surface</Dialog.Title>
              <Dialog.Close className="ml-auto rounded-full p-2 text-graphite-600 transition hover:bg-graphite-900 hover:text-bone-50" aria-label="Close command palette">
                <X size={16} />
              </Dialog.Close>
            </div>
            <div className="p-4">
              <label className="sr-only" htmlFor="ag-command-search">Search actions</label>
              <input
                id="ag-command-search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search sessions, policies, incidents"
                className="w-full rounded-2xl border border-graphite-900/10 bg-bone-50 px-4 py-3 text-base text-graphite-950 outline-none transition focus:border-verdigris-500"
              />
              <div className="mt-4 grid gap-2">
                {filtered.map((action) => (
                  <Dialog.Close asChild key={action.href}>
                    <Link href={action.href} className="group flex items-center justify-between rounded-2xl border border-transparent px-4 py-3 transition duration-300 ease-cockpit hover:border-verdigris-500/30 hover:bg-verdigris-500/10">
                      <span>
                        <span className="block text-sm font-semibold text-graphite-950">{action.label}</span>
                        <span className="mt-1 block text-xs text-graphite-650">{action.detail}</span>
                      </span>
                      <Siren className="text-graphite-400 transition group-hover:text-verdigris-800" size={18} />
                    </Link>
                  </Dialog.Close>
                ))}
              </div>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
