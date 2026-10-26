import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api, ApiError } from "@/lib/api";

import HomePage from "./page";

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <HomePage />
    </QueryClientProvider>,
  );
}

describe("HomePage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows API OK when the health check succeeds", async () => {
    vi.spyOn(api, "health").mockResolvedValue({ status: "ok", database: "ok" });

    renderPage();

    expect(await screen.findByText("API OK")).toBeInTheDocument();
  });

  it("shows the API error message when the health check fails", async () => {
    vi.spyOn(api, "health").mockRejectedValue(
      new ApiError(503, {
        code: "SERVICE_UNAVAILABLE",
        message: "Database is unavailable",
        details: {},
      }),
    );

    renderPage();

    expect(await screen.findByText("Database is unavailable")).toBeInTheDocument();
  });
});
