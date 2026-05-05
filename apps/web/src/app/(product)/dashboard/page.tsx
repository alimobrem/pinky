export const dynamic = "force-dynamic";

import { requireServerSession } from "@/lib/server-auth";
import { DashboardView } from "./_components/dashboard-view";

export default async function DashboardPage() {
  await requireServerSession();
  return <DashboardView />;
}
