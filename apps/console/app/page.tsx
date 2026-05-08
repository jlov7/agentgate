import { HeroFrontDoor } from "../components/control-plane";
import { getControlPlaneSnapshot } from "../lib/agentgate-data";

export default async function HomePage() {
  const snapshot = await getControlPlaneSnapshot();
  return <HeroFrontDoor snapshot={snapshot.data} />;
}
