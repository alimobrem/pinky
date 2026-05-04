"use server";

import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";

interface SessionPrincipal {
  id: string;
  display_name?: string;
  email?: string | null;
  groups?: string[];
  is_admin?: boolean;
}

interface SessionResponse {
  authenticated: boolean;
  principal?: SessionPrincipal;
  session_age_minutes?: number;
}

function getBaseUrl(host: string | null, proto: string | null): string {
  const safeHost = host ?? "localhost:3000";
  const safeProto = proto ?? (safeHost.includes("localhost") ? "http" : "https");
  return `${safeProto}://${safeHost}`;
}

export async function fetchServerSession(): Promise<SessionResponse> {
  const cookieStore = await cookies();
  const sessionCookie = cookieStore.get("pinky_session");
  if (!sessionCookie) {
    return { authenticated: false };
  }

  const headerStore = await headers();
  const host = headerStore.get("x-forwarded-host") ?? headerStore.get("host");
  const proto = headerStore.get("x-forwarded-proto");
  const baseUrl = getBaseUrl(host, proto);

  try {
    const res = await fetch(`${baseUrl}/api/v1/auth/session`, {
      headers: {
        cookie: cookieStore
          .getAll()
          .map((c) => `${c.name}=${c.value}`)
          .join("; "),
      },
      cache: "no-store",
    });

    if (!res.ok) {
      return { authenticated: false };
    }

    return (await res.json()) as SessionResponse;
  } catch {
    return { authenticated: false };
  }
}

export async function requireServerSession(): Promise<SessionResponse> {
  const session = await fetchServerSession();
  if (!session.authenticated || !session.principal?.id) {
    redirect("/login");
  }
  return session;
}
