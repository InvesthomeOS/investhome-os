import type { Route } from 'next';
import { redirect } from 'next/navigation';

/** Alias → canonical Image Builder route */
export default function ImageStudioAliasRedirect() {
  redirect('/workspaces/creative-studio/image-builder' as Route);
}
