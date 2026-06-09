"use client";

import { QueryClient } from "@tanstack/react-query";
import { SessionExpiredError } from "@/lib/api";
import { redirectToLogin } from "@/lib/session";

const onSessionError = (error: unknown) => {
  if (error instanceof SessionExpiredError) redirectToLogin();
};

let client: QueryClient | null = null;

export function getQueryClient() {
  if (!client) {
    client = new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 30_000,
          retry: (failureCount, error) => {
            if (error instanceof SessionExpiredError) return false;
            return failureCount < 1;
          },
        },
        mutations: {
          onError: onSessionError,
        },
      },
    });
    client.getQueryCache().config.onError = onSessionError;
  }
  return client;
}
