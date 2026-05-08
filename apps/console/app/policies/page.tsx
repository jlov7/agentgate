import { Bezel, EmptyState, Metric, SectionHeading, ShellBand, StatusPill } from "@agentgate/ui";
import { GitBranch, ShieldCheck } from "@phosphor-icons/react/dist/ssr";
import { ConsoleAction } from "../../components/console-action";
import { getControlPlaneSnapshot } from "../../lib/agentgate-data";

export default async function PoliciesPage() {
  const snapshot = await getControlPlaneSnapshot();
  const revision = snapshot.data.policyRevisions[0];
  const replay = snapshot.data.replayRuns[0];

  return (
    <main>
      <ShellBand className="py-10">
        <SectionHeading eyebrow="Policy studio" title="Review policy changes against replay evidence." copy="Policy work is treated as a release workflow: draft, replay, invariant review, publish, and rollback." />
      </ShellBand>
      <ShellBand className="grid gap-5 pb-20 lg:grid-cols-[1fr_380px]">
        <Bezel innerClassName="p-6 md:p-8">
          {revision && replay ? (
            <>
              <div className="flex items-center gap-3">
                <GitBranch size={28} className="text-verdigris-800" />
                <div>
                  <h2 className="text-xl font-semibold text-graphite-950">{revision.policyVersion}</h2>
                  <p className="mt-1 text-sm text-graphite-650">{revision.changeSummary}</p>
                </div>
                <div className="ml-auto">
                  <StatusPill tone="accent">{revision.status}</StatusPill>
                </div>
              </div>
              <div className="mt-8 grid gap-4 md:grid-cols-3">
                <Metric label="drifted events" value={String(replay.driftedEvents)} />
                <Metric label="critical drift" value={String(replay.criticalDrift)} />
                <Metric label="high drift" value={String(replay.highDrift)} />
              </div>
              <div className="mt-8 rounded-[1.5rem] border border-graphite-900/10 bg-bone-100/70 p-5">
                <h3 className="text-sm font-semibold text-graphite-950">Publish gate</h3>
                <p className="mt-2 text-sm leading-6 text-graphite-650">The candidate can publish only after replay drift is reviewed and no critical invariant fails. This demo revision is reviewed but not yet published.</p>
                <div className="mt-5">
                  <ConsoleAction
                    label="Publish revision"
                    endpoint={`policies/revisions/${revision.revisionId}/publish`}
                    payload={{ publishedBy: "console.operator" }}
                    requiredRole="policy_editor"
                    disabled={revision.status !== "reviewed" && revision.status !== "review"}
                  />
                </div>
              </div>
            </>
          ) : (
            <div className="flex items-center gap-3">
              <GitBranch size={28} className="text-verdigris-800" />
              <EmptyState title="No policy revision yet" copy="Policy revisions and replay drift appear here after the first policy lifecycle event." />
            </div>
          )}
        </Bezel>
        <Bezel innerClassName="p-6">
          <ShieldCheck size={30} className="text-verdigris-800" />
          <h3 className="mt-4 text-lg font-semibold text-graphite-950">Rollback posture</h3>
          <p className="mt-2 text-sm leading-6 text-graphite-650">Every publish action records a rollback target, policy bundle hash, reviewer, and replay evidence link.</p>
        </Bezel>
      </ShellBand>
    </main>
  );
}
