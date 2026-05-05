export const dynamic = "force-dynamic";

import { requireServerSession } from "@/lib/server-auth";
import { WatchView } from "./_components/watch-view";

export default async function WatchPage() {
  await requireServerSession();
  return <WatchView />;
}
