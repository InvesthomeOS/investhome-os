/** Pure helpers for Media Library tagging + multi-select. */

const RECENT_TAGS_KEY = 'cs-media-library-recent-tags';
const RECENT_TAGS_MAX = 12;

export function normalizeTag(raw: string): string {
  return raw.trim().replace(/\s+/g, ' ');
}

export function uniqueTags(tags: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of tags) {
    const tag = normalizeTag(raw);
    if (!tag) continue;
    const key = tag.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(tag);
  }
  return out;
}

export function mergeTags(existing: string[], toAdd: string[]): string[] {
  return uniqueTags([...existing, ...toAdd]);
}

export function removeTags(existing: string[], toRemove: string[]): string[] {
  const drop = new Set(toRemove.map((t) => normalizeTag(t).toLowerCase()).filter(Boolean));
  return existing.filter((t) => !drop.has(normalizeTag(t).toLowerCase()));
}

export function collectLibraryTags(assets: { tags: string[] }[]): string[] {
  return uniqueTags(assets.flatMap((a) => a.tags));
}

export function collectUnionTags(assets: { tags: string[] }[]): string[] {
  return uniqueTags(assets.flatMap((a) => a.tags));
}

export function readRecentTags(): string[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(RECENT_TAGS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return uniqueTags(parsed.map((item) => String(item))).slice(0, RECENT_TAGS_MAX);
  } catch {
    return [];
  }
}

export function pushRecentTags(tags: string[]): string[] {
  const next = uniqueTags([...tags, ...readRecentTags()]).slice(0, RECENT_TAGS_MAX);
  if (typeof window !== 'undefined') {
    try {
      window.localStorage.setItem(RECENT_TAGS_KEY, JSON.stringify(next));
    } catch {
      // ignore quota / private mode
    }
  }
  return next;
}

export function filterTagSuggestions(
  allTags: string[],
  query: string,
  exclude: string[] = [],
): string[] {
  const q = query.trim().toLowerCase();
  const excluded = new Set(exclude.map((t) => t.toLowerCase()));
  return allTags.filter((tag) => {
    if (excluded.has(tag.toLowerCase())) return false;
    if (!q) return true;
    return tag.toLowerCase().includes(q);
  });
}

/** Inclusive range selection between two ids in ordered list. */
export function rangeSelectIds(
  orderedIds: string[],
  fromId: string,
  toId: string,
): string[] {
  const a = orderedIds.indexOf(fromId);
  const b = orderedIds.indexOf(toId);
  if (a < 0 || b < 0) return [toId];
  const start = Math.min(a, b);
  const end = Math.max(a, b);
  return orderedIds.slice(start, end + 1);
}
