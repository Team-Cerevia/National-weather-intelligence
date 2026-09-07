"use client";
import useSWR from "swr";
import { fetchIncidents } from "../lib/api";
import type { Incident, IncidentFilters } from "../lib/types";

export function useIncidents(filters: IncidentFilters = {}) {
  const key = ["incidents", JSON.stringify(filters)];
  const { data, error, isLoading, mutate } = useSWR<Incident[]>(
    key,
    () => fetchIncidents(filters, 200),
    {
      refreshInterval: 60_000, // re-poll every 60s as safety net
      revalidateOnFocus: false,
      keepPreviousData: true,
    }
  );

  return {
    incidents: data ?? [],
    isLoading,
    error,
    refresh: mutate,
  };
}
