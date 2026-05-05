export const dynamic = "force-dynamic";

import { requireServerSession } from "@/lib/server-auth";
import { HistoryView } from "./_components/history-view";

export default async function HistoryPage() {
  await requireServerSession();
  return <HistoryView />;
}
