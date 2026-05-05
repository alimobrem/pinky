export const dynamic = "force-dynamic";

import { requireServerSession } from "@/lib/server-auth";
import { TaskDetailView } from "./_components/task-detail-view";

export default async function TaskDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  await requireServerSession();
  const { id } = await params;
  return <TaskDetailView taskId={id} />;
}
