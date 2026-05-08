import { SessionDetailView } from "../../../components/control-plane";
import { getSessionDetail } from "../../../lib/agentgate-data";

export default async function SessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  const detail = await getSessionDetail(sessionId);
  return <SessionDetailView detail={detail.data} />;
}
