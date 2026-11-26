"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchHealth, fetchSystemStatus } from "@/lib/api-client";

export function useBackendHealth() {
  return useQuery({
    queryKey: ["backend-health"],
    queryFn: fetchHealth,
    refetchInterval: 15_000,
    retry: 1,
  });
}

export function useSystemStatus() {
  return useQuery({
    queryKey: ["system-status"],
    queryFn: fetchSystemStatus,
    refetchInterval: 15_000,
    retry: 1,
  });
}
