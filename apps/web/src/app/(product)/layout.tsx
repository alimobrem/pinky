export const dynamic = "force-dynamic";

import type { ReactNode } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { requireServerSession } from "@/lib/server-auth";

export default async function ProductLayout({ children }: { children: ReactNode }) {
  await requireServerSession();

  return <AppShell>{children}</AppShell>;
}
