import { redirect } from 'next/navigation';

/** Alias → canonical Email Builder route */
export default function EmailAliasRedirect() {
  redirect('/workspaces/creative-studio/email-builder');
}
