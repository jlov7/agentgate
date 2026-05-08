import type { ControlPlaneSnapshot, SessionDetail, SessionListItem } from "@agentgate/client";
import { Bezel, EmptyState, Metric, SectionHeading, ShellBand, StatusPill } from "@agentgate/ui";
import { ArrowUpRight, FileLock, GitBranch, Pulse, ShieldWarning, Siren } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import type { ReactNode } from "react";
import { formatDateTime, formatTime, riskTone, shortNumber } from "../lib/format";
import { CommandPalette } from "./command-palette";

export function HeroFrontDoor({ snapshot }: { snapshot: ControlPlaneSnapshot }) {
  return (
    <main>
      <ShellBand className="grid min-h-[calc(100dvh-4rem)] items-center gap-10 py-14 md:grid-cols-[1.05fr_0.95fr] md:py-20">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.28em] text-verdigris-800">Containment-first agent security</p>
          <h1 className="mt-6 max-w-5xl text-balance text-5xl font-semibold leading-[0.94] tracking-[-0.07em] text-graphite-950 md:text-7xl xl:text-8xl">
            Stop unsafe tool calls before they become incidents.
          </h1>
          <p className="mt-7 max-w-2xl text-lg leading-8 text-graphite-650">
            AgentGate turns every agent action into an enforceable decision, a replayable policy record, and audit-grade evidence.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/console" className="group inline-flex items-center gap-3 rounded-full bg-graphite-950 py-2 pl-5 pr-2 text-sm font-semibold text-bone-50 transition duration-300 ease-cockpit hover:-translate-y-0.5 active:scale-[0.98]">
              Open console demo
              <span className="grid h-8 w-8 place-items-center rounded-full bg-bone-50/12 transition group-hover:translate-x-0.5">
                <ArrowUpRight size={16} />
              </span>
            </Link>
            <Link href="/reference" className="inline-flex items-center rounded-full border border-graphite-900/10 bg-bone-50 px-5 py-2.5 text-sm font-semibold text-graphite-800 transition duration-300 ease-cockpit hover:-translate-y-0.5 hover:border-verdigris-500/40">
              Read reference
            </Link>
          </div>
        </div>
        <Bezel innerClassName="overflow-hidden p-0">
          <ConsoleFrame snapshot={snapshot} />
        </Bezel>
      </ShellBand>
      <ShellBand className="pb-24">
        <div className="grid gap-5 md:grid-cols-[1.2fr_0.8fr]">
          <Bezel innerClassName="p-7 md:p-9">
            <SectionHeading eyebrow="Operational proof" title="The product is the evidence loop." copy="The console is organized around containment, replay, rollout, and export. Every surface must answer what happened, why it was allowed or blocked, and what to do next." />
          </Bezel>
          <Bezel innerClassName="p-7">
            <div className="grid grid-cols-3 gap-5">
              <Metric label="decisions" value={shortNumber(snapshot.decisions.allow + snapshot.decisions.deny + snapshot.decisions.requireApproval)} hint="current window" />
              <Metric label="denied" value={shortNumber(snapshot.decisions.deny)} hint="blocked before execution" />
              <Metric label="approval" value={shortNumber(snapshot.decisions.requireApproval)} hint="human gate required" />
            </div>
          </Bezel>
        </div>
      </ShellBand>
    </main>
  );
}

export function CommandCenter({
  snapshot,
  liveState,
}: {
  snapshot: ControlPlaneSnapshot;
  liveState?: { refreshing: boolean; error: ReactNode };
}) {
  return (
    <main>
      <ShellBand className="py-10">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <SectionHeading eyebrow="Command center" title="Containment cockpit" copy="Live operational state for agent sessions, policy gates, incidents, replays, rollouts, and SLO posture." />
          <div className="flex flex-col items-start gap-3 lg:items-end">
            <CommandPalette />
            <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-graphite-500">
              {liveState?.refreshing ? "Refreshing live state" : "Live snapshot locked"}
            </span>
          </div>
        </div>
      </ShellBand>
      <ShellBand className="grid gap-5 pb-20 xl:grid-cols-[1fr_360px]">
        <div className="grid gap-5">
          {liveState?.error ? <Bezel innerClassName="p-6">{liveState.error}</Bezel> : null}
          <Bezel innerClassName="p-6 md:p-8">
            <div className="grid gap-6 md:grid-cols-4">
              <Metric label="allowed" value={shortNumber(snapshot.decisions.allow)} />
              <Metric label="denied" value={shortNumber(snapshot.decisions.deny)} />
              <Metric label="approval" value={shortNumber(snapshot.decisions.requireApproval)} />
              <Metric label="p95 target" value={`${snapshot.slo.p95LatencySeconds}s`} hint={`availability ${Math.round(snapshot.slo.availabilityTarget * 1000) / 10}%`} />
            </div>
          </Bezel>
          <SessionTable sessions={snapshot.sessions} />
          <PolicyReplayPanel snapshot={snapshot} />
        </div>
        <RiskRail snapshot={snapshot} />
      </ShellBand>
    </main>
  );
}

