export const dynamic = "force-dynamic";

import { requireServerSession } from "@/lib/server-auth";
import { SettingsView } from "./_components/settings-view";

export default async function SettingsPage() {
  await requireServerSession();
  return <SettingsView />;
}
