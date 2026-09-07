"use client";
import useSWR from "swr";
import { fetchIncident } from "../lib/api";
import type { Incident } from "../lib/types";

export function useIncidentDetail(id: string | null) {
  const { data, error, isLoading } = useSWR<Incident>(
    id ? ["incident", id] : null,
    () => fetchIncident(id!),
    { revalidateOnFocus: false }
  );

  return { incident: data ?? null, isLoading, error };
}
