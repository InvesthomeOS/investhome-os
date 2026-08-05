import { redirect } from 'next/navigation';

/** Alias → canonical Landing Page Builder route */
export default function LandingPageAliasRedirect() {
  redirect('/workspaces/creative-studio/landing-page-builder');
}
