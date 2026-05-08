import { describe, expect, it } from "vitest";
import { ControlPlaneSnapshotSchema, demoSnapshot } from "@agentgate/client";

describe("console contract fixtures", () => {
  it("keeps the demo snapshot aligned with the public schema", () => {
    const parsed = ControlPlaneSnapshotSchema.parse(demoSnapshot);

    expect(parsed.tenantId).toBe("northstar-bank");
    expect(parsed.sessions.length).toBeGreaterThan(0);
    expect(parsed.decisions.requireApproval).toBeGreaterThan(0);
  });
});
