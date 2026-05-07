import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { QUERY_KEYS } from "@/lib/constants";

interface SessionResponse {
  authenticated: boolean;
  principal?: {
    id: string;
    provider: string;
    email: string;
    display_name: string;
    groups: string[];
    is_admin: boolean;
  };
  session_age_minutes?: number;
}

export function useCurrentUser() {
  const query = useQuery({
    queryKey: QUERY_KEYS.session(),
    queryFn: () => api.get<SessionResponse>("/api/v1/auth/session"),
    staleTime: 5 * 60 * 1000,
  });

  return {
    ...query,
    user: query.data?.principal ?? null,
  };
}
