import type { Route } from 'next';
import { redirect } from 'next/navigation';

/**
 * Creative Studio moved out of Marketing → standalone TOOLS module.
 */
export default function MarketingCreativeStudioRedirectPage() {
  redirect('/workspaces/creative-studio' as Route);
}
