import type { ReactNode } from "react";

type Tone = "default" | "accent" | "danger" | "warning" | "success";

const toneClass: Record<Tone, string> = {
  default: "border-graphite-200/70 bg-bone-50 text-graphite-900",
  accent: "border-verdigris-500/40 bg-verdigris-500/10 text-verdigris-900",
  danger: "border-red-500/35 bg-red-500/10 text-red-900",
  warning: "border-amber-500/35 bg-amber-500/10 text-amber-950",
  success: "border-emerald-500/35 bg-emerald-500/10 text-emerald-950",
};

export function ShellBand({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`mx-auto w-full max-w-[1500px] px-4 sm:px-6 lg:px-8 ${className}`}>{children}</section>;
}

export function Bezel({
  children,
  className = "",
  innerClassName = "",
}: {
  children: ReactNode;
  className?: string;
  innerClassName?: string;
}) {
  return (
    <div className={`rounded-[2rem] border border-graphite-900/10 bg-graphite-900/[0.035] p-1.5 shadow-[0_28px_90px_-55px_oklch(0.28_0.015_170_/_0.46)] ${className}`}>
      <div className={`rounded-[calc(2rem-0.375rem)] border border-bone-50/70 bg-bone-50/92 shadow-[inset_0_1px_0_oklch(1_0_0_/_0.68)] ${innerClassName}`}>
        {children}
      </div>
    </div>
  );
}

export function StatusPill({ children, tone = "default" }: { children: ReactNode; tone?: Tone }) {
  return (
    <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium tabular-nums ${toneClass[tone]}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {children}
    </span>
  );
}

export function Metric({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="min-w-0">
      <div className="font-mono text-[2rem] leading-none tracking-[-0.03em] text-graphite-950 md:text-[2.65rem]">{value}</div>
      <div className="mt-2 text-sm font-medium text-graphite-700">{label}</div>
      {hint ? <div className="mt-1 text-xs text-graphite-500">{hint}</div> : null}
    </div>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  copy,
}: {
  eyebrow: string;
  title: string;
  copy?: string;
}) {
  return (
    <div className="max-w-4xl">
      <p className="font-mono text-xs uppercase tracking-[0.22em] text-verdigris-800">{eyebrow}</p>
      <h2 className="mt-4 text-balance text-3xl font-semibold tracking-[-0.045em] text-graphite-950 md:text-5xl">{title}</h2>
      {copy ? <p className="mt-5 max-w-[70ch] text-base leading-7 text-graphite-650">{copy}</p> : null}
    </div>
  );
}

export function EmptyState({
  title,
  copy,
  action,
}: {
  title: string;
  copy: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-[1.5rem] border border-dashed border-graphite-300 bg-bone-100/70 p-8 text-center">
      <h3 className="text-lg font-semibold text-graphite-950">{title}</h3>
      <p className="mx-auto mt-2 max-w-[55ch] text-sm leading-6 text-graphite-650">{copy}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

export function classNames(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}