export function ConsoleFrame({ snapshot }: { snapshot: ControlPlaneSnapshot }) {
  return (
    <div className="bg-graphite-950 p-4 text-bone-50 md:p-5">
      <div className="flex items-center justify-between border-b border-bone-50/10 pb-4">
        <div>
          <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-verdigris-400">Tenant</div>
          <div className="mt-1 text-sm font-semibold">{snapshot.tenantId}</div>
        </div>
        <StatusPill tone={riskTone(snapshot.riskLevel)}>{snapshot.riskLevel}</StatusPill>
      </div>
      <div className="grid gap-3 py-5 sm:grid-cols-3">
        <DarkMetric label="allow" value={snapshot.decisions.allow} />
        <DarkMetric label="deny" value={snapshot.decisions.deny} />
        <DarkMetric label="approval" value={snapshot.decisions.requireApproval} />
      </div>
      <div className="space-y-3">
        {snapshot.sessions.map((session) => (
          <Link key={session.sessionId} href={`/sessions/${session.sessionId}`} className="group block rounded-2xl border border-bone-50/10 bg-bone-50/[0.04] p-4 transition duration-300 ease-cockpit hover:bg-bone-50/[0.08]">
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <div className="truncate font-mono text-xs text-bone-50/62">{session.sessionId}</div>
                <div className="mt-1 text-sm font-semibold">{session.agentId || "unbound agent"}</div>
              </div>
              <span className="font-mono text-xs text-verdigris-400">{formatTime(session.lastSeen)}</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

function DarkMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-bone-50/10 bg-bone-50/[0.035] p-4">
      <div className="font-mono text-2xl font-semibold tabular-nums">{value}</div>
      <div className="mt-1 text-xs text-bone-50/55">{label}</div>
    </div>
  );
}

function RiskRail({ snapshot }: { snapshot: ControlPlaneSnapshot }) {
  return (
    <aside className="grid gap-5">
      <Bezel innerClassName="p-6">
        <div className="flex items-center gap-3">
          <ShieldWarning className="text-amber-700" size={28} />
          <div>
            <div className="text-sm font-semibold text-graphite-950">Risk posture</div>
            <div className="mt-1 text-sm text-graphite-650">{snapshot.riskLevel} across {snapshot.sessions.length} live sessions</div>
          </div>
        </div>
      </Bezel>
      <Bezel innerClassName="p-6">
        <h3 className="text-sm font-semibold text-graphite-950">Incidents</h3>
        <div className="mt-4 space-y-3">
          {snapshot.incidents.length ? snapshot.incidents.map((incident) => (
            <div key={incident.incidentId} className="rounded-2xl border border-amber-500/25 bg-amber-500/10 p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="font-mono text-xs text-graphite-650">{incident.incidentId}</span>
                <StatusPill tone="warning">{incident.status}</StatusPill>
              </div>
              <p className="mt-3 text-sm leading-6 text-graphite-800">{incident.reason}</p>
            </div>
          )) : <EmptyState title="No active incidents" copy="Containment events will appear here when a session crosses risk policy." />}
        </div>
      </Bezel>
      <Bezel innerClassName="p-6">
        <h3 className="text-sm font-semibold text-graphite-950">Rollouts</h3>
        <div className="mt-4 space-y-3">
          {snapshot.rollouts.map((rollout) => (
            <div key={rollout.rolloutId} className="rounded-2xl border border-graphite-900/10 bg-bone-100/70 p-4">
              <div className="font-mono text-xs text-graphite-650">{rollout.tenantId}</div>
              <div className="mt-2 text-sm font-semibold text-graphite-950">{rollout.baselineVersion} to {rollout.candidateVersion}</div>
              <div className="mt-3 flex items-center justify-between text-xs text-graphite-650">
                <span>{rollout.status}</span>
                <span>{formatDateTime(rollout.updatedAt)}</span>
              </div>
            </div>
          ))}
        </div>
      </Bezel>
    </aside>
  );
}

function SessionTable({ sessions }: { sessions: SessionListItem[] }) {
  return (
    <Bezel innerClassName="overflow-hidden">
      <div className="border-b border-graphite-900/10 p-6">
        <h3 className="text-lg font-semibold text-graphite-950">Live sessions</h3>
        <p className="mt-1 text-sm text-graphite-650">Every row is a policy surface, not a log line.</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="bg-bone-100/70 text-xs uppercase tracking-[0.16em] text-graphite-500">
            <tr>
              <th className="px-6 py-4 font-medium">Session</th>
              <th className="px-6 py-4 font-medium">Agent</th>
              <th className="px-6 py-4 font-medium">Decisions</th>
              <th className="px-6 py-4 font-medium">Writes</th>
              <th className="px-6 py-4 font-medium">Risk</th>
              <th className="px-6 py-4 font-medium">Last seen</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-graphite-900/10">
            {sessions.map((session) => (
              <tr key={session.sessionId} className="transition hover:bg-verdigris-500/5">
                <td className="px-6 py-4 font-mono text-xs text-graphite-800"><Link href={`/sessions/${session.sessionId}`}>{session.sessionId}</Link></td>
                <td className="px-6 py-4 text-graphite-800">{session.agentId || "unbound"}</td>
                <td className="px-6 py-4 font-mono text-graphite-800">{session.decisions.allow}/{session.decisions.deny}/{session.decisions.requireApproval}</td>
                <td className="px-6 py-4 font-mono text-graphite-800">{session.writeActions}</td>
                <td className="px-6 py-4"><StatusPill tone={riskTone(session.riskLevel)}>{session.riskLevel}</StatusPill></td>
                <td className="px-6 py-4 font-mono text-xs text-graphite-650">{formatDateTime(session.lastSeen)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Bezel>
  );
}

function PolicyReplayPanel({ snapshot }: { snapshot: ControlPlaneSnapshot }) {
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <Bezel innerClassName="p-6">
        <div className="flex items-center gap-3">
          <GitBranch className="text-verdigris-800" size={24} />
          <h3 className="text-lg font-semibold text-graphite-950">Policy studio</h3>
        </div>
        <div className="mt-5 space-y-3">
          {snapshot.policyRevisions.map((revision) => (
            <Link key={revision.revisionId} href="/policies" className="block rounded-2xl border border-graphite-900/10 bg-bone-100/70 p-4 transition hover:border-verdigris-500/35">
              <div className="flex items-center justify-between gap-3">
                <span className="font-mono text-xs text-graphite-650">{revision.policyVersion}</span>
                <StatusPill tone="accent">{revision.status}</StatusPill>
              </div>
              <p className="mt-3 text-sm leading-6 text-graphite-800">{revision.changeSummary}</p>
            </Link>
          ))}
        </div>
      </Bezel>
      <Bezel innerClassName="p-6">
        <div className="flex items-center gap-3">
          <Pulse className="text-verdigris-800" size={24} />
          <h3 className="text-lg font-semibold text-graphite-950">Replay drift</h3>
        </div>
        <div className="mt-5 space-y-3">
          {snapshot.replayRuns.map((run) => (
            <div key={run.runId} className="rounded-2xl border border-graphite-900/10 bg-bone-100/70 p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="font-mono text-xs text-graphite-650">{run.runId}</span>
                <span className="font-mono text-xs text-graphite-650">{run.driftedEvents} drifted</span>
              </div>
              <div className="mt-3 text-sm font-semibold text-graphite-950">{run.baselinePolicyVersion} against {run.candidatePolicyVersion}</div>
            </div>
          ))}
        </div>
      </Bezel>
    </div>
  );
}

export function SessionDetailView({ detail }: { detail: SessionDetail }) {
  const session = detail.session;

  return (
    <main>
      <ShellBand className="py-10">
        <SectionHeading eyebrow="Session detail" title={session.sessionId} copy="Decision path, policy context, and evidence correlation for one agent session." />
      </ShellBand>
      <ShellBand className="grid gap-5 pb-20 lg:grid-cols-[1fr_360px]">
        <Bezel innerClassName="p-6 md:p-8">
          <div className="space-y-4">
            {detail.timeline.map((event) => (
              <div key={event.eventId} className="grid gap-4 rounded-2xl border border-graphite-900/10 bg-bone-100/70 p-4 md:grid-cols-[150px_1fr_auto] md:items-center">
                <div className="font-mono text-xs text-graphite-650">{formatTime(event.timestamp)}</div>
                <div>
                  <div className="text-sm font-semibold text-graphite-950">{event.toolName}</div>
                  <p className="mt-1 text-sm leading-6 text-graphite-650">{event.reason}</p>
                </div>
                <StatusPill tone={event.decision === "ALLOW" ? "success" : event.decision === "DENY" ? "danger" : "warning"}>{event.decision}</StatusPill>
              </div>
            ))}
          </div>
        </Bezel>
        <Bezel innerClassName="p-6">
          <FileLock className="text-verdigris-800" size={28} />
          <h3 className="mt-4 text-lg font-semibold text-graphite-950">Evidence export</h3>
          <p className="mt-2 text-sm leading-6 text-graphite-650">Signed JSON, HTML, and PDF exports remain tied to the append-only trace timeline.</p>
          <Link href="/operations" className="mt-5 inline-flex rounded-full bg-graphite-950 px-4 py-2 text-sm font-semibold text-bone-50 transition hover:-translate-y-0.5">
            Open evidence workflow
          </Link>
        </Bezel>
      </ShellBand>
    </main>
  );
}
