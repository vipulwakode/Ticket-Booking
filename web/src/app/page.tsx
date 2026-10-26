"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export default function HomePage() {
  const health = useQuery({ queryKey: ["health"], queryFn: api.health });

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-2xl font-semibold">Ticket Booking</h1>
      <div role="status" className="w-full rounded-lg border bg-white p-4 shadow-sm">
        {health.isPending && <p className="text-slate-500">Checking API…</p>}
        {health.isSuccess && health.data.status === "ok" && (
          <p className="font-medium text-green-700">API OK</p>
        )}
        {health.isError && (
          <div className="space-y-2">
            <p className="font-medium text-red-700">{health.error.message}</p>
            <button
              type="button"
              onClick={() => health.refetch()}
              className="rounded-md bg-slate-900 px-3 py-1.5 text-sm text-white"
            >
              Retry
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
