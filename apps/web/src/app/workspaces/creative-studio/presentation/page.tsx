import type { Route } from 'next';
import { redirect } from 'next/navigation';

/** Alias → canonical Presentation Builder route */
export default function PresentationAliasRedirect() {
  redirect('/workspaces/creative-studio/presentation-builder' as Route);
}
