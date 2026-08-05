import type { Route } from 'next';
import { redirect } from 'next/navigation';

/** Alias → canonical Social Media Builder route */
export default function SocialAliasRedirect() {
  redirect('/workspaces/creative-studio/social-media-builder' as Route);
}
