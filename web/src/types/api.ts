export interface ApiErrorBody {
  code: string;
  message: string;
  details: Record<string, unknown>;
}

export interface HealthResponse {
  status: "ok";
  database: "ok";
}
