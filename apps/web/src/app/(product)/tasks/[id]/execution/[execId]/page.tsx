export const dynamic = "force-dynamic";

import { requireServerSession } from "@/lib/server-auth";
import { ExecutionDetailView } from "./_components/execution-detail-view";

export default async function ExecutionPage({
  params,
}: {
  params: Promise<{ id: string; execId: string }>;
}) {
  await requireServerSession();
  const { id, execId } = await params;
  return <ExecutionDetailView taskId={id} execId={execId} />;
}
