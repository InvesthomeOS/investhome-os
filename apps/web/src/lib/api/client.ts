export function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
  if (typeof window === 'undefined') {
    return configured;
  }
  try {
    const api = new URL(configured);
    const pageHost = window.location.hostname;
    // localhost vs 127.0.0.1 is cross-site; SameSite=Lax would drop ih_session.
    if (
      (pageHost === '127.0.0.1' && api.hostname === 'localhost') ||
      (pageHost === 'localhost' && api.hostname === '127.0.0.1')
    ) {
      api.hostname = pageHost;
      return api.origin;
    }
  } catch {
    return configured;
  }
  return configured;
}

const REQUEST_ID_HEADER = 'X-Request-Id';
export const CSRF_HEADER = 'X-CSRF-Token';

const STATE_CHANGING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);
const CSRF_EXEMPT_PATHS = new Set([
  '/auth/login',
  '/auth/mfa/verify',
  '/auth/mfa/enroll/required',
  '/auth/mfa/enroll/required/confirm',
]);

let csrfTokenMemory: string | null = null;

function createRequestId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `req-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function requestPath(url: string): string {
  try {
    return new URL(url, 'http://investhome.invalid').pathname;
  } catch {
    return url.split('?')[0] ?? url;
  }
}

export function clearCsrfToken(): void {
  csrfTokenMemory = null;
}

export async function ensureCsrfToken(): Promise<string | null> {
  if (csrfTokenMemory) return csrfTokenMemory;
  const response = await fetch(`${getApiBaseUrl()}/auth/csrf`, {
    credentials: 'include',
    cache: 'no-store',
  });
  if (!response.ok) return null;
  try {
    const body = (await response.json()) as { csrf_token?: string; data?: { csrf_token?: string } };
    const token = body.csrf_token ?? body.data?.csrf_token;
    if (typeof token === 'string' && token.length > 0) {
      csrfTokenMemory = token;
      return token;
    }
  } catch {
    return null;
  }
  return null;
}

export async function applyCsrfHeaders(url: string, init?: RequestInit): Promise<Headers> {
  const headers = new Headers(init?.headers);
  const method = (init?.method ?? 'GET').toUpperCase();
  if (!STATE_CHANGING_METHODS.has(method)) return headers;
  if (CSRF_EXEMPT_PATHS.has(requestPath(url))) return headers;
  if (headers.has(CSRF_HEADER)) return headers;
  const token = await ensureCsrfToken();
  if (token) headers.set(CSRF_HEADER, token);
  return headers;
}

export async function staffFetch(url: string, init?: RequestInit): Promise<Response> {
  const headers = await applyCsrfHeaders(url, init);
  return fetch(url, {
    ...init,
    credentials: 'include',
    headers,
    cache: init?.cache ?? 'no-store',
  });
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
  const url = `${getApiBaseUrl()}${path}`;
  const headers: Record<string, string> = {
    [REQUEST_ID_HEADER]: requestId,
  };
  if (!(init?.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  Object.assign(headers, init?.headers);

  const send = () =>
    staffFetch(url, {
      ...init,
      headers,
      cache: 'no-store',
    });

  let response = await send();
  const responseRequestId = response.headers.get(REQUEST_ID_HEADER) ?? requestId;

  if (response.status === 403) {
    const cloned = response.clone();
    try {
      const body = (await cloned.json()) as ApiErrorBody;
      if (body.error?.code === 'csrf_rejected') {
        clearCsrfToken();
        const refreshed = await ensureCsrfToken();
        if (refreshed) {
          headers[CSRF_HEADER] = refreshed;
          response = await send();
        }
      }
    } catch {
      // Keep original 403 when body is not JSON.
    }
  }

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
