import { z } from "zod";

export const RiskLevelSchema = z.enum(["normal", "elevated", "critical"]);
export type RiskLevel = z.infer<typeof RiskLevelSchema>;

export const DecisionCountSchema = z.object({
  allow: z.number().int().nonnegative(),
  deny: z.number().int().nonnegative(),
  requireApproval: z.number().int().nonnegative(),
});
export type DecisionCount = z.infer<typeof DecisionCountSchema>;

export const SessionListItemSchema = z.object({
  sessionId: z.string(),
  tenantId: z.string().nullable(),
  userId: z.string().nullable(),
  agentId: z.string().nullable(),
  firstSeen: z.string(),
  lastSeen: z.string(),
  toolCalls: z.number().int().nonnegative(),
  writeActions: z.number().int().nonnegative(),
  decisions: DecisionCountSchema,
  riskLevel: RiskLevelSchema,
  status: z.enum(["active", "contained", "review", "quiet"]),
});
export type SessionListItem = z.infer<typeof SessionListItemSchema>;

export const TimelineEventSchema = z.object({
  eventId: z.string(),
  timestamp: z.string(),
  toolName: z.string(),
  policyVersion: z.string(),
  decision: z.string(),
  reason: z.string(),
  matchedRule: z.string().nullable(),
  executed: z.boolean(),
  durationMs: z.number().int().nullable(),
  error: z.string().nullable(),
  writeAction: z.boolean(),
  approvalTokenPresent: z.boolean(),
});
export type TimelineEvent = z.infer<typeof TimelineEventSchema>;

export const SessionDetailSchema = z.object({
  session: SessionListItemSchema,
  timeline: z.array(TimelineEventSchema),
  taintLabels: z.array(z.string()),
  evidenceExports: z.array(
    z.object({
      archiveId: z.string(),
      format: z.string(),
      createdAt: z.string(),
      immutable: z.boolean(),
    }),
  ),
});
export type SessionDetail = z.infer<typeof SessionDetailSchema>;

export const PolicyRevisionSchema = z.object({
  revisionId: z.string(),
  policyVersion: z.string(),
  status: z.string(),
  createdBy: z.string().nullable(),
  createdAt: z.string(),
  changeSummary: z.string().nullable(),
});
export type PolicyRevision = z.infer<typeof PolicyRevisionSchema>;

export const ReplayRunSummarySchema = z.object({
  runId: z.string(),
  sessionId: z.string().nullable(),
  baselinePolicyVersion: z.string(),
  candidatePolicyVersion: z.string(),
  status: z.string(),
  driftedEvents: z.number().int().nonnegative(),
  criticalDrift: z.number().int().nonnegative(),
  highDrift: z.number().int().nonnegative(),
  createdAt: z.string(),
});
export type ReplayRunSummary = z.infer<typeof ReplayRunSummarySchema>;

export const IncidentSummarySchema = z.object({
  incidentId: z.string(),
  sessionId: z.string(),
  status: z.string(),
  riskScore: z.number().int().nonnegative(),
  reason: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
});
export type IncidentSummary = z.infer<typeof IncidentSummarySchema>;

export const RolloutSummarySchema = z.object({
  rolloutId: z.string(),
  tenantId: z.string(),
  baselineVersion: z.string(),
  candidateVersion: z.string(),
  status: z.string(),
  verdict: z.string(),
  criticalDrift: z.number().int().nonnegative(),
  highDrift: z.number().int().nonnegative(),
  updatedAt: z.string(),
});
export type RolloutSummary = z.infer<typeof RolloutSummarySchema>;

export const ControlPlaneSnapshotSchema = z.object({
  generatedAt: z.string(),
  environment: z.string(),
  tenantId: z.string(),
  policyVersion: z.string(),
  riskLevel: RiskLevelSchema,
  sessions: z.array(SessionListItemSchema),
  decisions: DecisionCountSchema,
  incidents: z.array(IncidentSummarySchema),
  rollouts: z.array(RolloutSummarySchema),
  replayRuns: z.array(ReplayRunSummarySchema),
  policyRevisions: z.array(PolicyRevisionSchema),
  slo: z.object({
    enabled: z.boolean(),
    availabilityTarget: z.number(),
    p95LatencySeconds: z.number(),
    status: z.enum(["pass", "watch", "breach"]),
  }),
});
export type ControlPlaneSnapshot = z.infer<typeof ControlPlaneSnapshotSchema>;

export const EventEnvelopeSchema = z.object({
  eventId: z.string(),
  eventType: z.string(),
  emittedAt: z.string(),
  payload: z.unknown(),
});
export type EventEnvelope = z.infer<typeof EventEnvelopeSchema>;

const demoNow = "2026-05-08T16:00:00.000Z";

