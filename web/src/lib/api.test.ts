import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiFetch } from "./api";

function mockFetch(response: Response | Error) {
  const fn =
    response instanceof Error
      ? vi.fn().mockRejectedValue(response)
      : vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fn);
  return fn;
}

describe("apiFetch", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the parsed JSON body on success", async () => {
    const fetchMock = mockFetch(Response.json({ status: "ok", database: "ok" }));

    await expect(apiFetch("/health")).resolves.toEqual({ status: "ok", database: "ok" });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/health",
      expect.objectContaining({ headers: { "Content-Type": "application/json" } }),
    );
  });

  it("throws ApiError carrying the API's code and message", async () => {
    mockFetch(
      Response.json(
        { code: "SEAT_UNAVAILABLE", message: "Seats taken", details: { seat_ids: [1] } },
        { status: 409 },
      ),
    );

    const error = await apiFetch("/holds").catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 409,
      code: "SEAT_UNAVAILABLE",
      message: "Seats taken",
      details: { seat_ids: [1] },
    });
  });

  it("falls back to a generic message when the error body is not JSON", async () => {
    mockFetch(new Response("<html>Bad Gateway</html>", { status: 502 }));

    await expect(apiFetch("/health")).rejects.toMatchObject({
      status: 502,
      code: "UNKNOWN_ERROR",
      message: "Request failed (502)",
    });
  });

  it("reports network failures with a readable message", async () => {
    mockFetch(new TypeError("Failed to fetch"));

    await expect(apiFetch("/health")).rejects.toMatchObject({
      status: 0,
      code: "NETWORK_ERROR",
    });
  });
});
