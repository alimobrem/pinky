export const dynamic = "force-dynamic";

import { requireServerSession } from "@/lib/server-auth";
import { AlertsView } from "./_components/alerts-view";

export default async function AlertsPage() {
  await requireServerSession();
  return <AlertsView />;
}
