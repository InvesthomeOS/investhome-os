import type { Route } from 'next';
import { redirect } from 'next/navigation';

/** Alias → canonical Proposal Builder route */
export default function ProposalStudioAliasRedirect() {
  redirect('/workspaces/creative-studio/proposal-builder' as Route);
}
