import type { Route } from 'next';
import { redirect } from 'next/navigation';

/** Alias → canonical Presentation Builder route */
export default function PresentationBuilderAliasRedirect() {
  redirect('/workspaces/creative-studio/presentation-builder' as Route);
}
