import { LiveCommandCenter } from "../../components/live-command-center";
import { getControlPlaneSnapshot } from "../../lib/agentgate-data";

export default async function ConsolePage() {
  const snapshot = await getControlPlaneSnapshot();
  return <LiveCommandCenter initialSnapshot={snapshot.data} />;
}
