import { redirect } from 'next/navigation';

/** Alias → canonical Email Builder route */
export default function EmailStudioAliasRedirect() {
  redirect('/workspaces/creative-studio/email-builder');
}