export const demoSnapshot: ControlPlaneSnapshot = {
  generatedAt: demoNow,
  environment: "demo",
  tenantId: "northstar-bank",
  policyVersion: "v2.2",
  riskLevel: "elevated",
  decisions: { allow: 184, deny: 17, requireApproval: 9 },
  slo: {
    enabled: true,
    availabilityTarget: 0.995,
    p95LatencySeconds: 0.42,
    status: "pass",
  },
  sessions: [
    {
      sessionId: "sess-containment-8241",
      tenantId: "northstar-bank",
      userId: "mira.halberg",
      agentId: "payments-recon-agent",
      firstSeen: "2026-05-08T15:42:10.000Z",
      lastSeen: "2026-05-08T15:59:35.000Z",
      toolCalls: 41,
      writeActions: 6,
      decisions: { allow: 31, deny: 5, requireApproval: 5 },
      riskLevel: "elevated",
      status: "review",
    },
    {
      sessionId: "sess-rollout-3917",
      tenantId: "northstar-bank",
      userId: "devon.kappel",
      agentId: "policy-canary-agent",
      firstSeen: "2026-05-08T15:18:44.000Z",
      lastSeen: "2026-05-08T15:57:04.000Z",
      toolCalls: 83,
      writeActions: 0,
      decisions: { allow: 79, deny: 4, requireApproval: 0 },
      riskLevel: "normal",
      status: "active",
    },
  ],
  incidents: [
    {
      incidentId: "inc-42b7",
      sessionId: "sess-containment-8241",
      status: "quarantined",
      riskScore: 82,
      reason: "write action requested after tainted context touched credentials",
      createdAt: "2026-05-08T15:56:22.000Z",
      updatedAt: "2026-05-08T15:58:51.000Z",
    },
  ],
  rollouts: [
    {
      rolloutId: "rollout-v2-2-bank",
      tenantId: "northstar-bank",
      baselineVersion: "v2.1",
      candidateVersion: "v2.2",
      status: "promoting",
      verdict: "pass",
      criticalDrift: 0,
      highDrift: 1,
      updatedAt: "2026-05-08T15:54:00.000Z",
    },
  ],
  replayRuns: [
    {
      runId: "replay-77a9",
      sessionId: "sess-containment-8241",
      baselinePolicyVersion: "v2.1",
      candidatePolicyVersion: "v2.2",
      status: "completed",
      driftedEvents: 6,
      criticalDrift: 0,
      highDrift: 1,
      createdAt: "2026-05-08T15:53:31.000Z",
    },
  ],
  policyRevisions: [
    {
      revisionId: "rev-v2-2",
      policyVersion: "v2.2",
      status: "reviewed",
      createdBy: "nina.oshaughnessy",
      createdAt: "2026-05-08T14:30:00.000Z",
      changeSummary: "tighten credential writes after external context ingestion",
    },
  ],
};

export function buildDemoSessionDetail(sessionId: string): SessionDetail {
  const session = demoSnapshot.sessions.find((item) => item.sessionId === sessionId) ?? demoSnapshot.sessions[0];
  return SessionDetailSchema.parse({
    session,
    timeline: [
      {
        eventId: "evt-101",
        timestamp: session.firstSeen,
        toolName: "db_query",
        policyVersion: demoSnapshot.policyVersion,
        decision: "ALLOW",
        reason: "read scope matched approved analytics rule",
        matchedRule: "tools.read.analytics",
        executed: true,
        durationMs: 91,
        error: null,
        writeAction: false,
        approvalTokenPresent: false,
      },
      {
        eventId: "evt-102",
        timestamp: session.lastSeen,
        toolName: "credential_write",
        policyVersion: demoSnapshot.policyVersion,
        decision: "REQUIRE_APPROVAL",
        reason: "write action after tainted context requires human approval",
        matchedRule: "risk.tainted_context.write_guard",
        executed: false,
        durationMs: 37,
        error: null,
        writeAction: true,
        approvalTokenPresent: false,
      },
      {
        eventId: "evt-103",
        timestamp: demoSnapshot.generatedAt,
        toolName: "external_transfer",
        policyVersion: demoSnapshot.policyVersion,
        decision: "DENY",
        reason: "destination outside tenant trust boundary",
        matchedRule: "tenant.egress.boundary",
        executed: false,
        durationMs: 22,
        error: "blocked by policy",
        writeAction: true,
        approvalTokenPresent: true,
      },
    ],
    taintLabels: ["credentials", "external-context"],
    evidenceExports: [
      {
        archiveId: "ev-demo-json",
        format: "json",
        createdAt: demoSnapshot.generatedAt,
        immutable: true,
      },
      {
        archiveId: "ev-demo-pdf",
        format: "pdf",
        createdAt: demoSnapshot.generatedAt,
        immutable: true,
      },
    ],
  });
}

export async function fetchControlPlaneSnapshot(baseUrl = ""): Promise<ControlPlaneSnapshot> {
  const response = await fetch(`${baseUrl}/api/agentgate/control/overview`, {
    headers: { accept: "application/json" },
    cache: "no-store",
  });
  if (!response.ok) {
    return demoSnapshot;
  }
  const payload = await response.json();
  return ControlPlaneSnapshotSchema.parse(payload);
}
