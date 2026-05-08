import {
  buildDemoSessionDetail,
  ControlPlaneSnapshotSchema,
  demoSnapshot,
  SessionDetailSchema,
  type ControlPlaneSnapshot,
  type SessionDetail,
} from "@agentgate/client";
import { z } from "zod";

const backendBaseUrl = process.env.AGENTGATE_API_BASE_URL || "";
const adminKey = process.env.AGENTGATE_ADMIN_API_KEY || "";

type DataResult<T> = {
  data: T;
  mode: "live" | "demo";
  error?: string;
};

export async function getControlPlaneSnapshot(): Promise<DataResult<ControlPlaneSnapshot>> {
  return fetchBackendJson("control/overview", ControlPlaneSnapshotSchema, demoSnapshot);
}

export async function getSessionDetail(sessionId: string): Promise<DataResult<SessionDetail>> {
  return fetchBackendJson(
    `sessions/${encodeURIComponent(sessionId)}`,
    SessionDetailSchema,
    buildDemoSessionDetail(sessionId),
  );
}

async function fetchBackendJson<T>(
  path: string,
  schema: z.ZodType<T>,
  fallback: T,
): Promise<DataResult<T>> {
  if (!backendBaseUrl) {
    return { data: fallback, mode: "demo" };
  }

  try {
    const headers: HeadersInit = { accept: "application/json" };
    if (adminKey) {
      headers["X-AgentGate-Admin-Key"] = adminKey;
    }
    const response = await fetch(new URL(`/api/v1/${path}`, backendBaseUrl), {
      headers,
      cache: "no-store",
    });
    if (!response.ok) {
      return { data: fallback, mode: "demo", error: `Backend returned ${response.status}` };
    }
    return { data: schema.parse(await response.json()), mode: "live" };
  } catch (error) {
    return {
      data: fallback,
      mode: "demo",
      error: error instanceof Error ? error.message : "Unknown backend error",
    };
  }
}
