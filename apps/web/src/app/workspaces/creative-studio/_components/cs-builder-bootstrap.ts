/**
 * Shared bootstrap helpers for Creative Studio Document API loaders.
 */

export const CS_BUILDER_BOOTSTRAP_TIMEOUT_MS = 45_000;

export async function withCsBuilderTimeout<T>(
  promise: Promise<T>,
  options?: { timeoutMs?: number; message?: string },
): Promise<T> {
  const timeoutMs = options?.timeoutMs ?? CS_BUILDER_BOOTSTRAP_TIMEOUT_MS;
  const message =
    options?.message ??
    `Builder bootstrap timed out after ${Math.round(timeoutMs / 1000)}s`;

  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      promise,
      new Promise<T>((_, reject) => {
        timer = setTimeout(() => reject(new Error(message)), timeoutMs);
      }),
    ]);
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}
