import { buildDemoSessionDetail, demoSnapshot } from "@agentgate/client";

const backendBaseUrl = process.env.AGENTGATE_API_BASE_URL || "";
const adminKey = process.env.AGENTGATE_ADMIN_API_KEY || "";

async function proxy(request: Request, path: string[]) {
  const joinedPath = path.join("/");
  if (!backendBaseUrl) {
    if (request.method === "GET") {
      const demo = demoResponse(joinedPath);
      if (demo) {
        return demo;
      }
    }
    if (request.method === "POST") {
      const demo = demoMutationResponse(joinedPath);
      if (demo) {
        return demo;
      }
    }
    return Response.json(
      {
        error: "AgentGate backend is not configured for this console route.",
        hint: "Set AGENTGATE_API_BASE_URL for live data or use the built-in demo snapshot.",
      },
      { status: 503 },
    );
  }

  const upstream = new URL(`/api/v1/${joinedPath}`, backendBaseUrl);
  const incoming = new URL(request.url);
  upstream.search = incoming.search;

  const headers = new Headers(request.headers);
  headers.delete("host");
  if (adminKey) {
    headers.set("X-AgentGate-Admin-Key", adminKey);
  }

  const response = await fetch(upstream, {
    method: request.method,
    headers,
    body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.text(),
    cache: "no-store",
  });

  return new Response(response.body, {
    status: response.status,
    headers: response.headers,
  });
}

function demoResponse(joinedPath: string): Response | null {
  if (joinedPath === "control/overview") return Response.json(demoSnapshot);
  if (joinedPath === "sessions") return Response.json(demoSnapshot.sessions);
  if (joinedPath.startsWith("sessions/")) {
    const sessionId = decodeURIComponent(joinedPath.slice("sessions/".length));
    return Response.json(buildDemoSessionDetail(sessionId));
  }
  if (joinedPath === "policies/revisions") return Response.json(demoSnapshot.policyRevisions);
  if (joinedPath === "replay/runs") return Response.json(demoSnapshot.replayRuns);
  if (joinedPath === "incidents") return Response.json(demoSnapshot.incidents);
  if (joinedPath === "rollouts") return Response.json(demoSnapshot.rollouts);
  return null;
}

function demoMutationResponse(joinedPath: string): Response | null {
  if (joinedPath.match(/^policies\/revisions\/[^/]+\/publish$/)) {
    return Response.json({ status: "published", revision: demoSnapshot.policyRevisions[0] });
  }
  if (joinedPath.match(/^incidents\/[^/]+\/release$/)) {
    return Response.json({ status: "released" });
  }
  if (joinedPath.match(/^rollouts\/[^/]+\/rollback$/)) {
    return Response.json({ status: "rolled_back", rollout: demoSnapshot.rollouts[0] });
  }
  if (joinedPath === "replay/runs") {
    return Response.json({ status: "completed", run_id: "replay-demo" });
  }
  return null;
}

export async function GET(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const params = await context.params;
  return proxy(request, params.path);
}

export async function POST(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const params = await context.params;
  return proxy(request, params.path);
}
