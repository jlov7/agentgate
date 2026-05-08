"use client";

import { ControlPlaneSnapshotSchema, type ControlPlaneSnapshot } from "@agentgate/client";
import { EmptyState } from "@agentgate/ui";
import { useQuery } from "@tanstack/react-query";
import { CommandCenter } from "./control-plane";

export function LiveCommandCenter({ initialSnapshot }: { initialSnapshot: ControlPlaneSnapshot }) {
  const query = useQuery({
    queryKey: ["control-overview"],
    initialData: initialSnapshot,
    refetchInterval: 15_000,
    queryFn: async () => {
      const response = await fetch("/api/agentgate/control/overview", {
        headers: { accept: "application/json" },
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error(`Console BFF returned ${response.status}`);
      }
      return ControlPlaneSnapshotSchema.parse(await response.json());
    },
  });

  return (
    <CommandCenter
      snapshot={query.data ?? initialSnapshot}
      liveState={{
        refreshing: query.isFetching,
        error: query.isError ? (
          <EmptyState
            title="Live refresh paused"
            copy="The console is showing the last valid snapshot while the BFF retries."
          />
        ) : null,
      }}
    />
  );
}
