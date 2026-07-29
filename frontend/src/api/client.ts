const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export interface ApiError {
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
  detail?:
    | {
        error?: {
          code: string;
          message: string;
        };
      }
    | string
    | unknown;
}

export class ApiClientError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

function parseErrorBody(body: ApiError | null, fallback: string): { code: string; message: string } {
  if (!body) return { code: "UNKNOWN", message: fallback };
  if (body.detail && typeof body.detail === "object" && !Array.isArray(body.detail)) {
    const nested = (body.detail as { error?: { code?: string; message?: string } }).error;
    if (nested?.message) {
      return { code: nested.code || "UNKNOWN", message: nested.message };
    }
  }
  if (body.error?.message) {
    return { code: body.error.code || "UNKNOWN", message: body.error.message };
  }
  if (typeof body.detail === "string") {
    return { code: "UNKNOWN", message: body.detail };
  }
  return { code: "UNKNOWN", message: fallback };
}

type RequestOptions = RequestInit & {
  token?: string | null;
};

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { token, headers, ...rest } = options;
  const isFormData = typeof FormData !== "undefined" && rest.body instanceof FormData;
  const response = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiError | null;
    const parsed = parseErrorBody(body, response.statusText);
    throw new ApiClientError(response.status, parsed.code, parsed.message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function apiDownload(
  path: string,
  token?: string | null,
  method: "GET" | "POST" = "GET",
): Promise<Blob> {
  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || ""}${path}`, {
    method,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiError | null;
    const parsed = parseErrorBody(body, response.statusText);
    throw new ApiClientError(response.status, parsed.code, parsed.message);
  }
  return response.blob();
}
