export const dynamic = "force-dynamic";

import { requireServerSession } from "@/lib/server-auth";
import { TasksView } from "./_components/tasks-view";

export default async function TasksPage() {
  await requireServerSession();
  return <TasksView />;
}
