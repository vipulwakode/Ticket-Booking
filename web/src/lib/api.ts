import type { ApiErrorBody, HealthResponse } from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: Record<string, unknown>;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code;
    this.details = body.details;
  }
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as ApiErrorBody).code === "string" &&
    typeof (value as ApiErrorBody).message === "string"
  );
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init.headers },
    });
  } catch {
    throw new ApiError(0, {
      code: "NETWORK_ERROR",
      message: "Cannot reach the server. Check your connection and try again.",
      details: {},
    });
  }

  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(
      response.status,
      isApiErrorBody(body)
        ? { ...body, details: body.details ?? {} }
        : {
            code: "UNKNOWN_ERROR",
            message: `Request failed (${response.status})`,
            details: {},
          },
    );
  }

  return body as T;
}

export const api = {
  health: () => apiFetch<HealthResponse>("/health"),
};
