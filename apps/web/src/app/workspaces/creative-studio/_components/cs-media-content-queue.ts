/**
 * Bounds concurrent Drive / Media Library `/content` blob fetches so they cannot
 * starve Document API (and other critical) requests under browser connection limits.
 */

export const CS_MEDIA_CONTENT_MAX_CONCURRENT = 2;

let active = 0;
const waiting: Array<() => void> = [];

function pump(): void {
  while (active < CS_MEDIA_CONTENT_MAX_CONCURRENT && waiting.length) {
    const next = waiting.shift();
    if (next) next();
  }
}

/** Run a media content fetch with a shared concurrency cap. */
export function withCsMediaContentLimit<T>(task: () => Promise<T>): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const start = () => {
      active += 1;
      task().then(resolve, reject).finally(() => {
        active -= 1;
        pump();
      });
    };
    if (active < CS_MEDIA_CONTENT_MAX_CONCURRENT) {
      start();
    } else {
      waiting.push(start);
    }
  });
}
