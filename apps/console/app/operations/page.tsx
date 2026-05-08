import { Bezel, EmptyState, SectionHeading, ShellBand, StatusPill } from "@agentgate/ui";
import { Archive, Siren, SlidersHorizontal } from "@phosphor-icons/react/dist/ssr";
import { ConsoleAction } from "../../components/console-action";
import { getControlPlaneSnapshot } from "../../lib/agentgate-data";

export default async function OperationsPage() {
  const snapshot = await getControlPlaneSnapshot();

  return (
    <main>
      <ShellBand className="py-10">
        <SectionHeading eyebrow="Operations" title="Incident, rollout, and audit work in one place." copy="Operations pages are built for repeated action: release incidents, inspect rollouts, package evidence, and hand support a reproducible bundle." />
      </ShellBand>
      <ShellBand className="grid gap-5 pb-20 lg:grid-cols-3">
        <Bezel innerClassName="p-6">
          <Siren size={28} className="text-amber-700" />
          <h2 className="mt-4 text-lg font-semibold text-graphite-950">Incidents</h2>
          <div className="mt-4 space-y-3">
            {snapshot.data.incidents.map((incident) => (
              <div key={incident.incidentId} className="rounded-2xl border border-amber-500/25 bg-amber-500/10 p-4">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-graphite-650">{incident.incidentId}</span>
                  <StatusPill tone="warning">{incident.status}</StatusPill>
                </div>
                <p className="mt-3 text-sm leading-6 text-graphite-800">{incident.reason}</p>
                <div className="mt-4">
                  <ConsoleAction
                    label="Release incident"
                    endpoint={`incidents/${incident.incidentId}/release`}
                    payload={{ releasedBy: "console.operator" }}
                    requiredRole="operator"
                    disabled={incident.status === "released"}
                  />
                </div>
              </div>
            ))}
          </div>
        </Bezel>
        <Bezel innerClassName="p-6">
          <SlidersHorizontal size={28} className="text-verdigris-800" />
          <h2 className="mt-4 text-lg font-semibold text-graphite-950">Rollouts</h2>
          <div className="mt-4 space-y-3">
            {snapshot.data.rollouts.map((rollout) => (
              <div key={rollout.rolloutId} className="rounded-2xl border border-graphite-900/10 bg-bone-100/70 p-4">
                <div className="font-mono text-xs text-graphite-650">{rollout.rolloutId}</div>
                <p className="mt-2 text-sm font-semibold text-graphite-950">{rollout.baselineVersion} to {rollout.candidateVersion}</p>
                <p className="mt-2 text-sm text-graphite-650">{rollout.status}, {rollout.verdict}</p>
                <div className="mt-4">
                  <ConsoleAction
                    label="Rollback"
                    endpoint={`rollouts/${rollout.rolloutId}/rollback`}
                    payload={{ tenantId: rollout.tenantId, reason: "console rollback" }}
                    requiredRole="operator"
                    disabled={rollout.status === "rolled_back"}
                  />
                </div>
              </div>
            ))}
          </div>
        </Bezel>
        <Bezel innerClassName="p-6">
          <Archive size={28} className="text-verdigris-800" />
          <h2 className="mt-4 text-lg font-semibold text-graphite-950">Support bundle</h2>
          <EmptyState title="Ready to package" copy="Support bundles include doctor logs, scorecards, security closure, replay, incident, and rollout artifacts." />
        </Bezel>
      </ShellBand>
    </main>
  );
}
