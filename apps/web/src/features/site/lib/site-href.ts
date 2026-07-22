/**
 * Site route cast helper for Next.js typedRoutes with dynamic / query paths.
 */
import type { Route } from 'next';

export function siteHref(path: string): Route {
  return path as Route;
}
