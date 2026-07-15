export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
}

const REQUEST_ID_HEADER = 'X-Request-Id';

function createRequestId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `req-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export type ApiErrorBody = {
  success?: boolean;
  detail?: string | { msg: string; loc?: string[] }[];
  error?: { code?: string; message?: string; field?: string | null };
  meta?: { request_id?: string | null };
  details?: { code: string; message: string; field?: string | null }[];
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
    readonly requestId?: string | null,
    readonly details?: ApiErrorBody['details'],
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export function parseApiErrorBody(body: ApiErrorBody, status: number): ApiError {
  const requestId = body.meta?.request_id ?? null;
  const code = body.error?.code;
  let message = `Request failed with status ${status}`;

  if (typeof body.detail === 'string') {
    message = body.detail;
  } else if (body.error?.message) {
    message = body.error.message;
  } else if (Array.isArray(body.detail) && body.detail[0]?.msg) {
    message = body.detail[0].msg;
  }

  return new ApiError(message, status, code, requestId, body.details);
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const requestId = createRequestId();
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      [REQUEST_ID_HEADER]: requestId,
      ...init?.headers,
    },
    cache: 'no-store',
  });

  const responseRequestId = response.headers.get(REQUEST_ID_HEADER) ?? requestId;

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    let code: string | undefined;
    let details: ApiErrorBody['details'];
    try {
      const body = (await response.json()) as ApiErrorBody;
      const parsed = parseApiErrorBody(body, response.status);
      message = parsed.message;
      code = parsed.code;
      details = parsed.details;
    } catch {
      // Keep default message when response is not JSON.
    }
    throw new ApiError(message, response.status, code, responseRequestId, details);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export type ApiEnvelope<T> = {
  success: boolean;
  data: T;
  meta?: { request_id?: string | null; page?: number; page_size?: number; total?: number; pages?: number };
};

export function unwrapApiEnvelope<T>(payload: T | ApiEnvelope<T>): T {
  if (payload && typeof payload === 'object' && 'success' in payload && 'data' in payload) {
    return (payload as ApiEnvelope<T>).data;
  }
  return payload as T;
}
