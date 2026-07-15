import { ApiError } from '@/lib/api/client';

export function getUserFacingErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message || fallback;
  }
  if (error instanceof Error) {
    return error.message || fallback;
  }
  return fallback;
}

export function isUnauthorizedError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

export function isForbiddenError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 403;
}

export function isValidationError(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 422 || error.code === 'validation_error');
}
