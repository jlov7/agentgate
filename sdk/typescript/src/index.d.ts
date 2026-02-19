export interface AgentGateClientOptions {
  baseUrl: string;
  apiKey?: string;
  tenantId?: string;
  requestedApiVersion?: string;
  headers?: Record<string, string>;
  fetchImpl?: typeof fetch;
}

export interface AgentGateFromEnvOptions {
  env?: Record<string, string | undefined>;
  headers?: Record<string, string>;
  fetchImpl?: typeof fetch;
}

export class AgentGateApiError extends Error {
  readonly method: string;
  readonly path: string;
  readonly statusCode: number;
  readonly payload: unknown;
}

export class AgentGateClient {
  constructor(options: AgentGateClientOptions);

  static fromEnv(options?: AgentGateFromEnvOptions): AgentGateClient;

  health(): Promise<Record<string, unknown>>;
  listTools(input: { sessionId: string }): Promise<Record<string, unknown>>;
  callTool(input: {
    sessionId: string;
    toolName: string;
    arguments: Record<string, unknown>;
    approvalToken?: string;
    context?: Record<string, unknown>;
  }): Promise<Record<string, unknown>>;
  killSession(input: { sessionId: string; reason?: string }): Promise<void>;
  exportEvidence(input: { sessionId: string }): Promise<Record<string, unknown>>;

  createPolicyException(input: {
    toolName: string;
    reason: string;
    expiresInSeconds: number;
    sessionId?: string;
    tenantId?: string;
    createdBy?: string;
    apiKey?: string;
  }): Promise<Record<string, unknown>>;
  listPolicyExceptions(input?: {
    includeInactive?: boolean;
    apiKey?: string;
  }): Promise<Record<string, unknown>>;
  revokePolicyException(input: {
    exceptionId: string;
    revokedBy?: string;
    apiKey?: string;
  }): Promise<Record<string, unknown>>;

  createReplayRun(input: {
    payload: Record<string, unknown>;
    apiKey?: string;
    tenantId?: string;
  }): Promise<Record<string, unknown>>;
  releaseIncident(input: {
    incidentId: string;
    releasedBy: string;
    apiKey?: string;
    tenantId?: string;
  }): Promise<Record<string, unknown>>;
  startRollout(input: {
    tenantId: string;
    payload: Record<string, unknown>;
    apiKey?: string;
  }): Promise<Record<string, unknown>>;
  getRolloutObservability(input: {
    tenantId: string;
    apiKey?: string;
  }): Promise<Record<string, unknown>>;
}

export default AgentGateClient;
